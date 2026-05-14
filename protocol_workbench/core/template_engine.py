from __future__ import annotations

import json
from typing import Any

from protocol_workbench.core.models import MessageTemplate, JsonNode, JsonNodeType
from protocol_workbench.core.variable_engine import VariableEngine


class TemplateEngine:
    def __init__(self, variable_engine: VariableEngine):
        self.variable_engine = variable_engine

    def render(self, template: MessageTemplate) -> str:
        content = template.content
        rendered = self.variable_engine.resolve(content)
        return rendered

    def render_string(self, text: str) -> str:
        return self.variable_engine.resolve(text)

    def render_tree_nodes(self, nodes: list[JsonNode]) -> Any:
        return self._nodes_to_value(nodes)

    def _nodes_to_value(self, nodes: list[JsonNode]) -> dict:
        result = {}
        for node in nodes:
            if not node.enabled:
                continue
            key = self.variable_engine.resolve(node.key)
            value = self._node_to_value(node)
            result[key] = value
        return result

    def _node_to_value(self, node: JsonNode) -> Any:
        resolved_value = self.variable_engine.resolve(node.value)
        if node.node_type == JsonNodeType.STRING:
            return resolved_value
        elif node.node_type == JsonNodeType.NUMBER:
            try:
                if "." in resolved_value:
                    return float(resolved_value)
                return int(resolved_value)
            except ValueError:
                return resolved_value
        elif node.node_type == JsonNodeType.BOOLEAN:
            return resolved_value.lower() in ("true", "1", "yes")
        elif node.node_type == JsonNodeType.NULL:
            return None
        elif node.node_type == JsonNodeType.OBJECT:
            return self._nodes_to_value(node.children)
        elif node.node_type == JsonNodeType.ARRAY:
            return [self._node_to_value(child) for child in node.children if child.enabled]
        elif node.node_type == JsonNodeType.RAW:
            try:
                return json.loads(resolved_value)
            except json.JSONDecodeError:
                return resolved_value
        elif node.node_type == JsonNodeType.EXPRESSION:
            return resolved_value
        return resolved_value

    @staticmethod
    def json_to_tree_nodes(data: Any, key: str = "") -> list[JsonNode]:
        if isinstance(data, dict):
            nodes = []
            for k, v in data.items():
                node = TemplateEngine._value_to_node(v, k)
                nodes.append(node)
            return nodes
        elif isinstance(data, list):
            node = TemplateEngine._value_to_node(data, key)
            return [node]
        else:
            node = TemplateEngine._value_to_node(data, key)
            return [node]

    @staticmethod
    def _value_to_node(value: Any, key: str = "") -> JsonNode:
        if isinstance(value, dict):
            children = []
            for k, v in value.items():
                children.append(TemplateEngine._value_to_node(v, k))
            return JsonNode(
                key=key,
                value="",
                node_type=JsonNodeType.OBJECT,
                children=children,
            )
        elif isinstance(value, list):
            children = []
            for i, item in enumerate(value):
                children.append(TemplateEngine._value_to_node(item, f"[{i}]"))
            return JsonNode(
                key=key,
                value="",
                node_type=JsonNodeType.ARRAY,
                children=children,
            )
        elif isinstance(value, str):
            return JsonNode(key=key, value=value, node_type=JsonNodeType.STRING)
        elif isinstance(value, bool):
            return JsonNode(key=key, value=str(value).lower(), node_type=JsonNodeType.BOOLEAN)
        elif isinstance(value, int) or isinstance(value, float):
            return JsonNode(key=key, value=str(value), node_type=JsonNodeType.NUMBER)
        elif value is None:
            return JsonNode(key=key, value="null", node_type=JsonNodeType.NULL)
        else:
            return JsonNode(key=key, value=str(value), node_type=JsonNodeType.RAW)

    @staticmethod
    def tree_nodes_to_json(nodes: list[JsonNode]) -> str:
        engine = TemplateEngine(VariableEngine())
        data = engine._nodes_to_value(nodes)
        return json.dumps(data, ensure_ascii=False, indent=2)
