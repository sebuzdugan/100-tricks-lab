Bug: `frai setup` destroys `.env` files, and API key detection is unreliable.

1. `frai setup --key sk-…` (the non-interactive form in the README) still opens the interactive prompt, and `frai setup --key sk-… --global` doesn't store globally.
2. Saving a key locally rewrote `.env` with only `OPENAI_API_KEY`, deleting every other variable. Saving globally does the same to other settings in `~/.config/frai/config`.
3. `frai config` says a local key is configured whenever a `.env` exists, even with no key in it. And frai-agent can't find a key written as `export OPENAI_API_KEY="sk-…" # rotated`.

Expected:

- Saving a key changes only the key. Every other line of `.env` stays byte-for-byte (comments, blank lines, order). An existing definition is updated in place, keeping its `export` prefix; otherwise the key is appended. The global config keeps its other JSON fields; if that file is not valid JSON, fail with an error and leave it untouched.
- Reading follows the usual `.env` rules: optional `export`, single or double quotes, a `# comment` after an unquoted value or after the closing quote, commented-out lines ignored, and if the key is defined twice the last definition wins (that is also the one to update).
- A key only counts as configured, locally or globally, if it is non-empty.
- Keep the legacy root flags working (`frai --setup --key …`, with or without `--global`), and keep the Config API's function names, arguments, return values and file permissions.

Two frai-core tests already fail on main for unrelated reasons.
