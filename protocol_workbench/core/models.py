from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from datetime import datetime


def new_id() -> str:
    return uuid.uuid4().hex[:12]


class EndpointType(str, Enum):
    TCP_CLIENT = "tcp_client"
    TCP_SERVER = "tcp_server"
    HTTP_CLIENT = "http_client"
    HTTP_SERVER = "http_server"
    UDP_ENDPOINT = "udp_endpoint"
    WS_CLIENT = "websocket_client"
    WS_SERVER = "websocket_server"


class FrameMode(str, Enum):
    RAW = "raw"
    DELIMITER = "delimiter"
    START_END = "start_end"
    LENGTH_PREFIX = "length_prefix"


class PayloadType(str, Enum):
    JSON = "json"
    TEXT = "text"
    HEX = "hex"


class TemplateCategory(str, Enum):
    MESSAGE = "message"
    # ── SPI 协议帧类型 ──────────────────────────
    CMD_LASER = "cmd_laser"
    CMD_CAMERA = "cmd_camera"
    CMD_RANGE = "cmd_range"
    CMD_TURNTABLE = "cmd_turntable"
    CMD_POWER = "cmd_power"
    CMD_CONNECT = "cmd_connect"
    PARAM_SCAN_CONFIG = "param_scan_config"
    PARAM_MONITOR_POINT = "param_monitor_point"
    PARAM_RANGE_PARAM = "param_range_param"
    PARAM_IMAGING_PARAM = "param_imaging_param"
    PARAM_CAMERA_PARAM = "param_camera_param"
    PARAM_FAN_PARAM = "param_fan_param"
    QUERY_COMPONENT = "query_component"
    QUERY_RANGE_CONFIG = "query_range_config"
    QUERY_CAMERA_CALIB = "query_camera_calib"
    REPORT_DEVICE_STATUS = "report_device_status"
    REPORT_ALARM = "report_alarm"
    REPORT_IMG = "report_img"
    REPORT_HIGH_RANGE = "report_high_range"
    REPORT_TASK = "report_task"
    REPORT_RANGE_RESULT = "report_range_result"
    RESPONSE = "response"
    ACK = "ack"
    HEARTBEAT = "heartbeat"
    # ── 通用 ────────────────────────────────────
    HTTP_REQUEST = "http_request"
    WS_MESSAGE = "ws_message"
    UDP_MESSAGE = "udp_message"
    TCP_MESSAGE = "tcp_message"


class StepType(str, Enum):
    START_ENDPOINT = "start_endpoint"
    STOP_ENDPOINT = "stop_endpoint"
    SEND_MESSAGE = "send_message"
    WAIT_MESSAGE = "wait_message"
    AUTO_REPLY = "auto_reply"
    DELAY = "delay"
    ASSERT_JSON = "assert_json"
    LOOP = "loop"


class MatchOperator(str, Enum):
    EQ = "eq"
    NE = "ne"
    CONTAINS = "contains"
    EXISTS = "exists"
    REGEX = "regex"


class SendMode(str, Enum):
    SEND_ONLY = "send_only"
    RECEIVE_ONLY = "receive_only"
    SEND_WAIT_RESPONSE = "send_wait_response"
    RECEIVE_AUTO_REPLY = "receive_auto_reply"


class HeartbeatMode(str, Enum):
    ACTIVE = "active"
    PASSIVE = "passive"


class FailAction(str, Enum):
    CONTINUE = "continue"
    DISCONNECT = "disconnect"
    RECONNECT = "reconnect"
    STOP_ENV = "stop_environment"
    STOP_SCENARIO = "stop_scenario"


class JsonNodeType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    NULL = "null"
    OBJECT = "object"
    ARRAY = "array"
    RAW = "raw"
    EXPRESSION = "expression"


@dataclass
class JsonNode:
    key: str = ""
    value: str = ""
    node_type: JsonNodeType = JsonNodeType.STRING
    enabled: bool = True
    description: str = ""
    children: list[JsonNode] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "key": self.key,
            "value": self.value,
            "node_type": self.node_type.value,
            "enabled": self.enabled,
            "description": self.description,
        }
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> JsonNode:
        children = [cls.from_dict(c) for c in d.get("children", [])]
        return cls(
            key=d.get("key", ""),
            value=d.get("value", ""),
            node_type=JsonNodeType(d.get("node_type", "string")),
            enabled=d.get("enabled", True),
            description=d.get("description", ""),
            children=children,
        )


