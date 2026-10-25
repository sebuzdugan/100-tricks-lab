#!/usr/bin/env python3
"""Tally the four bugs per side from a run folder's runs.csv (the BUGS fields in grade_reason). Read-only.

  python3 tasks/m5-weekly-plans/bugs_table.py runs/pilot-m5fix [runs/other ...]
"""
import csv, re, sys
from collections import Counter, defaultdict
from pathlib import Path

KEYS = ("core", "B1", "B2", "B3", "B4")


def fields(reason):
    m = re.search(r"BUGS (.*?)(?: ::|$)", reason or "")
    return dict(kv.split("=", 1) for kv in m.group(1).split() if "=" in kv) if m else {}


for d in sys.argv[1:]:
    rows = [r for r in csv.DictReader(open(Path(d) / "runs.csv")) if r["task"] == "m5-weekly-plans" and not r["infra_error"]]
    by = defaultdict(list)
    for r in rows:
        by[r["side"]].append((r, fields(r["grade_reason"])))
    print(f"\n{d}")
    print(f"  {'side':8} {'n':>2} {'ALL4':>5} " + " ".join(f"{k:>5}" for k in KEYS) + "  cheats / b4 kinds / suite red / timeouts / models")
    for side, items in sorted(by.items()):
        n = len(items)
        all4 = sum(1 for r, f in items if r["passed"] == "True")
        cnt = {k: sum(1 for _, f in items if f.get(k) == "pass") for k in KEYS}
        cheats = Counter(f.get("cheat", "?") for _, f in items if f.get("cheat") not in (None, "none"))
        b4 = Counter(f.get("b4") for _, f in items)
        red = sum(1 for _, f in items if f.get("suite") == "red")
        to = sum(1 for r, _ in items if r["timeout"] == "True")
        models = Counter(r["models"] for r, _ in items)
        print(f"  {side:8} {n:>2} {all4:>5} " + " ".join(f"{cnt[k]:>5}" for k in KEYS)
              + f"  {dict(cheats) or '-'} / {dict(b4)} / {red} / {to} / {dict(models)}")
