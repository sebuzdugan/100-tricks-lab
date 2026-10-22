#!/usr/bin/env bash
# Install the pinned Context7 MCP server (4.1.1, from context7/package-lock.json) where day 36's --mcp-config points.
# Started through `npx -y` it took 24-70 s to come up (4 runs in parallel), past Claude Code's MCP start-up wait, and
# 2 of 4 pilot runs started with the server 'failed'; started with node from this install it answers in 0.1 s.
# /private/tmp is cleared on reboot: run this before day 36 (it is idempotent). Needs npm and network.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST=/private/tmp/100-tricks-runs/_tools/context7-mcp-4.1.1
mkdir -p "$DEST" && cp "$HERE/context7/package.json" "$HERE/context7/package-lock.json" "$DEST/"
(cd "$DEST" && npm ci --silent --no-audit --no-fund)
JS="$DEST/node_modules/@upstash/context7-mcp/dist/index.js"
python3 - "$JS" <<'PY'
import json, subprocess, sys, time
t = time.time()
p = subprocess.Popen(["node", sys.argv[1]], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "lab", "version": "0"}}}) + "\n"); p.stdin.flush()
r = json.loads(p.stdout.readline()); p.kill()
v = r["result"]["serverInfo"]["version"]; dt = time.time() - t
assert v == "4.1.1" and dt < 5, (v, dt)
print(f"context7-mcp {v} ready in {dt:.1f}s at {sys.argv[1]}")
PY
