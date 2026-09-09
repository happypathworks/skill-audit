# Changelog

Every release, dated and versioned. Pirated copies go stale; this file is how
you tell.

## v1.0.0 — 2026-09-08

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
    Fixed   — exit 0 was published as a live outcome in four places and is
              not reachable: gate 6 has no PASS branch, so a static lint
              tops out at 2. It is now documented as defined-and-never-
              returned everywhere it appears, and exit 1 is named as the
              code worth scripting against.
    Fixed   — --log-row printed gate identifiers in a field that reads as
              counts ("FAIL:4" meaning gate 4 failed), three lines under the
              report's real counts. It now prints counts first and names
              gates as gates.
    Fixed   — SKILL.md told the runner to invoke skill_audit.py by bare
              name, which works only when the working directory is the skill
              folder — which it is not, on any surface where the skill is
              installed. It now resolves the script from SKILL.md's own
              folder. (Open since the first release.)
    Fixed   — the issue template still described a "→" the report stopped
              printing: the last instance of a claim retracted everywhere
              else in the same pass.
    Added   — --quiet documented in README, SETUP.md and SKILL.md. It had
              shipped visible only in --help.
    Added   — reference fixtures (examples/refs/broken, examples/refs/intact)
              and preflight assertions in the bundled regression test.
    Added   — bundled fixture regression test (tests/test_fixtures.py).
    Added   — setup guide.

---

**Cutting the next release.** Open an `## Unreleased` section, write entries as
they land, and rename it to the version and its ship date on the day it ships —
never before. A changelog entry for a release that has not happened is the first
thing in this repository that would be untrue.

Set `version` in `.claude-plugin/plugin.json` to the same number in the same
commit, so the version and its date are decided once, together, instead of
drifting apart in two files.
