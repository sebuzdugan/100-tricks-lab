Bug: a spec drafted by `frai-gate draft` fails `frai-gate check` for formatting reasons, not content.

`examples/support-triage-demo/rai-gate-draft.reference.md` is a real draft. Checking it (with `frai-gate check` or `frai gate check`) reports "Risk tier must be one of: …" although the draft says `**Tier:** **limited**`, and "Unanswered field" for fields whose answer is a nested list or a table under the label. Users who resolve every open item still can't get a PASS. And once that noise is gone, nothing stops a draft whose `NEEDS HUMAN INPUT` items were never resolved from passing, which is exactly what the drafter tells people to fix first.

Make the check accept the way the drafter (and people) write specs:

- Both label styles work: `- **Retention**: 30 days` and `- **Retention:** 30 days`. An empty field is still unanswered in either style.
- An answer may sit on indented lines below its field (nested bullets, an indented table or paragraph; blank lines in between are fine). The same goes for the Tier and Sign-off values.
- An unresolved `NEEDS HUMAN INPUT` anywhere in a gate subsection blocks that check.
- No regressions: on the untouched spec template (`packages/frai-gate/assets/rai-spec-template.md`) the check must report exactly the findings it reports today, and `examples/frai-spec-example.md` and `examples/support-triage-demo/FRAI-SPEC.md` must still pass.

JSON output and exit codes stay as they are. Don't edit existing tests.