@dataclass
class FrameRule:
    id: str = field(default_factory=new_id)
    name: str = "SPI-*JSON#"
    mode: FrameMode = FrameMode.START_END
    delimiter: str = "\n"
    start_flag: str = "*"
    end_flag: str = "#"
    length_field_offset: int = 0
    length_field_size: int = 4
    byte_order: str = "big"
    length_includes_header: bool = False
    fixed_length: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "mode": self.mode.value,
            "delimiter": self.delimiter,
            "start_flag": self.start_flag,
            "end_flag": self.end_flag,
            "length_field_offset": self.length_field_offset,
            "length_field_size": self.length_field_size,
            "byte_order": self.byte_order,
            "length_includes_header": self.length_includes_header,
            "fixed_length": self.fixed_length,
        }

    @classmethod
    def from_dict(cls, d: dict) -> FrameRule:
        return cls(
            id=d.get("id", new_id()),
            name=d.get("name", ""),
            mode=FrameMode(d.get("mode", "raw")),
            delimiter=d.get("delimiter", "\n"),
            start_flag=d.get("start_flag", ""),
            end_flag=d.get("end_flag", ""),
            length_field_offset=d.get("length_field_offset", 0),
            length_field_size=d.get("length_field_size", 4),
            byte_order=d.get("byte_order", "big"),
            length_includes_header=d.get("length_includes_header", False),
            fixed_length=d.get("fixed_length", 0),
        )


@dataclass
class MatchRule:
    path: str = ""
    operator: MatchOperator = MatchOperator.EQ
    value: str = ""

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "operator": self.operator.value,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MatchRule:
        return cls(
            path=d.get("path", ""),
            operator=MatchOperator(d.get("operator", "eq")),
            value=d.get("value", ""),
        )


CATEGORY_MIGRATION_MAP = {
    "command": "message",
    "query": "message",
    "report": "message",
}


def _migrate_category(raw: str) -> str:
    return CATEGORY_MIGRATION_MAP.get(raw, raw)


@dataclass
class AckConfig:
    enabled: bool = False
    template_id: str = ""
    timeout_ms: int = 5000
    match_rules: list[MatchRule] = field(default_factory=list)
    fail_action: FailAction = FailAction.CONTINUE
    auto_reply: bool = False

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "template_id": self.template_id,
            "timeout_ms": self.timeout_ms,
            "match_rules": [r.to_dict() for r in self.match_rules],
            "fail_action": self.fail_action.value,
            "auto_reply": self.auto_reply,
        }

    @classmethod
    def from_dict(cls, d: dict) -> AckConfig:
        return cls(
            enabled=d.get("enabled", False),
            template_id=d.get("template_id", ""),
            timeout_ms=d.get("timeout_ms", 5000),
            match_rules=[MatchRule.from_dict(r) for r in d.get("match_rules", [])],
            fail_action=FailAction(d.get("fail_action", "continue")),
            auto_reply=d.get("auto_reply", False),
        )


@dataclass
class ResponseConfig:
    enabled: bool = False
    template_id: str = ""
    timeout_ms: int = 10000
    match_rules: list[MatchRule] = field(default_factory=list)
    fail_action: FailAction = FailAction.CONTINUE

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "template_id": self.template_id,
            "timeout_ms": self.timeout_ms,
            "match_rules": [r.to_dict() for r in self.match_rules],
            "fail_action": self.fail_action.value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ResponseConfig:
        return cls(
            enabled=d.get("enabled", False),
            template_id=d.get("template_id", ""),
            timeout_ms=d.get("timeout_ms", 10000),
            match_rules=[MatchRule.from_dict(r) for r in d.get("match_rules", [])],
            fail_action=FailAction(d.get("fail_action", "continue")),
        )


