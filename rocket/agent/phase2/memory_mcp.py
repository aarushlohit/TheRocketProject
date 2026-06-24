"""Minimal stdio MCP server exposing RocketMemory."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from agent.runtime.memory import RocketMemory


def main() -> None:
    memory = RocketMemory(Path("data/rocket/phase2"))
    for line in sys.stdin:
        line = line.lstrip("\ufeff")
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            response = _handle(memory, request)
        except Exception as error:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": str(error)}}
        sys.stdout.write(json.dumps(response, ensure_ascii=True) + "\n")
        sys.stdout.flush()


def _handle(memory: RocketMemory, request: dict[str, Any]) -> dict[str, Any]:
    method = request.get("method")
    request_id = request.get("id")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "rocket-memory", "version": "0.1.0"},
            },
        }
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "rocket_profile",
                        "description": "Read Rocket user profile preferences.",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                    {
                        "name": "rocket_memory_get",
                        "description": "Read a Rocket memory key.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"key": {"type": "string"}},
                            "required": ["key"],
                        },
                    },
                    {
                        "name": "rocket_setup",
                        "description": "Read Rocket runtime setup state.",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                    {
                        "name": "rocket_memory_set",
                        "description": "Write a Rocket memory key.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"key": {"type": "string"}, "value": {}},
                            "required": ["key", "value"],
                        },
                    },
                ],
            },
        }
    if method == "tools/call":
        params = request.get("params") if isinstance(request.get("params"), dict) else {}
        return _tool_call(memory, request_id, params)
    return {"jsonrpc": "2.0", "id": request_id, "result": {}}


def _tool_call(memory: RocketMemory, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
    if name == "rocket_profile":
        text = json.dumps(memory.load_profile().__dict__, ensure_ascii=True)
    elif name == "rocket_setup":
        text = json.dumps(memory.get("setup", {}), ensure_ascii=True)
    elif name == "rocket_memory_get":
        text = json.dumps(memory.get(str(arguments.get("key", ""))), ensure_ascii=True)
    elif name == "rocket_memory_set":
        memory.set(str(arguments.get("key", "")), arguments.get("value"))
        text = "ok"
    else:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Unknown tool"}}

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {"content": [{"type": "text", "text": text}]},
    }


if __name__ == "__main__":
    main()
