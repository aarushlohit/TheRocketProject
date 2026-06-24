"""Rocket wrapper for vendored Shokunin memory MCP.

When ChromaDB's native binding is unavailable on Windows, this module serves a
small Shokunin-compatible fallback so Rocket still has persistent memory,
freshness-aware search, session logs, and claim verification.
"""

from __future__ import annotations

import json
import os
import runpy
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    shokunin_root = repo_root / "external" / "shokunin"
    server_path = shokunin_root / ".pack" / "memory" / "mcp-server.py"
    stub_path = shokunin_root / ".pack" / "scripts" / "chroma_helper_stub.py"
    if not server_path.exists():
        raise FileNotFoundError(f"Shokunin MCP server not found: {server_path}")
    if not stub_path.exists():
        raise FileNotFoundError(f"Shokunin helper stub not found: {stub_path}")

    home = (repo_root / "data" / "rocket" / "phase2" / "shokunin_home").resolve()
    scripts_dir = home / ".shokunin" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(stub_path, scripts_dir / "chroma_helper_stub.py")

    os.environ["USERPROFILE"] = str(home)
    os.environ["HOME"] = str(home)
    if not _chromadb_ready():
        _fallback_loop(home)
        return
    runpy.run_path(str(server_path), run_name="__main__")


def _chromadb_ready() -> bool:
    try:
        from chromadb.api import rust  # noqa: F401
    except Exception:
        return False
    return True


def _fallback_loop(home: Path) -> None:
    db_path = home / ".shokunin" / "memory" / "fallback_memory.sqlite3"
    sessions_dir = home / ".shokunin" / "memory" / "sessions"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    _init_db(db_path)
    for line in sys.stdin:
        line = line.lstrip("\ufeff")
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            response = _handle_fallback(db_path, sessions_dir, request)
        except Exception as error:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": str(error)}}
        sys.stdout.write(json.dumps(response, ensure_ascii=True) + "\n")
        sys.stdout.flush()


def _init_db(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                type TEXT NOT NULL,
                tags TEXT NOT NULL,
                project TEXT NOT NULL,
                session_id TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )


def _handle_fallback(db_path: Path, sessions_dir: Path, request: dict[str, Any]) -> dict[str, Any]:
    method = request.get("method")
    request_id = request.get("id")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "shokunin-memory", "version": "1.0.0-rocket-fallback"},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": _fallback_tools()}}
    if method == "tools/call":
        params = request.get("params") if isinstance(request.get("params"), dict) else {}
        result = _fallback_tool_call(db_path, sessions_dir, params)
        return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": result}]}}
    return {"jsonrpc": "2.0", "id": request_id, "result": {}}


def _fallback_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "store_context",
            "description": "Store persistent Rocket/Shokunin context with tags, project, and session.",
            "inputSchema": {"type": "object", "required": ["text", "session_id"], "properties": {"text": {"type": "string"}, "session_id": {"type": "string"}, "type": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}, "project": {"type": "string"}}},
        },
        {
            "name": "search_context",
            "description": "Search persistent memory with keyword and freshness scoring.",
            "inputSchema": {"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}, "project": {"type": "string"}, "type": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}, "n_results": {"type": "integer"}, "freshness_boost": {"type": "number"}}},
        },
        {
            "name": "multi_search_context",
            "description": "Search persistent memory with keyword, tag, and freshness scoring.",
            "inputSchema": {"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}, "project": {"type": "string"}, "n_results": {"type": "integer"}, "freshness_boost": {"type": "number"}}},
        },
        {
            "name": "get_session_summary",
            "description": "Return all memory entries for a session.",
            "inputSchema": {"type": "object", "required": ["session_id"], "properties": {"session_id": {"type": "string"}}},
        },
        {
            "name": "list_sessions",
            "description": "List recent memory sessions.",
            "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer"}}},
        },
        {
            "name": "save_message",
            "description": "Save one chat/message entry.",
            "inputSchema": {"type": "object", "required": ["text", "session_id"], "properties": {"text": {"type": "string"}, "session_id": {"type": "string"}, "role": {"type": "string"}}},
        },
        {
            "name": "verify_file_path",
            "description": "Verify whether a file or directory path exists.",
            "inputSchema": {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}},
        },
    ]


