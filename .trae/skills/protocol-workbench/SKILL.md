
---
name: "protocol-workbench"
description: "Protocol Workbench development skill. Creates project structure, implements TCP/HTTP/UDP/WebSocket endpoints, JSON editors, template management, and logging. Invoke when building or modifying the Protocol Workbench."
---

# 协议联调工作台开发技能

这个技能用于辅助开发Python + PySide6协议联调工作台项目。

## 项目概述

协议联调工作台是一个桌面端工具，用于后端、上位机设备端、前端接口之间的协议测试、接口验证、场景仿真和问题复现。

## 技术栈

- Python 3
- PySide6 (Qt 6 for Python)
- asyncio (异步编程)
- qasync (Qt + asyncio 集成)
- aiohttp (HTTP)
- websockets (WebSocket)
- 本地JSON文件持久化

## 项目结构

```
protocol_workbench/
├── main.py
├── app/                    # UI层
│   ├── main_window.py
│   ├── project_panel.py
│   ├── endpoint_panel.py
│   ├── message_editor_panel.py
│   ├── scenario_panel.py
│   ├── log_panel.py
│   └── console_panel.py
├── core/                   # 核心逻辑
│   ├── models.py
│   ├── project_manager.py
│   ├── config_store.py
│   ├── runtime_manager.py
│   ├── variable_engine.py
│   ├── template_engine.py
│   ├── response_matcher.py
│   └── logger_service.py
├── transports/             # 通信适配层
│   ├── base.py
│   ├── tcp_client.py
│   ├── tcp_server.py
│   ├── udp_endpoint.py
│   ├── http_client.py
│   ├── http_server.py
│   ├── websocket_client.py
│   └── websocket_server.py
├── codecs/                 # 编解码层
│   ├── frame_base.py
│   ├── raw_frame.py
│   ├── delimiter_frame.py
│   ├── start_end_frame.py
│   ├── length_prefix_frame.py
│   ├── json_payload.py
│   ├── text_payload.py
│   └── hex_payload.py
├── scenario/               # 场景编排
│   ├── scenario_runner.py
│   ├── step_executor.py
│   └── step_types.py
├── storage/                # 存储
│   ├── projects/
│   ├── templates/
│   ├── environments/
│   └── logs/
└── resources/              # 资源文件
    └── default_templates.json
```

## 核心功能模块

### 1. 项目管理
- 新建、打开、保存项目
- 导入/导出项目配置包
- 本地JSON持久化

### 2. 环境管理
- 创建多个联调环境
- 环境变量配置
- 绑定端点
- 自动启动策略

### 3. 端点管理
支持的端点类型：
- TCP Client / TCP Server
- HTTP Client / HTTP Server
- UDP Endpoint
- WebSocket Client / WebSocket Server

### 4. 分帧规则
- Raw (不处理)
- Delimiter (分隔符)
- Start-End (起止符)
- Length-Prefix (长度前缀)

### 5. Payload编解码
- JSON
- Text
- Hex

### 6. 消息模板
- 支持变量替换
- 模板分类管理
- 本地持久化

### 7. 场景编排
- 步骤表格形式
- 支持发送、等待、断言等步骤
- 并行执行

### 8. 日志系统
- 实时日志窗口
- packets.jsonl 报文记录
- 原始字节和解析结果同时保存

## 开发优先级

### 第一阶段 (最高优先级)
1. 项目骨架搭建
2. 数据模型定义
3. 配置持久化
4. 主界面框架

### 第二阶段
1. TCP Client / TCP Server
2. 分帧编解码器
3. JSON编解码
4. 基础日志系统

### 第三阶段
1. JSON源码编辑器
2. JSON树形编辑器
3. 模板管理系统

### 第四阶段
1. HTTP Client / HTTP Server
2. UDP Endpoint
3. WebSocket Client / WebSocket Server

### 第五阶段
1. ACK机制
2. Response机制
3. Heartbeat心跳
4. 自动响应
5. 响应匹配

### 第六阶段
1. 场景步骤表
2. 场景执行器
3. 并行运行

### 第七阶段
1. 项目导入导出
2. 基础文档

## 关键架构原则

1. **传输与业务解耦**: TCP/HTTP/UDP/WebSocket 只负责通信通道
2. **收发与解析解耦**: TCP只处理bytes, FrameCodec拆包, PayloadCodec解码
3. **ACK/Response/Heartbeat分离**: 三者不能混用
4. **模板与运行时分离**: 变量在运行时替换
5. **日志保留原始字节**: 必须保存rawText和rawHex

## 使用说明

当你需要开发协议联调工作台时调用此技能。此技能会帮助你：

- 搭建项目骨架
- 实现通信端点
- 开发编解码器
- 创建UI组件
- 实现业务逻辑
- 编写测试

## 注意事项

- 优先完成TCP + JSON + 自定义分帧 + 日志核心功能
- 避免写死业务字段(msgType, theme等)
- 保证多端点并行运行时UI不阻塞
- 完善错误处理和日志记录
