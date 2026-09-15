#!/usr/bin/env python3
"""Fill a day's Short script with the real result, after the runs.

  python3 harness/fill_script.py d01                      # verdict and numbers from runs/d01/summary.json
  python3 harness/fill_script.py d47 --variant planted_edits --set edits=3
  python3 harness/fill_script.py d01 --preview works       # no results yet: fill with example numbers to rehearse

Scripts live in private/scripts.json (not committed: they are unpublished content). Each script has fixed beats,
one `takeaway` slot and verdict variants. This picks the variant, fills the placeholders (spoken words in `voice`,
digits in `screen`) and writes private/out/dNN/:
  script.md       what Sebi reads, beat by beat, with on-screen text and visuals
  prompter.json   one entry for the yt-short-voicematch teleprompter SCRIPTS array
  beats.json      voice + on_screen per beat, a starting point for the voicematch project

It refuses inconclusive results (they are rerun, never posted).
"""
import argparse
import json
import re
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
VERDICT_KEY = {"works": "works", "no difference": "no_difference", "hurts": "hurts"}
ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def words(n: int) -> str:
    if n < 0:
        return "minus " + words(-n)
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("" if n % 10 == 0 else "-" + ONES[n % 10])
    if n < 1000:
        return ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " and " + words(n % 100))
    return str(n)


def minutes_voice(m: float) -> str:
    if m < 1:
        return "under a minute"
    r = round(m)
    return "about a minute" if r == 1 else f"about {words(r)} minutes"


def cost_voice(c: float) -> str:
    if c <= 0:
        return "nothing"
    if c < 1:
        cents = max(5, int(round(c * 100 / 5) * 5))
        return "about a dollar" if cents >= 100 else f"about {words(cents)} cents"
    d, cents = int(c), int(round((c - int(c)) * 10)) * 10
    if cents == 100:
        d, cents = d + 1, 0
    base = "a dollar" if d == 1 else f"{words(d)} dollars"
    return f"about {base}" + (f" {words(cents)}" if cents else "")


def ratio_phrase(a: float, b: float, better: str, worse: str, same: str, spoken: bool) -> str:
    if not b:
        return same
    t = a / b
    pct = int(round(abs(1 - t) * 100 / 5) * 5)
    if pct < 10:
        return same
    if t < 1:
        return f"about {words(pct)} percent {better}" if spoken else f"{pct}% {better}"
    if t >= 1.95:
        k = int(round(t))
        mult = "twice" if k == 2 else f"{words(k)} times"
        if not spoken:
            return f"{round(t, 1)}x {'longer' if worse == 'time' else 'the cost'}"
        return f"about {mult} as long" if worse == "time" else f"about {mult} the cost"
    return f"about {words(pct)} percent {'slower' if worse == 'time' else 'more expensive'}" if spoken else f"{pct}% {'slower' if worse == 'time' else 'costlier'}"


def values(summary: dict, spoken: bool, extra: dict) -> dict:
    w, o = summary["with"], summary["without"]
    num = (lambda n: words(int(n))) if spoken else (lambda n: str(int(n)))
    dp = w["passed"] - o["passed"]
    if dp == 0:
        gap = "the same number of passes"
    elif abs(dp) == 1:
        gap = "one more passing run" if dp > 0 else "one fewer passing run"
    else:
        gap = f"{words(abs(dp))} {'more' if dp > 0 else 'fewer'} passing runs" if spoken else f"{abs(dp)} {'more' if dp > 0 else 'fewer'} passes"
    v = {
        "with_passed": num(w["passed"]), "with_total": num(w["graded"]),
        "without_passed": num(o["passed"]), "without_total": num(o["graded"]),
        "runs_total": num(w["graded"] + o["graded"]),
        "with_minutes": minutes_voice(w["avg_minutes"]) if spoken else f"{w['avg_minutes']:.1f} min",
        "without_minutes": minutes_voice(o["avg_minutes"]) if spoken else f"{o['avg_minutes']:.1f} min",
        "with_cost": cost_voice(w["avg_cost_usd"]) if spoken else f"${w['avg_cost_usd']:.2f}",
        "without_cost": cost_voice(o["avg_cost_usd"]) if spoken else f"${o['avg_cost_usd']:.2f}",
        "pass_gap_phrase": gap,
        "time_phrase": ratio_phrase(w["avg_minutes"], o["avg_minutes"], "faster", "time", "about the same time", spoken),
        "cost_phrase": ratio_phrase(w["avg_cost_usd"], o["avg_cost_usd"], "cheaper", "cost", "about the same cost", spoken),
    }
    for k, val in extra.items():
        v[k] = words(int(val)) if spoken and re.fullmatch(r"-?\d+", str(val)) else str(val)
    return v


