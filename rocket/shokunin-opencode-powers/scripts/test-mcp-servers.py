#!/usr/bin/env python3
"""Test all MCP servers in the shokunin-opencode-powers package."""
import subprocess, json, sys, os

def test_mcp(name, cmd, timeout=15):
    try:
        init_msg = json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}})
        payload = f"Content-Length: {len(init_msg.encode())}\r\n\r\n{init_msg}"
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        try:
            stdout, stderr = proc.communicate(input=payload.encode(), timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill(); stdout, stderr = proc.communicate()
            return "SLOW", f"Running (>{timeout}s)"
        
        stdout_str = stdout.decode(errors="replace")
        stderr_str = stderr.decode(errors="replace")
        
        if "Content-Length:" in stdout_str:
            for part in stdout_str.split("Content-Length:")[1:]:
                try:
                    end = part.index("\r\n\r\n")
                    length = int(part[:end])
                    body = part[end+4:end+4+length]
                    r = json.loads(body)
                    if "result" in r:
                        si = r["result"].get("serverInfo", {})
                        return "PASS", f"{si.get('name','?')} v{si.get('version','?')}"
                except:
                    pass
        
        if stderr_str.strip():
            return "PARTIAL", f"Running ({stderr_str[:80]})"
        return "FAIL", "No response"
    except Exception as e:
        return "ERROR", str(e)[:100]

tests = [
    ("shokunin-memory", "python ~/.shokunin/memory/mcp-server.py"),
    ("github", "npx -y @modelcontextprotocol/server-github"),
    ("google-workspace", "npx -y google-tools-mcp"),
    ("claude-screen", "npx -y claude-screen-mcp"),
    ("playwright", "npx @playwright/mcp@latest"),
    ("computer-use", "computer-use-mcp"),
    ("obsidian", "npx @bitbonsai/mcpvault@latest"),
    ("darbot-windows", "darbot-windows-mcp"),
    ("weather", "npx -y @dangahagan/weather-mcp@latest"),
    ("mcp-notifications", "npx -y @topvisor/mcp-notifications"),
    ("mcp-personal-suite", "npx -y mcp-personal-suite"),
    ("neo-mcp", "neo-mcp-daemon --mcp"),
    ("youtube", "npx -y @eat-pray-ai/yutu mcp"),
]

print("=" * 50)
print(" MCP Server Test - Shokunin OpenCode Powers")
print("=" * 50)
print()

passed = 0
failed = 0
for name, cmd in tests:
    status, detail = test_mcp(name, cmd)
    icon = {"PASS": "[OK]", "PARTIAL": "[--]", "SLOW": "[~~]", "FAIL": "[XX]", "ERROR": "[!!]"}.get(status, "[??]")
    color = {"PASS": "green", "PARTIAL": "yellow", "SLOW": "yellow", "fail": "red", "ERROR": "red"}.get(status, "white")
    print(f"  {icon} {name:20s} {detail}")
    if status == "PASS": passed += 1
    else: failed += 1

print()
print(f"Results: {passed} passed, {failed} need attention")
print("=" * 50)
