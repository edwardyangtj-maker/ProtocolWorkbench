from __future__ import annotations

import asyncio
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal

from protocol_workbench.core.models import (
    EndpointConfig, EndpointType, FrameRule, MessageTemplate,
    LogRecord, PayloadType, Project, Environment,
)
from protocol_workbench.core.logger_service import LoggerService
from protocol_workbench.core.template_engine import TemplateEngine
from protocol_workbench.core.variable_engine import VariableEngine
from protocol_workbench.core.response_matcher import ResponseMatcher
from protocol_workbench.codecs.frame_base import FrameCodec
from protocol_workbench.codecs.payload_base import PayloadCodec
from protocol_workbench.transports.base import TransportAdapter


class RuntimeManager(QObject):
    endpoint_state_changed = Signal(str, str)
    data_received = Signal(str, bytes, str)
    data_sent = Signal(str, bytes, str)
    log_record_created = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, logger: LoggerService, parent=None):
        super().__init__(parent)
        self.logger = logger
        self.variable_engine = VariableEngine()
        self.template_engine = TemplateEngine(self.variable_engine)
        self.response_matcher = ResponseMatcher()
        self._transports: dict[str, TransportAdapter] = {}
        self._frame_codecs: dict[str, FrameCodec] = {}
        self._payload_codecs: dict[str, PayloadCodec] = {}
        self._project: Project | None = None
        self._pending_responses: dict[str, tuple] = {}
        self._auto_reply_rules: list[dict] = []
        self._heartbeat_tasks: dict[str, asyncio.Task] = {}

    def set_project(self, project: Project):
        self._project = project
        self.variable_engine.set_project_variables(project.variables)
        self._frame_codecs.clear()
        self._payload_codecs.clear()
        for rule in project.frame_rules:
            self._frame_codecs[rule.id] = FrameCodec.create(rule)

    async def start_endpoint(self, endpoint: EndpointConfig):
        if endpoint.id in self._transports:
            adapter = self._transports[endpoint.id]
            if adapter.is_running():
                self.logger.warn(f"Endpoint {endpoint.name} already running")
                return

        adapter = self._create_adapter(endpoint)
        if adapter is None:
            return

        conflict = self._check_port_conflict(endpoint)
        if conflict:
            self.logger.error(f"端口冲突: {conflict}")
            self.error_occurred.emit(conflict)
            return

        self._transports[endpoint.id] = adapter
        self._payload_codecs[endpoint.id] = PayloadCodec.create(endpoint.payload_type)

        if endpoint.frame_rule_id and endpoint.frame_rule_id in self._frame_codecs:
            self._frame_codecs[endpoint.id] = self._frame_codecs[endpoint.frame_rule_id]

        adapter.data_received.connect(lambda data, addr, eid=endpoint.id: self._on_data_received(eid, data, addr))
        adapter.state_changed.connect(self.endpoint_state_changed.emit)
        adapter.error_occurred.connect(lambda msg: self.logger.error(msg))

        await adapter.start()
        self.logger.info(f"Endpoint {endpoint.name} started ({endpoint.type.value})")

        # 自动注册 auto-reply：扫描模板，找到 ack_config.auto_reply=True 的模板作为自动回复规则
        # 先清除该端点的旧规则，避免重复注册导致重复发送
        self._auto_reply_rules = [
            r for r in self._auto_reply_rules
            if r["endpoint_id"] != endpoint.id
        ]
        if self._project:
            for tpl in self._project.message_templates:
                if tpl.ack_config.enabled and tpl.ack_config.auto_reply:
                    self.add_auto_reply(endpoint.id, tpl.ack_config.match_rules, tpl)
                    self.logger.info(f"自动注册回复规则: {tpl.name}")

        if endpoint.heartbeat_config.enabled:
            self._start_heartbeat(endpoint)

    async def stop_endpoint(self, endpoint_id: str):
        self._stop_heartbeat(endpoint_id)
        # 清理该端点的自动回复规则
        self._auto_reply_rules = [
            r for r in self._auto_reply_rules
            if r["endpoint_id"] != endpoint_id
        ]
        if endpoint_id in self._transports:
            adapter = self._transports[endpoint_id]
            await adapter.stop()
            name = adapter.config.name
            del self._transports[endpoint_id]
            self.logger.info(f"Endpoint {name} stopped")

    async def stop_all(self):
        for eid in list(self._transports.keys()):
            await self.stop_endpoint(eid)

    async def send_message(self, endpoint_id: str, template: MessageTemplate, target: str = "") -> bool:
        if endpoint_id not in self._transports:
            self.logger.error(f"Endpoint {endpoint_id} not found or not started")
            return False

        adapter = self._transports[endpoint_id]
        rendered = self.template_engine.render(template)

        # 日志：打印模板渲染后的结果，检查变量是否成功替换
        self.logger.info(f"[发送] 模板: {template.name} | 渲染结果前200字: {rendered[:200]}")

        payload_codec = self._payload_codecs.get(endpoint_id)
        if payload_codec:
            raw_bytes = payload_codec.encode(rendered)
        else:
            raw_bytes = rendered.encode("utf-8")

        frame_codec = self._frame_codecs.get(endpoint_id)
        if frame_codec:
            framed_data = frame_codec.encode(raw_bytes)
        else:
            framed_data = raw_bytes

        success = await adapter.send(framed_data, target)

        record = LogRecord(
            endpoint=adapter.config.name,
            direction="TX",
            protocol_type=adapter.config.type.value,
            remote_addr=target or f"{adapter.config.remote_host}:{adapter.config.remote_port}",
            template_name=template.name,
            raw_text=rendered[:500] if isinstance(rendered, str) else str(rendered)[:500],
            raw_hex=framed_data.hex()[:500],
            parsed_json=rendered if isinstance(rendered, str) else "",
            status="success" if success else "failed",
        )
        self.logger.tx(
            f"[{adapter.config.type.value.upper()}] {adapter.config.name}({adapter.config.host}:{adapter.config.port}) "
            f"-> {target or f'{adapter.config.remote_host}:{adapter.config.remote_port}'} "
            f"| 模板: {template.name} | {len(framed_data)} bytes",
            record,
        )
        self.log_record_created.emit(record.to_dict())

        self.data_sent.emit(endpoint_id, framed_data, target)

        if success and template.response_config.enabled:
            self._setup_response_wait(endpoint_id, template)

        return success

    async def send_raw(self, endpoint_id: str, data: bytes, target: str = "") -> bool:
        if endpoint_id not in self._transports:
            self.logger.error(f"Endpoint {endpoint_id} not found or not started")
            return False

        adapter = self._transports[endpoint_id]
        frame_codec = self._frame_codecs.get(endpoint_id)
        if frame_codec:
            framed_data = frame_codec.encode(data)
        else:
            framed_data = data

        success = await adapter.send(framed_data, target)
        if success:
            self.logger.info(
                f"[{adapter.config.type.value.upper()}] {adapter.config.name} "
                f"发送原始数据 {len(data)} bytes -> {target or 'default'}"
            )
        return success

    def _setup_response_wait(self, endpoint_id: str, template: MessageTemplate):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        future = loop.create_future()
        match_rules = template.response_config.match_rules
        self._pending_responses[endpoint_id] = (future, match_rules)

        async def timeout_wait():
            try:
                await asyncio.wait_for(future, timeout=template.response_config.timeout_ms / 1000.0)
                self.logger.info(f"Response received for {template.name}")
            except asyncio.TimeoutError:
                self.logger.warn(f"Response timeout for {template.name}")
                action = template.response_config.fail_action.value
                self.logger.warn(f"Fail action: {action}")

        asyncio.create_task(timeout_wait())

    def add_auto_reply(self, endpoint_id: str, match_rules: list, reply_template: MessageTemplate):
        self._auto_reply_rules.append({
            "endpoint_id": endpoint_id,
            "match_rules": match_rules,
            "reply_template": reply_template,
        })

    def create_wait_future(self, endpoint_id: str, match_rules: list) -> asyncio.Future | None:
        if endpoint_id not in self._transports:
            return None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return None
        future = loop.create_future()
        self._pending_responses[endpoint_id] = (future, match_rules)
        return future

    def _on_data_received(self, endpoint_id: str, data: bytes, remote_addr: str):
        adapter = self._transports.get(endpoint_id)
        if adapter is None:
            return

        frame_codec = self._frame_codecs.get(endpoint_id)
        payload_codec = self._payload_codecs.get(endpoint_id)

        frames = [data]
        if frame_codec:
            frames = frame_codec.feed(data)

        for frame in frames:
            decoded = frame
            parsed = ""
            if payload_codec:
                decoded = payload_codec.decode(frame)
                parsed = payload_codec.to_display(decoded)

            record = LogRecord(
                endpoint=adapter.config.name,
                direction="RX",
                protocol_type=adapter.config.type.value,
                remote_addr=remote_addr,
                raw_text=frame.decode("utf-8", errors="replace")[:500],
                raw_hex=frame.hex()[:500],
                parsed_json=parsed,
                status="success",
            )
            self.logger.rx(
                f"[{adapter.config.type.value.upper()}] {adapter.config.name}({adapter.config.host}:{adapter.config.port}) "
                f"<- {remote_addr} | {len(frame)} bytes",
                record,
            )
            self.log_record_created.emit(record.to_dict())
            self.data_received.emit(endpoint_id, frame, remote_addr)

            self._check_auto_reply(endpoint_id, decoded, remote_addr)
            self._check_pending_response(endpoint_id, decoded)

    def _check_auto_reply(self, endpoint_id: str, decoded_data, remote_addr: str):
        import json
        data_dict = None
        if isinstance(decoded_data, dict):
            data_dict = decoded_data
        elif isinstance(decoded_data, str):
            try:
                data_dict = json.loads(decoded_data)
            except json.JSONDecodeError:
                return

        if data_dict is None:
            return

        header = data_dict.get("header", {})
        msg_type = ""
        if isinstance(header, dict):
            msg_type = header.get("msgType", "")

        # 自动回复只匹配 command/report/query/parameter 帧，
        # 不匹配 response 帧，防止自身发出的回复再次触发自动回复导致死循环
        if msg_type == "response":
            return

        # 从接收到的指令中提取 msgId，注入到运行时变量，供模板 ${received_msgId} 使用
        if isinstance(header, dict) and "msgId" in header:
            received_id = str(header["msgId"])
            self.variable_engine.set_runtime_variable("received_msgId", received_id)
            # 验证变量是否设置成功
            verify = self.variable_engine.get_variable("received_msgId")
            self.logger.info(f"[自动回复] 设置 received_msgId={received_id}, 验证读取={verify}")
            self.logger.info(f"[自动回复] 当前运行时变量: {self.variable_engine.get_all_variables()}")
        else:
            self.logger.warn(f"[自动回复] 收到的帧没有 msgId, header={header}")

        # 先检查预注册的自动回复规则
        replied = False
        for rule in self._auto_reply_rules:
            if rule["endpoint_id"] != endpoint_id:
                continue
            from protocol_workbench.core.models import MatchRule
            if self.response_matcher.match(data_dict, rule["match_rules"]):
                self.logger.info(f"[自动回复] 匹配成功(预注册规则): {rule['reply_template'].name}")
                asyncio.create_task(
                    self.send_message(endpoint_id, rule["reply_template"], remote_addr)
                )
                replied = True

        # 再实时扫描项目模板：兼容用户修改模板后未重启端点的情况
        if not replied and self._project:
            for tpl in self._project.message_templates:
                if not (tpl.ack_config.enabled and tpl.ack_config.auto_reply):
                    continue
                if self.response_matcher.match(data_dict, tpl.ack_config.match_rules):
                    self.logger.info(f"[自动回复] 匹配成功(实时扫描): {tpl.name}")
                    # 自动注册，下次直接命中预注册规则
                    self.add_auto_reply(endpoint_id, tpl.ack_config.match_rules, tpl)
                    asyncio.create_task(
                        self.send_message(endpoint_id, tpl, remote_addr)
                    )
                    replied = True
                    break

        # 若无模板匹配，则发送默认响应帧（服务端和客户端均生效）
        if not replied:
            self._send_default_response(endpoint_id, data_dict, remote_addr)

    def _send_default_response(self, endpoint_id: str, request_data: dict, remote_addr: str):
        import json as _json
        import time

        adapter = self._transports.get(endpoint_id)
        if adapter is None:
            return

        header = request_data.get("header", {})
        received_msg_id = ""
        received_from = ""
        if isinstance(header, dict):
            received_msg_id = str(header.get("msgId", ""))
            received_from = str(header.get("from", ""))

        received_body = request_data.get("body", {})

        response = {
            "header": {
                "msgId": received_msg_id,
                "msgType": "response",
                "timestamp": int(time.time() * 1000),
                "from": "server",
                "to": received_from or "client",
            },
            "body": {
                "code": 200,
                "message": "success",
                "data": received_body if isinstance(received_body, dict) else {},
            },
        }

        response_str = _json.dumps(response, ensure_ascii=False, separators=(",", ":"))

        payload_codec = self._payload_codecs.get(endpoint_id)
        if payload_codec:
            raw_bytes = payload_codec.encode(response_str)
        else:
            raw_bytes = response_str.encode("utf-8")

        frame_codec = self._frame_codecs.get(endpoint_id)
        if frame_codec:
            framed_data = frame_codec.encode(raw_bytes)
        else:
            framed_data = raw_bytes

        asyncio.create_task(adapter.send(framed_data, remote_addr))

        record = LogRecord(
            endpoint=adapter.config.name,
            direction="TX",
            protocol_type=adapter.config.type.value,
            remote_addr=remote_addr,
            template_name="自动响应(默认)",
            raw_text=response_str[:500],
            raw_hex=framed_data.hex()[:500],
            parsed_json=response_str,
            status="success",
        )
        self.logger.tx(
            f"[{adapter.config.type.value.upper()}] {adapter.config.name} "
            f"自动响应(默认) -> {remote_addr} | msgId={received_msg_id}",
            record,
        )
        self.log_record_created.emit(record.to_dict())
        self.data_sent.emit(endpoint_id, framed_data, remote_addr)

    def _check_pending_response(self, endpoint_id: str, decoded_data):
        if endpoint_id not in self._pending_responses:
            return
        future, match_rules = self._pending_responses[endpoint_id]
        if future.done():
            del self._pending_responses[endpoint_id]
            return

        import json
        data_dict = None
        if isinstance(decoded_data, dict):
            data_dict = decoded_data
        elif isinstance(decoded_data, str):
            try:
                data_dict = json.loads(decoded_data)
            except json.JSONDecodeError:
                return

        if data_dict is not None:
            if match_rules and not self.response_matcher.match(data_dict, match_rules):
                return
            future.set_result(data_dict)
            del self._pending_responses[endpoint_id]

    def get_endpoint_state(self, endpoint_id: str) -> str:
        if endpoint_id in self._transports:
            return self._transports[endpoint_id].state
        return TransportAdapter.STATE_IDLE

    def _create_adapter(self, config: EndpointConfig) -> TransportAdapter | None:
        from protocol_workbench.transports.tcp_client import TcpClientAdapter
        from protocol_workbench.transports.tcp_server import TcpServerAdapter
        from protocol_workbench.transports.udp_endpoint import UdpEndpointAdapter
        from protocol_workbench.transports.http_client import HttpClientAdapter
        from protocol_workbench.transports.http_server import HttpServerAdapter
        from protocol_workbench.transports.websocket_client import WebSocketClientAdapter
        from protocol_workbench.transports.websocket_server import WebSocketServerAdapter

        adapters = {
            EndpointType.TCP_CLIENT: TcpClientAdapter,
            EndpointType.TCP_SERVER: TcpServerAdapter,
            EndpointType.UDP_ENDPOINT: UdpEndpointAdapter,
            EndpointType.HTTP_CLIENT: HttpClientAdapter,
            EndpointType.HTTP_SERVER: HttpServerAdapter,
            EndpointType.WS_CLIENT: WebSocketClientAdapter,
            EndpointType.WS_SERVER: WebSocketServerAdapter,
        }

        cls = adapters.get(config.type)
        if cls:
            adapter = cls(config, self)
            if config.type == EndpointType.HTTP_CLIENT:
                from protocol_workbench.transports.http_client import HttpClientAdapter
                if isinstance(adapter, HttpClientAdapter):
                    adapter.set_method(config.http_method)
                    if config.custom_headers:
                        adapter.set_custom_headers(config.custom_headers)
            elif config.type == EndpointType.HTTP_SERVER:
                from protocol_workbench.transports.http_server import HttpServerAdapter
                if isinstance(adapter, HttpServerAdapter):
                    for route in config.reply_routes:
                        adapter.add_reply_route(
                            method=route.get("method", "*"),
                            path=route.get("path", config.path),
                            status=route.get("status", 200),
                            content_type=route.get("content_type", "application/json"),
                            body=route.get("body", "{}"),
                        )
            return adapter
        self.logger.error(f"Unknown endpoint type: {config.type}")
        return None

    def _check_port_conflict(self, endpoint: EndpointConfig) -> str | None:
        server_types = {
            EndpointType.TCP_SERVER,
            EndpointType.HTTP_SERVER,
            EndpointType.UDP_ENDPOINT,
            EndpointType.WS_SERVER,
        }
        if endpoint.type not in server_types:
            return None

        bind_host = endpoint.host
        bind_port = endpoint.port

        for eid, adapter in self._transports.items():
            if eid == endpoint.id:
                continue
            other = adapter.config
            if other.type not in server_types:
                continue
            if other.port == bind_port:
                if other.host == "0.0.0.0" or bind_host == "0.0.0.0" or other.host == bind_host:
                    return f"端口 {bind_port} 已被端点 '{other.name}' 占用 ({other.host}:{other.port})"

        import socket
        try:
            sock_type = socket.SOCK_DGRAM if endpoint.type == EndpointType.UDP_ENDPOINT else socket.SOCK_STREAM
            with socket.socket(socket.AF_INET, sock_type) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((bind_host, bind_port))
        except OSError:
            return f"端口 {bind_host}:{bind_port} 已被系统其他进程占用"
        return None

    def _start_heartbeat(self, endpoint: EndpointConfig):
        hc = endpoint.heartbeat_config
        if not hc.enabled or not hc.template_id:
            return
        if endpoint.id in self._heartbeat_tasks:
            return

        async def heartbeat_loop():
            fail_count = 0
            while endpoint.id in self._transports:
                try:
                    await asyncio.sleep(hc.interval_ms / 1000.0)
                    if endpoint.id not in self._transports:
                        break

                    if hc.mode.value == "active":
                        template = None
                        if self._project:
                            for t in self._project.message_templates:
                                if t.id == hc.template_id:
                                    template = t
                                    break
                        if template:
                            success = await self.send_message(endpoint.id, template)
                            if not success:
                                fail_count += 1
                            else:
                                fail_count = 0
                    else:
                        fail_count = 0

                    if fail_count >= hc.max_fail_count:
                        self.logger.warn(f"Heartbeat failed {fail_count} times for {endpoint.name}")
                        if hc.fail_action.value == "disconnect":
                            await self.stop_endpoint(endpoint.id)
                            break
                        elif hc.fail_action.value == "reconnect":
                            await self.stop_endpoint(endpoint.id)
                            await asyncio.sleep(1)
                            await self.start_endpoint(endpoint)
                            break

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Heartbeat error: {e}")
                    fail_count += 1

        self._heartbeat_tasks[endpoint.id] = asyncio.create_task(heartbeat_loop())

    def _stop_heartbeat(self, endpoint_id: str):
        if endpoint_id in self._heartbeat_tasks:
            self._heartbeat_tasks[endpoint_id].cancel()
            del self._heartbeat_tasks[endpoint_id]
