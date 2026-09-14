#!/usr/bin/env python3
"""Render the day cards (1600x900 PNG + SVG) used on X, Notion and the plan page.

  python3 harness/render_cards.py                 # all 100 days from plan/days.json
  python3 harness/render_cards.py 7 12            # only these days

Each card: day and module, the trick name, and two panels, with the trick and without it. Each panel has one
Lucide icon and a pip per run. Pips stay hollow until runs/dNN/summary.json exists, then passed runs are filled,
so the same card shows the result after the test day.

Icons come from assets/icons/ (Lucide, ISC licence). Rendering needs rsvg-convert (brew install librsvg).
"""
import html
import json
import re
import subprocess
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
ICONS = LAB / "assets" / "icons"
OUT = LAB / "assets" / "cards"
W, H = 1600, 900
BG, PANEL, LINE, INK, MUTED, LIME, MISS = "#08090a", "#111316", "#262a2e", "#f2f4f5", "#8b9299", "#c5f24e", "#5a6068"
FONT = "Inter, 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'SF Mono', Menlo, monospace"


def icon(name, x, y, size, color, stroke_px=5.0):
    src = (ICONS / f"{name}.svg").read_text()
    inner = re.search(r"<svg[^>]*>(.*)</svg>", src, re.S).group(1)
    inner = re.sub(r"<!--.*?-->", "", inner, flags=re.S)
    s = size / 24
    return (f'<g transform="translate({x},{y}) scale({s})" fill="none" stroke="{color}" '
            f'stroke-width="{stroke_px / s:.2f}" stroke-linecap="round" stroke-linejoin="round">{inner}</g>')


def wrap(text, limit):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > limit and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return lines + [cur]


def pips(x, y, total, passed, color):
    cols = 9 if total > 9 else total
    out, r, gap = [], 11, 34
    for i in range(total):
        cx, cy = x + (i % cols) * gap, y + (i // cols) * gap
        if passed is not None and i < passed:
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>')
        else:
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{r - 1.5}" fill="none" stroke="{MISS}" stroke-width="3"/>')
    return "".join(out)


def card(d):
    day, e = d["day"], html.escape
    ill = d.get("illustration") or {}
    runs = int(d.get("runs_per_side") or 9)
    d = {**d, "run_mode": d.get("run_mode")}
    res = d.get("results")
    title = wrap(d["trick"], 30)[:2]
    size = 84 if max(len(t) for t in title) <= 22 else 72
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{BG}"/>',
             f'<text x="96" y="130" font-family="{MONO}" font-size="30" letter-spacing="3" fill="{LIME}">DAY {day:02d} / 100</text>',
             f'<text x="{W - 96}" y="130" text-anchor="end" font-family="{MONO}" font-size="26" letter-spacing="2" fill="{MUTED}">{e(d["module"].upper())}</text>']
    ty = 250
    for i, t in enumerate(title):
        parts.append(f'<text x="96" y="{ty + i * (size + 14)}" font-family="{FONT}" font-weight="700" font-size="{size}" fill="{INK}">{e(t)}</text>')
    label_y = ty + (len(title) - 1) * (size + 14) + 70
    if ill.get("label"):
        parts.append(f'<text x="96" y="{label_y}" font-family="{MONO}" font-size="32" fill="{MUTED}">{e(ill["label"])}</text>')
    top = label_y + 70
    pw, ph, gap = 660, H - top - 110, 88
    for k, (side, label, name, color) in enumerate([
        ("WITH", "the trick", ill.get("icon", "flask-conical"), LIME),
        ("WITHOUT", "without it", ill.get("icon_alt", "circle-x"), MUTED)]):
        px = 96 + k * (pw + gap)
        parts.append(f'<rect x="{px}" y="{top}" width="{pw}" height="{ph}" rx="18" fill="{PANEL}" stroke="{LINE}" stroke-width="2"/>')
        isz = min(96, ph - 70)
        parts.append(icon(name, px + 40, top + (ph - isz) / 2, isz, color))
        tx = px + 40 + isz + 36
        parts.append(f'<text x="{tx}" y="{top + 62}" font-family="{MONO}" font-size="30" letter-spacing="4" fill="{color}">{side}</text>')
        passed = res[side.lower()]["passed"] if res else None
        parts.append(pips(tx + 11, top + ph - 46 - (34 if runs > 9 else 0), runs, passed, color))
    parts.append(f'<text x="{96 + pw + gap / 2}" y="{top + ph / 2 + 12}" text-anchor="middle" font-family="{MONO}" font-size="30" fill="{MUTED}">vs</text>')
    unit = "run" if runs == 1 else "runs"
    foot = f"{d.get('task_note') or '3 tasks'} · {runs} {unit} a side" + (" · run by hand" if d.get("run_mode") == "Interactive" else "")
    parts.append(f'<text x="96" y="{H - 52}" font-family="{MONO}" font-size="24" fill="{MUTED}">{e(foot)}</text>')
    parts.append(f'<text x="{W - 96}" y="{H - 52}" text-anchor="end" font-family="{MONO}" font-size="24" fill="{MUTED}">github.com/sebuzdugan/100-tricks-lab</text>')
    parts.append("</svg>")
    return "".join(parts)


def main():
    plan = json.loads((LAB / "plan" / "days.json").read_text())["days"]
    bp = LAB / "plan" / "briefs.json"
    ill = {b["day"]: b["brief"]["illustration"] for b in json.loads(bp.read_text())["days"]} if bp.exists() else {}
    plan = [{**d, "illustration": ill.get(d["day"])} for d in plan]
    want = {int(a) for a in sys.argv[1:]}
    OUT.mkdir(parents=True, exist_ok=True)
    for d in plan:
        if want and d["day"] not in want:
            continue
        s = LAB / "runs" / f"d{d['day']:02d}" / "summary.json"
        if s.exists():
            j = json.loads(s.read_text())
            d = {**d, "results": {"with": {"passed": j["with"]["passed"]}, "without": {"passed": j["without"]["passed"]}},
                 "runs_per_side": j["with"]["graded"]}
        svg = OUT / f"d{d['day']:02d}.svg"
        svg.write_text(card(d))
        subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H), "-o", str(svg.with_suffix(".png")), str(svg)], check=True)
        print("OK", svg.with_suffix(".png").relative_to(LAB))


if __name__ == "__main__":
    main()
