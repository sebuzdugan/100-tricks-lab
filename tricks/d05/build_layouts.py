#!/usr/bin/env python3
"""Builds both day 5 layouts from lines.md, then checks them. Usage:

  python3 tricks/d05/build_layouts.py           # write with/ and without/, then check
  python3 tricks/d05/build_layouts.py --check   # only check the files already on disk

lines.md is written once. Each block starts with a tag line: `@root`, or `@packages/<folder>` for a package.

  with/     CLAUDE.md holds the root block; packages/<folder>/CLAUDE.md holds each package block.
  without/  CLAUDE.md holds every block, root first, then the packages in lines.md order, each package
            under its own heading (the heading is the first line of its block, identical in both layouts).

The check: the without/ file must equal the with/ files joined in the same order with one blank line between
them, so both sides carry the same lines, the same wording and the same number of non-blank lines.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent / "base" / "frai"


def parse():
    blocks, tag, buf = [], None, []
    for line in (HERE / "lines.md").read_text().splitlines():
        if line.startswith("@"):
            if tag:
                blocks.append((tag, "\n".join(buf).strip("\n")))
            tag, buf = line[1:].strip(), []
        else:
            buf.append(line)
    if tag:
        blocks.append((tag, "\n".join(buf).strip("\n")))
    return blocks


def target(tag):
    return Path("CLAUDE.md") if tag == "root" else Path(tag) / "CLAUDE.md"


def build(blocks):
    for tag, text in blocks:
        if tag != "root" and not (BASE / tag / "package.json").exists():
            sys.exit(f"{tag} is not a package folder in base/frai")
        out = HERE / "with" / target(tag)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n")
    combined = HERE / "without" / "CLAUDE.md"
    combined.parent.mkdir(parents=True, exist_ok=True)
    combined.write_text("\n\n".join(text for _, text in blocks) + "\n")


def check(blocks):
    errors = []
    tags = [t for t, _ in blocks]
    if tags.count("root") != 1 or tags[0] != "root":
        errors.append("lines.md must start with exactly one @root block")
    with_files = [HERE / "with" / target(t) for t in tags]
    on_disk = sorted(p.relative_to(HERE / "with") for p in (HERE / "with").rglob("CLAUDE.md"))
    if on_disk != sorted(target(t) for t in tags):
        errors.append(f"with/ has unexpected CLAUDE.md files: {on_disk}")
    without_files = sorted(p.relative_to(HERE / "without") for p in (HERE / "without").rglob("*") if p.is_file())
    if without_files != [Path("CLAUDE.md")]:
        errors.append("without/ must contain only CLAUDE.md")
    split_text = "\n\n".join(p.read_text().rstrip("\n") for p in with_files if p.exists()) + "\n"
    combined_text = (HERE / "without" / "CLAUDE.md").read_text()
    if split_text != combined_text:
        errors.append("without/CLAUDE.md does not equal the with/ files joined in order")
    nb = lambda text: [l for l in text.splitlines() if l.strip()]
    split_lines, combined_lines = nb(split_text), nb(combined_text)
    if split_lines != combined_lines:
        errors.append("non-blank lines differ between layouts")
    for tag, text in blocks:
        p = HERE / "with" / target(tag)
        if not p.exists() or p.read_text() != text + "\n":
            errors.append(f"{p.relative_to(HERE)} does not match its block in lines.md")
    print(f"with: {len(with_files)} files, {len(split_lines)} non-blank lines "
          f"({', '.join(f'{target(t)}: {len(nb(x))}' for t, x in blocks)})")
    print(f"without: 1 file, {len(combined_lines)} non-blank lines, {len(combined_text.splitlines())} lines in total")
    if errors:
        print("\n".join("ERROR " + e for e in errors))
        sys.exit(1)
    print("OK: both layouts carry the same lines in the same order")


if __name__ == "__main__":
    blocks = parse()
    if "--check" not in sys.argv:
        build(blocks)
    check(blocks)
