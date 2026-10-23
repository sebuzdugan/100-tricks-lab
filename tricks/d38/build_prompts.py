#!/usr/bin/env python3
"""Day 38: save the AI SDK 7 docs pages (once, dated) and build the paste side's prompt files.
  python3 tricks/d38/build_prompts.py --fetch   # download the pages into docs/ and record date, URL, sha256 in docs/MANIFEST.json
  python3 tricks/d38/build_prompts.py           # rebuild prompts/with/<task>.md from the saved copies (no network)
The paste side gets the saved pages, then the unchanged task prompt. The fetch side gets 'Docs: <url>' lines for the
same pages (prompt_prefix_by_task in trick.json), plus WebFetch and WebSearch."""
import hashlib, json, re, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent.parent
PAGES = {
    "a7-order-agent": ["https://ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling", "https://ai-sdk.dev/docs/ai-sdk-core/runtime-and-tool-context"],
    "a7-ticket-triage": ["https://ai-sdk.dev/docs/ai-sdk-core/generating-structured-data"],
    "a7-stream-reply": ["https://ai-sdk.dev/docs/ai-sdk-core/generating-text", "https://ai-sdk.dev/docs/foundations/prompts"],
    "a7-upgrade-legacy": ["https://ai-sdk.dev/docs/migration-guides/migration-guide-7-0"],
}
fname = lambda url: url.split("/docs/", 1)[1].replace("/", "__") + ".md"

def fetch():
    man = {}
    for url in sorted({u for us in PAGES.values() for u in us}):
        with urllib.request.urlopen(url + ".md", timeout=60) as r:
            body = r.read()
        (HERE / "docs" / fname(url)).write_bytes(body)
        man[url] = {"file": "docs/" + fname(url), "fetched": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "source": url + ".md",
                    "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
    (HERE / "docs" / "MANIFEST.json").write_text(json.dumps(man, indent=1) + "\n")

def clean(md: str) -> str:
    md = re.sub(r"\A---\n.*?\n---\n", "", md, flags=re.S)  # front matter
    md = re.sub(r"^> For an index of all documentation, see \[/llms\.txt\]\(/llms\.txt\)\.\n", "", md, flags=re.M)
    return md.strip() + "\n"

def build():
    man = json.loads((HERE / "docs" / "MANIFEST.json").read_text())
    trick = json.loads((HERE / "trick.json").read_text())
    for task, urls in PAGES.items():
        parts = []
        for url in urls:
            raw = (HERE / man[url]["file"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == man[url]["sha256"], f"saved copy changed: {url}"
            parts.append(f"=== {url} ===\n\n" + clean(raw.decode()))
        head = "Docs for the Vercel AI SDK 7 (ai 7.0.128), copied from ai-sdk.dev:\n\n"
        body = head + "\n".join(parts) + "\n---\n\n" + (LAB / "tasks" / task / "prompt.md").read_text()
        out = HERE / "prompts" / "with" / f"{task}.md"
        out.write_text(body)
        prefix = "".join(f"Docs: {u}\n" for u in urls) + "\n"
        assert trick["sides"]["without"]["prompt_prefix_by_task"][task] == prefix, f"fetch-side prefix out of sync for {task}"
        print(f"{task}: {len(body)} chars (~{len(body)//4} tokens) from {len(urls)} page(s)")

if __name__ == "__main__":
    if "--fetch" in sys.argv:
        fetch()
    build()
