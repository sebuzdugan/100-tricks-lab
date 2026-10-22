#!/usr/bin/env bash
# Acceptance for a7-order-agent (docs fixture, AI SDK 7). Usage: accept.sh <workdir>. Exit 0 = pass.
set -u
TASK=a7-order-agent
LOGDIR="${LAB_LOG_DIR:-$(mktemp -d -t lab-logs)}"; mkdir -p "$LOGDIR"
W="$(cd "$1" && pwd)"; H="$(cd "$(dirname "$0")" && pwd)/hidden"
source "$(cd "$(dirname "$0")/../.." && pwd)/fixtures/docs-aisdk7/grade_common.sh"
[ -f "$W/src/order-agent.js" ] || fail "src/order-agent.js missing"
run_hidden
echo "PASS a7-order-agent"
