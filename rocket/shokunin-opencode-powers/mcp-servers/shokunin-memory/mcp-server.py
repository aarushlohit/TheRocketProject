#!/usr/bin/env python3
"""Shokunin Memory MCP Server — Persistent memory via ChromaDB vector database."""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import chromadb
from chromadb.config import Settings

CHROMA_DIR = Path.home() / ".shokunin" / "memory" / "chroma_db"
SESSIONS_DIR = Path.home() / ".shokunin" / "memory" / "sessions"

VALID_TYPES = [
    "decision", "file", "command", "checkpoint", "session_end",
    "preference", "general", "claim_file", "claim_function"
]


def get_client():
    return chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False)
    )


def get_collection(client, project="default"):
    name = "".join(c if c.isalnum() or c == "-" else "-" for c in project.lower())[:64]
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"}
    )


# ── MCP Protocol ───────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "store_context",
        "description": "Store a piece of context in persistent memory. Use for decisions, file changes, commands, checkpoints, or general notes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The text content to store"},
                "tags": {"type": "string", "description": "Comma-separated tags for categorization"},
                "project": {"type": "string", "description": "Project name", "default": "default"},
                "session_id": {"type": "string", "description": "Current session ID"},
                "type": {"type": "string", "enum": VALID_TYPES, "description": "Entry type", "default": "general"}
            },
            "required": ["text", "project", "session_id"]
        }
    },
    {
        "name": "search_context",
        "description": "Search stored memory entries by semantic similarity. Use to recall past decisions, context, or information.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "project": {"type": "string", "description": "Project filter (empty for all projects)", "default": ""},
                "limit": {"type": "integer", "description": "Max results", "default": 10},
                "type": {"type": "string", "description": "Filter by entry type"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_session_summary",
        "description": "Get a full session summary by session ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID to retrieve"}
            },
            "required": ["session_id"]
        }
    },
    {
        "name": "list_sessions",
        "description": "List recent sessions with metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max sessions to list", "default": 10}
            }
        }
    },
    {
        "name": "save_session_end",
        "description": "Save a session end summary. Call at the end of each session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID"},
                "summary": {"type": "string", "description": "Session summary text"},
                "project": {"type": "string", "description": "Project name", "default": "default"},
                "tags": {"type": "string", "description": "Comma-separated tags", "default": "session-end"}
            },
            "required": ["session_id", "summary", "project"]
        }
    },
    {
        "name": "memory_healthcheck",
        "description": "Check the health and status of the memory database.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "delete_memory",
        "description": "Delete memory entries by session prefix or project name.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_prefix": {"type": "string", "description": "Session ID prefix to delete"},
                "project": {"type": "string", "description": "Project name to delete all entries for"}
            }
        }
    }
]