@dataclass
class HeartbeatConfig:
    enabled: bool = False
    mode: HeartbeatMode = HeartbeatMode.ACTIVE
    interval_ms: int = 30000
    template_id: str = ""
    response_template_id: str = ""
    timeout_ms: int = 10000
    max_fail_count: int = 3
    fail_action: FailAction = FailAction.DISCONNECT

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "mode": self.mode.value,
            "interval_ms": self.interval_ms,
            "template_id": self.template_id,
            "response_template_id": self.response_template_id,
            "timeout_ms": self.timeout_ms,
            "max_fail_count": self.max_fail_count,
            "fail_action": self.fail_action.value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> HeartbeatConfig:
        return cls(
            enabled=d.get("enabled", False),
            mode=HeartbeatMode(d.get("mode", "active")),
            interval_ms=d.get("interval_ms", 30000),
            template_id=d.get("template_id", ""),
            response_template_id=d.get("response_template_id", ""),
            timeout_ms=d.get("timeout_ms", 10000),
            max_fail_count=d.get("max_fail_count", 3),
            fail_action=FailAction(d.get("fail_action", "disconnect")),
        )


@dataclass
class MessageTemplate:
    id: str = field(default_factory=new_id)
    name: str = ""
    endpoint_id: str = ""
    category: TemplateCategory = TemplateCategory.MESSAGE
    payload_type: PayloadType = PayloadType.JSON
    frame_rule_id: str = ""
    content: str = ""
    tree_nodes: list[JsonNode] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)
    ack_config: AckConfig = field(default_factory=AckConfig)
    response_config: ResponseConfig = field(default_factory=ResponseConfig)
    heartbeat_config: HeartbeatConfig = field(default_factory=HeartbeatConfig)
    match_rules: list[MatchRule] = field(default_factory=list)
    send_mode: SendMode = SendMode.SEND_ONLY

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "endpoint_id": self.endpoint_id,
            "category": self.category.value,
            "payload_type": self.payload_type.value,
            "frame_rule_id": self.frame_rule_id,
            "content": self.content,
            "tree_nodes": [n.to_dict() for n in self.tree_nodes],
            "variables": self.variables,
            "ack_config": self.ack_config.to_dict(),
            "response_config": self.response_config.to_dict(),
            "heartbeat_config": self.heartbeat_config.to_dict(),
            "match_rules": [r.to_dict() for r in self.match_rules],
            "send_mode": self.send_mode.value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MessageTemplate:
        raw_cat = d.get("category", "message")
        migrated_cat = _migrate_category(raw_cat)
        return cls(
            id=d.get("id", new_id()),
            name=d.get("name", ""),
            endpoint_id=d.get("endpoint_id", ""),
            category=TemplateCategory(migrated_cat),
            payload_type=PayloadType(d.get("payload_type", "json")),
            frame_rule_id=d.get("frame_rule_id", ""),
            content=d.get("content", ""),
            tree_nodes=[JsonNode.from_dict(n) for n in d.get("tree_nodes", [])],
            variables=d.get("variables", []),
            ack_config=AckConfig.from_dict(d.get("ack_config", {})),
            response_config=ResponseConfig.from_dict(d.get("response_config", {})),
            heartbeat_config=HeartbeatConfig.from_dict(d.get("heartbeat_config", {})),
            match_rules=[MatchRule.from_dict(r) for r in d.get("match_rules", [])],
            send_mode=SendMode(d.get("send_mode", "send_only")),
        )


