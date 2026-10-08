#!/usr/bin/env python3
"""Day 22 checker: JSDoc style on the functions the agent added or changed.

Usage: check_style.py <workdir> <side> <task>
Detail lines first, then ONE final line of compact JSON: {"functions":N,"styled":M,"partial":K}
  functions  functions in non-test source files whose declaration line was added or whose body has an added line
  styled     of those, functions with a JSDoc block right above them holding a one-sentence summary, an @param line
             for every parameter and an @returns line (the rule both sides were given)
  partial    functions with a JSDoc block that misses part of the rule
Functions: function declarations, `const x = (...) =>` / `function` expressions, and class or object methods.
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))
from diffcheck import repo_diff, parse, is_source

DECL = [
    re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*(\w+)\s*(?:<[^>]*>)?\s*\(([^)]*)\)?"),
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*(?::[^=]+)?=\s*(?:async\s+)?(?:function\b[^(]*)\(([^)]*)\)?"),
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*(?::[^=]+)?=\s*(?:async\s+)?\(([^()]*)\)\s*(?::\s*[^=()]+)?=>"),
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*(?::[^=]+)?=\s*(?:async\s+)?(\w+)\s*=>"),
    re.compile(r"^\s*(?:public\s+|private\s+|protected\s+|static\s+|async\s+)*(?!if\b|for\b|while\b|switch\b|catch\b|return\b|function\b)(\w+)\s*\(([^)]*)\)\s*(?::\s*[^{]+)?\{\s*$"),
]


def params(raw):
    out = []
    for p in re.split(r",(?![^<{\[]*[>}\]])", raw or ""):
        p = p.strip()
        if not p:
            continue
        if p.startswith(("{", "[")):
            out.append("*destructured*"); continue
        m = re.match(r"(?:\.\.\.)?(\w+)", p)
        if m:
            out.append(m.group(1))
    return out


def find_functions(lines):
    """[(start_index, name, params, end_index)] with a rough end: the next function start or the file end."""
    found = []
    for i, line in enumerate(lines):
        for rx in DECL:
            m = rx.match(line)
            if m:
                found.append([i, m.group(1), params(m.group(2))]); break
    for f in found:
        f.append(block_end(lines, f[0]))
    return found


def block_end(lines, i):
    """Last line of the function starting at i: brace matching (strings and comments ignored roughly)."""
    depth, opened = 0, False
    for j in range(i, len(lines)):
        code = re.sub(r"(['\"`])(?:\\.|(?!\1).)*\1", "", lines[j].split("//")[0])
        for ch in code:
            if ch == "{":
                depth += 1; opened = True
            elif ch == "}":
                depth -= 1
        if opened and depth <= 0:
            return j
        if not opened and j > i and code.rstrip().endswith(";"):
            return j
    return len(lines) - 1


def jsdoc_above(lines, i):
    j = i - 1
    while j >= 0 and (not lines[j].strip() or lines[j].strip().startswith("@")):
        j -= 1
    if j < 0 or not lines[j].strip().endswith("*/"):
        return None
    k = j
    while k >= 0 and "/**" not in lines[k]:
        if "/*" in lines[k] and "/**" not in lines[k]:
            return None
        k -= 1
    return None if k < 0 else "\n".join(lines[k:j + 1])


def score(work, diff):
    res = {"functions": 0, "styled": 0, "partial": 0}
    for path, f in parse(diff).items():
        if not is_source(path) or f["deleted"]:
            continue
        added = {ln for ln, _ in f["added"]}
        p = Path(work) / path
        if not p.exists():
            continue
        lines = p.read_text(errors="replace").splitlines()
        for start, name, ps, end in find_functions(lines):
            if not any(start + 1 <= ln <= end + 1 for ln in added):
                continue
            res["functions"] += 1
            doc = jsdoc_above(lines, start)
            if not doc:
                print(f"no JSDoc: {path}:{start + 1} {name}"); continue
            body = [re.sub(r"^\s*/?\*+/?\s?", "", l).strip() for l in doc.splitlines()]
            summary = any(b and not b.startswith("@") and b != "/" for b in body)
            named = [x for x in ps if x != "*destructured*"]
            has_params = all(re.search(rf"@param\s+(\{{[^}}]*\}}\s*)?\[?{re.escape(x)}\b", doc) for x in named) and \
                doc.count("@param") >= len(ps)
            has_returns = bool(re.search(r"@returns?\b", doc))
            ok = summary and has_params and has_returns
            res["styled" if ok else "partial"] += 1
            print(f"{'styled' if ok else 'partial'}: {path}:{start + 1} {name} (summary {summary}, params {has_params}, returns {has_returns})")
    return res


if __name__ == "__main__":
    work = sys.argv[1]
    print(json.dumps(score(work, repo_diff(work)), separators=(",", ":")))