def handle_tool(name, args):
    client = get_client()

    if name == "store_context":
        project = args.get("project", "default")
        col = get_collection(client, project)
        entry_id = f"{args.get('session_id', 'unknown')}-{int(time.time() * 1000)}"
        col.add(
            documents=[args["text"]],
            ids=[entry_id],
            metadatas=[{
                "type": args.get("type", "general"),
                "tags": args.get("tags", ""),
                "project": project,
                "session_id": args.get("session_id", "unknown"),
                "timestamp": datetime.now().isoformat()
            }]
        )
        return {"content": [{"type": "text", "text": f"Stored entry {entry_id} in '{project}'"}]}

    elif name == "search_context":
        project = args.get("project", "")
        if project:
            col = get_collection(client, project)
            if col.count() == 0:
                return {"content": [{"type": "text", "text": "No entries found in this project."}]}
            where = {"type": args["type"]} if args.get("type") else None
            results = col.query(
                query_texts=[args["query"]],
                n_results=args.get("limit", 10),
                where=where,
                include=["documents", "metadatas", "distances"]
            )
        else:
            all_results = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
            for c in client.list_collections():
                if c.count() == 0:
                    continue
                where = {"type": args["type"]} if args.get("type") else None
                r = c.query(
                    query_texts=[args["query"]],
                    n_results=args.get("limit", 10),
                    where=where,
                    include=["documents", "metadatas", "distances"]
                )
                for key in all_results:
                    all_results[key][0].extend(r.get(key, [[]])[0])
            # Sort by distance
            combined = list(zip(
                all_results["documents"][0],
                all_results["metadatas"][0],
                all_results["distances"][0]
            ))
            combined.sort(key=lambda x: x[2])
            combined = combined[:args.get("limit", 10)]
            if not combined:
                return {"content": [{"type": "text", "text": "No results found."}]}
            results_text = ""
            for doc, meta, dist in combined:
                score = 1 - dist
                results_text += f"\n[{score:.3f}] {meta.get('type', '?')} | {meta.get('project', '?')} | {meta.get('session_id', '?')}\n"
                results_text += f"  {meta.get('timestamp', '?')}\n"
                results_text += f"  {doc[:500]}\n"
            return {"content": [{"type": "text", "text": results_text}]}

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]
        if not docs:
            return {"content": [{"type": "text", "text": "No results found."}]}
        output = ""
        for doc, meta, dist in zip(docs, metas, dists):
            score = 1 - dist
            output += f"\n[{score:.3f}] {meta.get('type', '?')} | {meta.get('project', '?')} | {meta.get('session_id', '?')}\n"
            output += f"  {meta.get('timestamp', '?')}\n"
            output += f"  {doc[:500]}\n"
        return {"content": [{"type": "text", "text": output}]}

    elif name == "get_session_summary":
        sid = args["session_id"]
        session_file = SESSIONS_DIR / f"{sid}.md"
        if session_file.exists():
            return {"content": [{"type": "text", "text": session_file.read_text(encoding="utf-8")}]}
        for col in client.list_collections():
            data = col.get(include=["documents", "metadatas"], where={"session_id": sid})
            docs = data.get("documents", [])
            if docs:
                output = "\n\n".join(docs)
                return {"content": [{"type": "text", "text": output}]}
        return {"content": [{"type": "text", "text": f"Session '{sid}' not found."}]}

    elif name == "list_sessions":
        limit = args.get("limit", 10)
        sessions = sorted(SESSIONS_DIR.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not sessions:
            return {"content": [{"type": "text", "text": "No sessions found."}]}
        output = ""
        for s in sessions[:limit]:
            mtime = datetime.fromtimestamp(s.stat().st_mtime).isoformat()
            output += f"  {s.stem}  ({s.stat().st_size} bytes, {mtime})\n"
        return {"content": [{"type": "text", "text": output}]}

    elif name == "save_session_end":
        sid = args["session_id"]
        project = args.get("project", "default")
        session_file = SESSIONS_DIR / f"{sid}.md"
        session_file.write_text(args["summary"], encoding="utf-8")
        col = get_collection(client, project)
        col.add(
            documents=[args["summary"]],
            ids=[f"session-{sid}"],
            metadatas=[{
                "type": "session_end",
                "tags": args.get("tags", "session-end"),
                "project": project,
                "session_id": sid,
                "timestamp": datetime.now().isoformat()
            }]
        )
        return {"content": [{"type": "text", "text": f"Session '{sid}' saved."}]}

    elif name == "memory_healthcheck":
        collections = client.list_collections()
        total = sum(c.count() for c in collections)
        db_size = sum(f.stat().st_size for f in CHROMA_DIR.rglob("*") if f.is_file()) if CHROMA_DIR.exists() else 0
        output = f"DB path: {CHROMA_DIR}\nExists: {CHROMA_DIR.exists()}\n"
        output += f"Collections: {len(collections)}\nTotal entries: {total}\n"
        output += f"DB size: {db_size / 1024 / 1024:.1f} MB\n"
        for col in collections:
            output += f"  - {col.name}: {col.count()} entries\n"
        return {"content": [{"type": "text", "text": output}]}

    elif name == "delete_memory":
        deleted = 0
        if args.get("project"):
            col = get_collection(client, args["project"])
            data = col.get(include=["metadatas"])
            ids = [data["ids"][i] for i, m in enumerate(data["metadatas"]) if m and m.get("project") == args["project"]]
            if ids:
                col.delete(ids=ids)
                deleted += len(ids)
        elif args.get("session_prefix"):
            prefix = args["session_prefix"]
            for col in client.list_collections():
                data = col.get(include=["metadatas"])
                ids = [data["ids"][i] for i, m in enumerate(data["metadatas"]) if m and m.get("session_id", "").startswith(prefix)]
                if ids:
                    col.delete(ids=ids)
                    deleted += len(ids)
        return {"content": [{"type": "text", "text": f"Deleted {deleted} entries."}]}

    return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}]}


# ── MCP stdio loop ─────────────────────────────────────────────────────────

def send_response(response):
    data = json.dumps(response).encode()
    sys.stdout.buffer.write(f"Content-Length: {len(data)}\r\n\r\n".encode())
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def read_message():
    stdin = sys.stdin.buffer
    while True:
        header = b""
        while True:
            byte = stdin.read(1)
            if not byte:
                return None
            header += byte
            if header.endswith(b"\r\n\r\n"):
                break
        length = int(header.decode().split(":")[1].strip())
        body = stdin.read(length)
        if not body:
            return None
        return json.loads(body.decode())


def main():
    while True:
        msg = read_message()
        if msg is None:
            break
        method = msg.get("method", "")
        msg_id = msg.get("id")
        if method == "initialize":
            send_response({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "shokunin-memory", "version": "1.0.0"}
                }
            })
        elif method == "notifications/initialized":
            pass
        elif method == "tools/list":
            send_response({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            tool_name = msg["params"]["name"]
            tool_args = msg["params"].get("arguments", {})
            try:
                result = handle_tool(tool_name, tool_args)
                send_response({"jsonrpc": "2.0", "id": msg_id, "result": result})
            except Exception as e:
                send_response({
                    "jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -1, "message": str(e)}
                })
        elif method == "ping":
            send_response({"jsonrpc": "2.0", "id": msg_id, "result": {}})
        else:
            if msg_id is not None:
                send_response({
                    "jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32601, "message": f"Unknown method: {method}"}
                })


if __name__ == "__main__":
    main()
