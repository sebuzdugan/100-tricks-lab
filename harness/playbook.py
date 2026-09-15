#!/usr/bin/env python3
"""The Playbook: every tested trick, kept, cut or optional, built only from real results.

  python3 harness/playbook.py              # the Playbook so far, grouped by module (markdown)
  python3 harness/playbook.py thread M3    # the module's X thread: opener, one line per posted day, recap

Reads private/playbook.json (written by fill_script.py after each real fill), private/scripts.json
(rules and X module threads) and private/course.json (module questions, lessons).
"""
import json
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
pb = {int(k): v for k, v in json.loads((LAB / "private/playbook.json").read_text()).items()} if (LAB / "private/playbook.json").exists() else {}
plan = {d["day"]: d for d in json.loads((LAB / "plan/days.json").read_text())["days"]}
course = json.loads((LAB / "private/course.json").read_text())
threads = json.loads((LAB / "private/x_module_threads.json").read_text()) if (LAB / "private/x_module_threads.json").exists() else {}
MODS = list(course["module_questions"])
MARK = {"kept": "KEEP", "cut": "CUT", "optional": "OPTIONAL", "none": "NOTE"}


def playbook():
    out = ["# The Playbook", ""]
    tot = {"kept": 0, "cut": 0, "optional": 0}
    for m in MODS:
        days = [d for d in sorted(pb) if plan[d]["module"] == m]
        out += [f"## {m}: {course['module_questions'][m]}", ""]
        if not days:
            out += ["No results yet.", ""]
            continue
        for d in days:
            e = pb[d]; tot[e["category"]] = tot.get(e["category"], 0) + 1
            out.append(f"- **{MARK[e['category']]}** {e['rule']} (day {d}, {e['verdict']})")
        out.append("")
    out.append(f"Totals: {tot['kept']} kept, {tot['cut']} cut, {tot['optional']} optional.")
    return "\n".join(out)


def thread(mod_key):
    m = next(x for x in MODS if x.split()[0] == mod_key)
    t = threads.get(m, {})
    posts = [t.get("opener", f"{m}: {course['module_questions'][m]}")]
    n = {"kept": 0, "cut": 0, "optional": 0}
    for d in sorted(pb):
        if plan[d]["module"] != m:
            continue
        e = pb[d]; n[e["category"]] = n.get(e["category"], 0) + 1
        posts.append(f"Day {d}: {plan[d]['trick']}. {MARK[e['category']].capitalize()}: {e['rule']}")
    closer = t.get("closer", "")
    if closer:
        closer = closer.replace("{module_kept}", str(n["kept"])).replace("{module_cut}", str(n["cut"])).replace("{module_optional}", str(n["optional"]))
        posts.append(closer)
    return "\n\n---\n\n".join(posts)


if __name__ == "__main__":
    print(thread(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "thread" else playbook())
