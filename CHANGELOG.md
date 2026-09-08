# Changelog

Every release, dated and versioned. Pirated copies go stale; this file is how
you tell.

## Unreleased

    Added   — seven-gate floor, exit codes 0 / 2 / 1 / 3.
    Added   — worked example: the same skill before and after, with the real
              output of both runs.
    Added   — [R] reference-resolution preflight: every path a skill claims
              to ship must exist, checked before the Floor. Workspace and
              runtime paths are counted as skipped, never flagged. Zero false
              positives across a 31-skill known-good corpus. --no-refs skips it.
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