def fill(text: str, v: dict, day: str) -> str:
    def sub(m):
        k = m.group(1)
        if k not in v:
            sys.exit(f"{day}: placeholder {{{k}}} has no value. Pass it with --set {k}=VALUE")
        return v[k]
    return re.sub(r"\{(\w+)\}", sub, text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("day")
    ap.add_argument("--variant", help="takeaway key to use (required for custom days)")
    ap.add_argument("--set", action="append", default=[], help="extra placeholder, name=value")
    ap.add_argument("--preview", choices=["works", "no_difference", "hurts"], help="fill with example numbers, before results exist")
    a = ap.parse_args()
    tid = a.day if a.day.startswith("d") else f"d{int(a.day):02d}"
    day = int(tid[1:])
    scripts = {s["day"]: s for s in json.loads((LAB / "private" / "scripts.json").read_text())["scripts"]}
    s = scripts.get(day) or sys.exit(f"no script for day {day} in private/scripts.json")
    extra = dict(x.split("=", 1) for x in a.set)

    if a.preview:
        sample = {"works": (8, 5, 3.1, 4.4, 0.42, 0.61), "no_difference": (6, 6, 4.0, 4.1, 0.5, 0.52), "hurts": (4, 7, 5.9, 4.0, 0.9, 0.55)}[a.preview]
        summary = {"verdict": a.preview.replace("_", " "), "with": {"passed": sample[0], "graded": 9, "avg_minutes": sample[2], "avg_cost_usd": sample[4]},
                   "without": {"passed": sample[1], "graded": 9, "avg_minutes": sample[3], "avg_cost_usd": sample[5]}}
        print("PREVIEW with example numbers. Do not record this.")
    else:
        p = LAB / "runs" / tid / "summary.json"
        if not p.exists():
            sys.exit(f"no results yet: {p}. Run python3 harness/run.py {tid}, or use --preview to rehearse.")
        summary = json.loads(p.read_text())
        if summary["verdict"] == "inconclusive":
            sys.exit("verdict is inconclusive: rerun before scripting the result")

    key = a.variant or (VERDICT_KEY.get(summary["verdict"]) if s.get("variant_rule", "standard verdict") == "standard verdict" else None)
    if not key:
        sys.exit(f"{tid} needs --variant. Rule: {s.get('variant_rule')}. Keys: {', '.join(s['takeaways'])}")
    if key not in s["takeaways"]:
        sys.exit(f"unknown variant {key}. Keys: {', '.join(s['takeaways'])}")
    vs, vd = values(summary, True, extra), values(summary, False, extra)

    beats = []
    for b in s["beats"]:
        src = s["takeaways"][key] if b["role"] == "takeaway" else b
        beats.append({"role": b["role"], "voice": fill(src["voice"], vs, tid), "screen": fill(src.get("screen", ""), vd, tid),
                      "visual": fill(src.get("visual", ""), vd, tid)})
    n_words = sum(len(b["voice"].split()) for b in beats)
    out = LAB / "private" / "out" / tid
    out.mkdir(parents=True, exist_ok=True)
    md = [f"# Day {day}: {s['title']}", "", f"First frame: **{s['hook_screen']}** · {n_words} words · about {round(n_words / 2.4)} s · variant `{key}`", ""]
    for i, b in enumerate(beats):
        md += [f"**{i}. {b['role']}**  ", b["voice"], f"*Screen:* {b['screen']} · *Visual:* {b['visual']}", ""]
    md += [f"Pinned comment: {s.get('pinned_comment', '')}", "", s.get("notes", "")]
    (out / "script.md").write_text("\n".join(md).rstrip() + "\n")
    (out / "prompter.json").write_text(json.dumps({"id": tid, "name": s["title"], "dur": round(n_words / 2.4),
                                                   "beats": [b["voice"] for b in beats]}, ensure_ascii=False, indent=2))
    (out / "beats.json").write_text(json.dumps({"title": s["title"], "beats": [
        {"section": b["role"], "voice": b["voice"], "on_screen": b["screen"], "visual_note": b["visual"]} for b in beats]},
        ensure_ascii=False, indent=2))
    print("\n".join(md))
    print(f"\nwrote {out.relative_to(LAB)}/script.md, prompter.json, beats.json")


if __name__ == "__main__":
    main()