def _fallback_tool_call(db_path: Path, sessions_dir: Path, params: dict[str, Any]) -> str:
    name = params.get("name")
    args = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
    if name == "store_context":
        return json.dumps(_store(db_path, sessions_dir, args), ensure_ascii=True)
    if name in {"search_context", "multi_search_context"}:
        return json.dumps(_search(db_path, args), ensure_ascii=True)
    if name == "get_session_summary":
        return json.dumps(_session_summary(db_path, str(args.get("session_id", ""))), ensure_ascii=True)
    if name == "list_sessions":
        return json.dumps(_list_sessions(db_path, int(args.get("limit", 10))), ensure_ascii=True)
    if name == "save_message":
        args = {**args, "type": "msg", "tags": [str(args.get("role", "user"))]}
        return json.dumps(_store(db_path, sessions_dir, args), ensure_ascii=True)
    if name == "verify_file_path":
        return json.dumps(_verify_path(str(args.get("path", ""))), ensure_ascii=True)
    return json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=True)


def _store(db_path: Path, sessions_dir: Path, args: dict[str, Any]) -> dict[str, Any]:
    import uuid

    entry_id = str(uuid.uuid4())
    text = str(args.get("text", ""))[:50000]
    entry_type = str(args.get("type", "general") or "general")
    tags = [str(tag) for tag in args.get("tags", []) if str(tag).strip()]
    project = str(args.get("project", "rocket") or "rocket")
    session_id = str(args.get("session_id", "rocket") or "rocket")
    created_at = time.time()
    with sqlite3.connect(db_path) as db:
        db.execute(
            "INSERT INTO memory VALUES (?, ?, ?, ?, ?, ?, ?)",
            (entry_id, text, entry_type, json.dumps(tags), project, session_id, created_at),
        )
    session_file = sessions_dir / f"{_safe_session(session_id)}.jsonl"
    session_file.write_text(
        session_file.read_text(encoding="utf-8") if session_file.exists() else "",
        encoding="utf-8",
    )
    with session_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"id": entry_id, "text": text[:500], "type": entry_type, "project": project, "tags": tags, "created_at": created_at}, ensure_ascii=True) + "\n")
    return {"id": entry_id, "type": entry_type, "stored": True, "fallback": True}


def _search(db_path: Path, args: dict[str, Any]) -> list[dict[str, Any]]:
    query = str(args.get("query", "")).lower()
    project = str(args.get("project", ""))
    entry_type = str(args.get("type", ""))
    n_results = int(args.get("n_results", 10) or 10)
    freshness = float(args.get("freshness_boost", 0.15) or 0.0)
    terms = [term for term in re_split(query) if term]
    now = time.time()
    rows: list[tuple[str, str, str, str, str, str, float]] = []
    with sqlite3.connect(db_path) as db:
        for row in db.execute("SELECT id, text, type, tags, project, session_id, created_at FROM memory"):
            rows.append(row)  # type: ignore[arg-type]
    scored = []
    for entry_id, text, typ, tags_raw, proj, session_id, created_at in rows:
        if project and proj != project:
            continue
        if entry_type and typ != entry_type:
            continue
        haystack = f"{text} {typ} {tags_raw} {proj}".lower()
        lexical = sum(1 for term in terms if term in haystack) / max(len(terms), 1)
        age_days = max((now - created_at) / 86400, 0)
        fresh_score = 1 / (1 + age_days)
        score = (1 - freshness) * lexical + freshness * fresh_score
        if score <= 0 and terms:
            continue
        scored.append((score, entry_id, text, typ, json.loads(tags_raw), proj, session_id, created_at))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "id": entry_id,
            "text": text,
            "type": typ,
            "tags": tags,
            "project": proj,
            "session_id": session_id,
            "score": round(score, 4),
            "created_at": created_at,
            "fallback": True,
        }
        for score, entry_id, text, typ, tags, proj, session_id, created_at in scored[:n_results]
    ]


def _session_summary(db_path: Path, session_id: str) -> list[dict[str, Any]]:
    with sqlite3.connect(db_path) as db:
        rows = db.execute(
            "SELECT id, text, type, tags, project, created_at FROM memory WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ).fetchall()
    return [
        {"id": row[0], "text": row[1], "type": row[2], "tags": json.loads(row[3]), "project": row[4], "created_at": row[5]}
        for row in rows
    ]


def _list_sessions(db_path: Path, limit: int) -> list[dict[str, Any]]:
    with sqlite3.connect(db_path) as db:
        rows = db.execute(
            "SELECT session_id, COUNT(*), MAX(created_at) FROM memory GROUP BY session_id ORDER BY MAX(created_at) DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"session_id": row[0], "entries": row[1], "updated_at": row[2]} for row in rows]


def _verify_path(raw_path: str) -> dict[str, Any]:
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    exists = path.exists()
    return {
        "exists": exists,
        "path": str(path),
        "kind": "directory" if path.is_dir() else "file" if path.is_file() else "missing",
    }


def _safe_session(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "-" for char in value)[:80] or "rocket"


def re_split(query: str) -> list[str]:
    import re

    return re.split(r"[^a-z0-9_./-]+", query.lower())


if __name__ == "__main__":
    main()
