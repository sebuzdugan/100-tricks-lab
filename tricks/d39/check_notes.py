#!/usr/bin/env python3
"""Day 39 (marathon) end check: <workdir> <side>. One line of JSON about the notes file at the end of the marathon:
{"notes":0|1,"notes_lines":N,"notes_bytes":N,"mentions_rules":N}; mentions_rules counts how many of the house rules and
decisions (cents/roundCents, fail/ERRORS, mutate, INV-, clamp/below zero, per line VAT, UTC, formatEuros, normalizeId)
the notes still name. Writes and re-reads per request come from the events (private/m4b/tools/measures.py)."""
import json, re, sys
from pathlib import Path
work = Path(sys.argv[1])
notes = next((p for p in work.iterdir() if p.name.lower() == "notes.md"), None)
text = notes.read_text(errors="replace") if notes else ""
keys = [r"roundCents|integer cents", r"fail\(|ERRORS", r"mutat", r"INV-", r"below zero|clamp", r"per line", r"UTC",
        r"formatEuros", r"normali[sz]eId"]
print(json.dumps({"notes": int(bool(notes)), "notes_lines": len(text.splitlines()), "notes_bytes": len(text.encode()),
                  "mentions_rules": sum(bool(re.search(k, text, re.I)) for k in keys)}, separators=(",", ":")))