@dataclass
class EndpointConfig:
    id: str = field(default_factory=new_id)
    name: str = ""
    type: EndpointType = EndpointType.TCP_CLIENT
    host: str = "0.0.0.0"
    port: int = 9000
    remote_host: str = "127.0.0.1"
    remote_port: int = 9000
    path: str = "/"
    http_method: str = "POST"
    custom_headers: dict[str, str] = field(default_factory=dict)
    reply_routes: list[dict] = field(default_factory=list)
    payload_type: PayloadType = PayloadType.JSON
    frame_rule_id: str = ""
    connect_timeout_ms: int = 10000
    read_timeout_ms: int = 30000
    auto_reconnect: bool = False
    heartbeat_config: HeartbeatConfig = field(default_factory=HeartbeatConfig)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "host": self.host,
            "port": self.port,
            "remote_host": self.remote_host,
            "remote_port": self.remote_port,
            "path": self.path,
            "http_method": self.http_method,
            "custom_headers": self.custom_headers,
            "reply_routes": self.reply_routes,
            "payload_type": self.payload_type.value,
            "frame_rule_id": self.frame_rule_id,
            "connect_timeout_ms": self.connect_timeout_ms,
            "read_timeout_ms": self.read_timeout_ms,
            "auto_reconnect": self.auto_reconnect,
            "heartbeat_config": self.heartbeat_config.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> EndpointConfig:
        return cls(
            id=d.get("id", new_id()),
            name=d.get("name", ""),
            type=EndpointType(d.get("type", "tcp_client")),
            host=d.get("host", "0.0.0.0"),
            port=d.get("port", 9000),
            remote_host=d.get("remote_host", "127.0.0.1"),
            remote_port=d.get("remote_port", 9000),
            path=d.get("path", "/"),
            http_method=d.get("http_method", "POST"),
            custom_headers=d.get("custom_headers", {}),
            reply_routes=d.get("reply_routes", []),
            payload_type=PayloadType(d.get("payload_type", "json")),
            frame_rule_id=d.get("frame_rule_id", ""),
            connect_timeout_ms=d.get("connect_timeout_ms", 10000),
            read_timeout_ms=d.get("read_timeout_ms", 30000),
            auto_reconnect=d.get("auto_reconnect", False),
            heartbeat_config=HeartbeatConfig.from_dict(d.get("heartbeat_config", {})),
        )


@dataclass
class Environment:
    id: str = field(default_factory=new_id)
    name: str = ""
    description: str = ""
    variables: dict[str, str] = field(default_factory=dict)
    endpoint_ids: list[str] = field(default_factory=list)
    auto_start_endpoints: bool = False
    allow_parallel: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "variables": self.variables,
            "endpoint_ids": self.endpoint_ids,
            "auto_start_endpoints": self.auto_start_endpoints,
            "allow_parallel": self.allow_parallel,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Environment:
        return cls(
            id=d.get("id", new_id()),
            name=d.get("name", ""),
            description=d.get("description", ""),
            variables=d.get("variables", {}),
            endpoint_ids=d.get("endpoint_ids", []),
            auto_start_endpoints=d.get("auto_start_endpoints", False),
            allow_parallel=d.get("allow_parallel", True),
        )


@dataclass
class ScenarioStep:
    id: str = field(default_factory=new_id)
    order: int = 0
    type: StepType = StepType.SEND_MESSAGE
    endpoint_id: str = ""
    template_id: str = ""
    timeout_ms: int = 10000
    retry_count: int = 0
    matcher: list[MatchRule] = field(default_factory=list)
    delay_ms: int = 0
    output_variables: dict[str, str] = field(default_factory=dict)
    assert_rules: list[MatchRule] = field(default_factory=list)
    loop_count: int = 1
    data_source_path: str = ""
    data_source_format: str = "json"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order": self.order,
            "type": self.type.value,
            "endpoint_id": self.endpoint_id,
            "template_id": self.template_id,
            "timeout_ms": self.timeout_ms,
            "retry_count": self.retry_count,
            "matcher": [r.to_dict() for r in self.matcher],
            "delay_ms": self.delay_ms,
            "output_variables": self.output_variables,
            "assert_rules": [r.to_dict() for r in self.assert_rules],
            "loop_count": self.loop_count,
            "data_source_path": self.data_source_path,
            "data_source_format": self.data_source_format,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ScenarioStep:
        return cls(
            id=d.get("id", new_id()),
            order=d.get("order", 0),
            type=StepType(d.get("type", "send_message")),
            endpoint_id=d.get("endpoint_id", ""),
            template_id=d.get("template_id", ""),
            timeout_ms=d.get("timeout_ms", 10000),
            retry_count=d.get("retry_count", 0),
            matcher=[MatchRule.from_dict(r) for r in d.get("matcher", [])],
            delay_ms=d.get("delay_ms", 0),
            output_variables=d.get("output_variables", {}),
            assert_rules=[MatchRule.from_dict(r) for r in d.get("assert_rules", [])],
            loop_count=d.get("loop_count", 1),
            data_source_path=d.get("data_source_path", ""),
            data_source_format=d.get("data_source_format", "json"),
        )


