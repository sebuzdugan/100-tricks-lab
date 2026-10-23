#!/usr/bin/env python3
"""Day 37 extra measure (final repo): console.log calls added per request and the first request that broke the rule.
Usage: check_forget.py <workdir> <side> <task>. The per-turn timeline from the saved events is turn_timeline.py."""
import subprocess, sys
from pathlib import Path
LAB = Path(__file__).resolve().parents[2]
r = subprocess.run([sys.executable, str(LAB / "fixtures" / "forget-log" / "count_logs.py"), sys.argv[1]], capture_output=True, text=True)
print((r.stdout.strip().splitlines() or [f"checker error: {r.stderr.strip()[:150]}"])[-1])
