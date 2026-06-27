#!/usr/bin/env python3
"""ChromaDB Memory Helper — CLI for managing persistent memory across sessions."""

import argparse
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
BACKUPS_DIR = Path.home() / ".shokunin" / "backups"

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


# ── count ──────────────────────────────────────────────────────────────────
def cmd_count(args):
    client = get_client()
    collections = client.list_collections()
    total = sum(c.count() for c in collections)
    db_size = sum(f.stat().st_size for f in CHROMA_DIR.rglob("*") if f.is_file()) if CHROMA_DIR.exists() else 0
    print(f"Total entries: {total}")
    print(f"Collections:  {len(collections)}")
    print(f"DB size:      {db_size / 1024 / 1024:.1f} MB")


# ── stats ──────────────────────────────────────────────────────────────────
def cmd_stats(args):
    client = get_client()
    collections = client.list_collections()
    if not collections:
        print("No collections found.")
        return
    for col in collections:
        data = col.get(include=["metadatas"])
        metadatas = data.get("metadatas", [])
        types = {}
        projects = {}
        for m in metadatas:
            if m:
                t = m.get("type", "unknown")
                types[t] = types.get(t, 0) + 1
                p = m.get("project", "unknown")
                projects[p] = projects.get(p, 0) + 1
        print(f"\nCollection: {col.name} ({col.count()} entries)")
        print(f"  Types:    {json.dumps(types, indent=4)}")
        print(f"  Projects: {json.dumps(projects, indent=4)}")


# ── search ─────────────────────────────────────────────────────────────────
def cmd_search(args):
    client = get_client()
    collections = client.list_collections()
    if not collections:
        print("No collections found.")
        return
    if args.project:
        collections = [get_collection(client, args.project)]
    where = {"type": args.type} if args.type else None
    all_results = []
    for col in collections:
        if col.count() == 0:
            continue
        results = col.query(
            query_texts=[args.query],
            n_results=min(args.limit, col.count()),
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]
        for doc, meta, dist in zip(docs, metas, dists):
            all_results.append((doc, meta, dist))
    all_results.sort(key=lambda x: x[2])
    if not all_results:
        print("No results found.")
        return
    for i, (doc, meta, dist) in enumerate(all_results[:args.limit], 1):
        score = 1 - dist
        print(f"\n{'='*60}")
        print(f"[{i}] Score: {score:.3f}  Type: {meta.get('type', '?')}  Tags: {meta.get('tags', '')}")
        print(f"    Project: {meta.get('project', '?')}  Session: {meta.get('session_id', '?')}")
        print(f"    Time:    {meta.get('timestamp', '?')}")
        print(f"    {doc[:500]}")


# ── recent ─────────────────────────────────────────────────────────────────
def cmd_recent(args):
    client = get_client()
    project_filter = args.project
    all_entries = []
    for col in client.list_collections():
        data = col.get(include=["documents", "metadatas"])
        docs = data.get("documents", [])
        metas = data.get("metadatas", [])
        for doc, meta in zip(docs, metas):
            if meta:
                if project_filter and meta.get("project") != project_filter:
                    continue
                all_entries.append((doc, meta))
    all_entries.sort(key=lambda x: x[1].get("timestamp", ""), reverse=True)
    for doc, meta in all_entries[:args.limit]:
        print(f"\n[{meta.get('type', '?')}] {meta.get('project', '?')} | {meta.get('session_id', '?')}")
        print(f"  {meta.get('timestamp', '?')}")
        print(f"  {doc[:300]}")


# ── save ───────────────────────────────────────────────────────────────────
def cmd_save(args):
    client = get_client()
    col = get_collection(client, args.project)
    entry_id = f"{args.session_id}-{int(time.time() * 1000)}"
    col.add(
        documents=[args.text],
        ids=[entry_id],
        metadatas=[{
            "type": args.type,
            "tags": args.tags,
            "project": args.project,
            "session_id": args.session_id,
            "timestamp": datetime.now().isoformat()
        }]
    )
    print(f"Saved entry {entry_id}")


# ── delete ─────────────────────────────────────────────────────────────────
def cmd_delete(args):
    client = get_client()
    if args.project:
        col = get_collection(client, args.project)
        data = col.get(include=["metadatas"])
        ids_to_delete = [
            data["ids"][i] for i, m in enumerate(data["metadatas"])
            if m and m.get("project") == args.project
        ]
        if ids_to_delete:
            col.delete(ids=ids_to_delete)
            print(f"Deleted {len(ids_to_delete)} entries for project '{args.project}'")
        else:
            print("No entries found for project.")
    elif args.session_prefix:
        for col in client.list_collections():
            data = col.get(include=["metadatas"])
            ids_to_delete = [
                data["ids"][i] for i, m in enumerate(data["metadatas"])
                if m and m.get("session_id", "").startswith(args.session_prefix)
            ]
            if ids_to_delete:
                col.delete(ids=ids_to_delete)
                print(f"Deleted {len(ids_to_delete)} entries from session '{args.session_prefix}'")