@dataclass
class Scenario:
    id: str = field(default_factory=new_id)
    name: str = ""
    description: str = ""
    variables: dict[str, str] = field(default_factory=dict)
    steps: list[ScenarioStep] = field(default_factory=list)
    stop_policy: str = "stop_on_error"
    parallel_policy: str = "sequential"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "variables": self.variables,
            "steps": [s.to_dict() for s in self.steps],
            "stop_policy": self.stop_policy,
            "parallel_policy": self.parallel_policy,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Scenario:
        return cls(
            id=d.get("id", new_id()),
            name=d.get("name", ""),
            description=d.get("description", ""),
            variables=d.get("variables", {}),
            steps=[ScenarioStep.from_dict(s) for s in d.get("steps", [])],
            stop_policy=d.get("stop_policy", "stop_on_error"),
            parallel_policy=d.get("parallel_policy", "sequential"),
        )


@dataclass
class Project:
    id: str = field(default_factory=new_id)
    name: str = "New Project"
    version: str = "1.0.0"
    description: str = ""
    environments: list[Environment] = field(default_factory=list)
    endpoints: list[EndpointConfig] = field(default_factory=list)
    frame_rules: list[FrameRule] = field(default_factory=list)
    message_templates: list[MessageTemplate] = field(default_factory=list)
    scenarios: list[Scenario] = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "environments": [e.to_dict() for e in self.environments],
            "endpoints": [e.to_dict() for e in self.endpoints],
            "frame_rules": [f.to_dict() for f in self.frame_rules],
            "message_templates": [t.to_dict() for t in self.message_templates],
            "scenarios": [s.to_dict() for s in self.scenarios],
            "variables": self.variables,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Project:
        return cls(
            id=d.get("id", new_id()),
            name=d.get("name", "New Project"),
            version=d.get("version", "1.0.0"),
            description=d.get("description", ""),
            environments=[Environment.from_dict(e) for e in d.get("environments", [])],
            endpoints=[EndpointConfig.from_dict(e) for e in d.get("endpoints", [])],
            frame_rules=[FrameRule.from_dict(f) for f in d.get("frame_rules", [])],
            message_templates=[MessageTemplate.from_dict(t) for t in d.get("message_templates", [])],
            scenarios=[Scenario.from_dict(s) for s in d.get("scenarios", [])],
            variables=d.get("variables", {}),
            created_at=d.get("created_at", datetime.now().isoformat()),
            updated_at=d.get("updated_at", datetime.now().isoformat()),
        )


@dataclass
class LogRecord:
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    environment: str = ""
    endpoint: str = ""
    direction: str = ""
    protocol_type: str = ""
    remote_addr: str = ""
    template_name: str = ""
    raw_text: str = ""
    raw_hex: str = ""
    parsed_json: str = ""
    frame_rule: str = ""
    match_rule: str = ""
    elapsed_ms: float = 0.0
    status: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "environment": self.environment,
            "endpoint": self.endpoint,
            "direction": self.direction,
            "protocol_type": self.protocol_type,
            "remote_addr": self.remote_addr,
            "template_name": self.template_name,
            "raw_text": self.raw_text,
            "raw_hex": self.raw_hex,
            "parsed_json": self.parsed_json,
            "frame_rule": self.frame_rule,
            "match_rule": self.match_rule,
            "elapsed_ms": self.elapsed_ms,
            "status": self.status,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> LogRecord:
        return cls(**{k: d.get(k, "") for k in [
            "timestamp", "environment", "endpoint", "direction",
            "protocol_type", "remote_addr", "template_name",
            "raw_text", "raw_hex", "parsed_json", "frame_rule",
            "match_rule", "elapsed_ms", "status", "error",
        ]})
