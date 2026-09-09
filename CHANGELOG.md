# Changelog

Every release, dated and versioned. Pirated copies go stale; this file is how
you tell.

## Unreleased

    Added   — seven-gate floor, exit codes 0 / 2 / 1 / 3.
    Added   — worked example: the same skill before and after, with the real
              output of both runs.
    Added   — [R] reference-resolution preflight: every path a skill claims
              to ship must exist, checked before the Floor. Workspace and
              runtime paths are counted as skipped, never flagged, as are
              paths on a line that announces itself illustrative. A missing
              path FAILs only when the skill points at it — a link, an
              invocation, or a pointer verb; missing but merely mentioned is
              REVIEW. --no-refs skips it.
    Added   — detector precision pass on gates 4, 5, 6 and the preflight,
              measured against a 32-skill known-good corpus (Anthropic's
              official plugin marketplace plus one local skill): 6 FAILs,
              all six false positives, now 0. "spec" no longer counts as a
              countable constraint on its own; a scope boundary FAILs only
              when its exit is soft, and names the phrase; "you already
              know" needs a discourse object.
    Added   — reference fixtures (examples/refs/broken, examples/refs/intact)
              and preflight assertions in the bundled regression test.
    Added   — bundled fixture regression test (tests/test_fixtures.py).
    Added   — setup guide.

Rename this section to the version and its ship date on release. Do not
pre-date it: a changelog entry for a release that has not happened is the
first thing on this repo that would be untrue.

Set `version` in `.claude-plugin/plugin.json` to the same number in the same
commit. It is deliberately absent until then — `claude plugin validate` warns
about it and still passes — so that the version and its date are decided once,
together, instead of drifting apart in two files.
