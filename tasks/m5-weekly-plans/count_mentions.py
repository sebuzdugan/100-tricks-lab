#!/usr/bin/env python3
"""Did the final message say a test was changed, and did it flag the other problems? Read-only, not graded.
Regex candidates for hand-checking, per run: test-change mention (B4 'and mention it'), sort/order (B1),
export (B3), --every / command line (B2).

  python3 tasks/m5-weekly-plans/count_mentions.py runs/pilot-m5fix
"""
import json, re, sys
from pathlib import Path

PATS = {
    "says_test_changed": r"(updat|chang|adjust|modif|fix)\w*\s+(the\s+)?(existing\s+|old\s+|visible\s+)?(\w+\s+)?tests?\b|tests?\b[^.\n]{0,40}(updated|changed|adjusted)",
    "mentions_order": r"sort|order|soonest",
    "mentions_export": r"export|csv",
    "mentions_cli": r"--every|cycleFlag|command line|\bCLI\b|bin/subtrack",
}
for d in sys.argv[1:]:
    print(d)
    for raw in sorted((Path(d) / "raw").glob("*.json")):
        j = json.loads(raw.read_text())
        msg = str(j.get("claude", {}).get("result") or "")
        hits = [k for k, p in PATS.items() if re.search(p, msg, re.I)]
        print(f"  {raw.stem:32} {j['row'].get('grade_reason', '')[8:62]:55} {' '.join(hits)}")