# ── session ────────────────────────────────────────────────────────────────
def cmd_session(args):
    if args.session_cmd == "list":
        sessions = sorted(SESSIONS_DIR.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not sessions:
            print("No sessions found.")
            return
        for s in sessions[:args.limit]:
            size = s.stat().st_size
            mtime = datetime.fromtimestamp(s.stat().st_mtime).isoformat()
            print(f"  {s.stem}  ({size} bytes, {mtime})")

    elif args.session_cmd == "continue" or args.session_cmd == "summary":
        session_file = SESSIONS_DIR / f"{args.session_id}.md"
        if session_file.exists():
            print(session_file.read_text(encoding="utf-8"))
        else:
            # Try searching ChromaDB
            client = get_client()
            for col in client.list_collections():
                data = col.get(
                    include=["documents", "metadatas"],
                    where={"session_id": args.session_id}
                )
                docs = data.get("documents", [])
                metas = data.get("metadatas", [])
                if docs:
                    for doc, meta in zip(docs, metas):
                        print(f"\n[{meta.get('type', '?')}]")
                        print(doc)
                    return
            print(f"Session '{args.session_id}' not found.")

    elif args.session_cmd == "save":
        session_file = SESSIONS_DIR / f"{args.session_id}.md"
        session_file.write_text(args.text, encoding="utf-8")
        print(f"Session saved to {session_file}")

        # Also store in ChromaDB
        client = get_client()
        col = get_collection(client, args.project)
        col.add(
            documents=[args.text],
            ids=[f"session-{args.session_id}"],
            metadatas=[{
                "type": "session_end",
                "tags": args.tags,
                "project": args.project,
                "session_id": args.session_id,
                "timestamp": datetime.now().isoformat()
            }]
        )


# ── verify ─────────────────────────────────────────────────────────────────
def cmd_verify(args):
    client = get_client()
    issues = []
    for col in client.list_collections():
        data = col.get(include=["documents", "metadatas"])
        docs = data.get("documents", [])
        metas = data.get("metadatas", [])
        ids = data.get("ids", [])
        if len(docs) != len(ids):
            issues.append(f"Collection '{col.name}': document count mismatch ({len(docs)} docs vs {len(ids)} ids)")
        for i, (doc, meta) in enumerate(zip(docs, metas)):
            if not doc:
                issues.append(f"Collection '{col.name}': empty document at index {i}")
            if not meta:
                issues.append(f"Collection '{col.name}': missing metadata at index {i}")
    if issues:
        print("Issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("All collections healthy.")
    print(f"\nDB path: {CHROMA_DIR}")
    print(f"Exists:  {CHROMA_DIR.exists()}")


# ── main ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="ChromaDB Memory Helper")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("count", help="Show storage stats")
    sub.add_parser("stats", help="Show detailed stats by type/project")

    p_search = sub.add_parser("search", help="Semantic search")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--project", default="", help="Project filter")
    p_search.add_argument("--limit", type=int, default=10, help="Max results")
    p_search.add_argument("--type", help="Filter by entry type")

    p_recent = sub.add_parser("recent", help="Show recent entries")
    p_recent.add_argument("--limit", type=int, default=10, help="Max entries")
    p_recent.add_argument("--project", help="Filter by project")

    p_save = sub.add_parser("save", help="Save an entry")
    p_save.add_argument("text", help="Entry text")
    p_save.add_argument("session_id", help="Session ID")
    p_save.add_argument("type", help="Entry type")
    p_save.add_argument("tags", help="Comma-separated tags")
    p_save.add_argument("project", help="Project name")

    p_delete = sub.add_parser("delete", help="Delete entries")
    p_delete.add_argument("session_prefix", nargs="?", help="Session ID prefix")
    p_delete.add_argument("--project", help="Delete all entries for project")

    p_verify = sub.add_parser("verify", help="Verify database health")

    p_session = sub.add_parser("session", help="Session management")
    p_session.add_argument("session_cmd", choices=["list", "continue", "summary", "save"])
    p_session.add_argument("session_id", nargs="?", help="Session ID")
    p_session.add_argument("--limit", type=int, default=5, help="Max sessions")
    p_session.add_argument("--text", help="Session text (for save)")
    p_session.add_argument("--project", default="default", help="Project name")
    p_session.add_argument("--tags", default="", help="Tags")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    cmds = {
        "count": cmd_count,
        "stats": cmd_stats,
        "search": cmd_search,
        "recent": cmd_recent,
        "save": cmd_save,
        "delete": cmd_delete,
        "verify": cmd_verify,
        "session": cmd_session,
    }
    cmds[args.command](args)


if __name__ == "__main__":
    main()
