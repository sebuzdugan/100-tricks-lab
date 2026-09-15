# 100 Tricks Lab

100 viral AI coding tricks, tested on the same real tasks with and without each trick. The rules are in
[PROTOCOL.md](PROTOCOL.md).

## One-time setup

```bash
harness/setup_base.sh                         # rebuilds base/frai from the public frai repo (skip if it exists)
CLAUDE_CONFIG_DIR=~/.claude-lab claude        # opens a clean Claude Code; run /login once, then exit
export LAB_CLAUDE_CONFIG_DIR=~/.claude-lab    # add to your shell profile
```

The clean config folder keeps your own hooks, plugins, agents, commands and memory out of the runs. No API key is
involved: `/login` uses your normal Claude subscription.

## Every test day

```bash
python3 harness/run.py d01 --dry-run          # prepares the copies and confirms the graders fail on the baseline
python3 harness/run.py d01                    # 18 runs, 3 at a time, then prints the verdict
python3 harness/run.py d01 --summarize-only   # re-print the summary
```

Run it from a normal terminal, not from inside another Claude Code session.

After the runs, fill the day's Short script with the real numbers (scripts are private until posted):

```bash
python3 harness/fill_script.py d01            # picks the takeaway from the verdict, writes private/out/d01/
python3 harness/fill_script.py d01 --preview works   # rehearse before results exist
```

Each real fill also records the day's rule in the Playbook: kept (works), cut (hurts) or optional (no difference).
The tally and module recaps in the scripts and X drafts come only from those recorded results:

```bash
python3 harness/playbook.py                   # the Playbook so far, grouped by module
python3 harness/playbook.py thread M2         # a module's X thread: opener, one line per day, recap
```

When the verdict is in, publish the raw runs before the post goes out (the post links to them):

```bash
harness/publish_day.sh d01                    # commits tricks/d01 and runs/d01, pushes, prints the link
```

Outputs land in `runs/d01/`: `runs.csv`, `raw/`, `summary.json` and `result_fragment.json`, which feeds the Notion
scorecard row and the `test-result-crosspost` skill.

## Adding a trick

Create `tricks/dNN/trick.json` (copy `tricks/d01/trick.json`) and put the files that make up the trick in
`tricks/dNN/with/` (or `without/`). Files in an overlay folder are copied into the repo copy before the agent starts.
Use `prompt_prefix`, `model`, `effort` or `extra_args` on a side when the trick is a prompt, model or flag rather
than a file. More side options:

| Field | Use |
|---|---|
| `prompt_prefix_by_task` | `{task: text}` added before one task's prompt |
| `prompt_file_by_task` | `{task: path}` replaces that task's prompt with a file in the trick folder |
| `turns` | follow-up calls in the same session: `[{"prompt": "...", "model": "sonnet"}]` (plan then execute, review then fix) |
| `allowed_tools_extra` | extra tools, e.g. `["Agent"]` or `["WebFetch"]` |
| `permission_mode` | defaults to `acceptEdits` |
| `env` | extra environment, e.g. a local model: `{"ANTHROPIC_BASE_URL": "http://localhost:11434", "ANTHROPIC_AUTH_TOKEN": "ollama"}` |

Trick-level: `tasks`, `runs`, `timeout_min`, `skills` (enables slash commands and skills), `extra_check` (script run on
each finished repo copy, its last output line lands in the `extra` column), `fetch` (third-party files downloaded at a
pinned URL and SHA-256 instead of being committed).

`plan/briefs.json` holds the reviewed brief for every day: exact setup, caveats, clip plan, sources. Day cards live in
`assets/cards/` (`python3 harness/render_cards.py` re-renders them; pips fill in once `runs/dNN/summary.json` exists).
Icons: [Lucide](https://lucide.dev), ISC licence.

## Layout

```
PROTOCOL.md          the rules, including the pre-registered verdict rule
harness/run.py       runner, grader and summariser
harness/setup_base.sh
tasks/<task>/        prompt.md, accept.sh, hidden/ acceptance tests
reference/           known-good fixes used to validate the graders (never shown to agents)
tricks/dNN/          one folder per day
runs/dNN/            results
base/frai            the baseline repo (rebuilt by setup_base.sh, not committed)
plan/days.json       the 100-day plan: trick, test, run mode, runs, source
plan/briefs.json     reviewed brief per day
assets/cards/        day cards (PNG + SVG)
```
