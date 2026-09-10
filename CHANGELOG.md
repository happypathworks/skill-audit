# Changelog

Every release, dated and versioned. Pirated copies go stale; this file is how
you tell.

## v1.1.0 — 2026-09-10

    Added   — NOT CHECKABLE, a fourth per-gate state. A gate reports it when
              the lint declined to decide the row: the skill raised no premise
              for the gate to test (no countable constraint, no bundled
              paths), no static reader can settle it at all (gate 6), or the
              detector's vocabulary is narrow enough that an unusually phrased
              boundary and no boundary look identical (gate 5, gate 7's
              "no example detected"). These rows carry their -> line and are
              excluded from the verdict.
    Changed — exit 0 is reachable. v1.0.0 documented it as defined-and-never-
              returned, which was true and was the defect: gate 6 returned
              REVIEW on every input, so every run of the checker returned 2.
              A verdict that is the same on every input carries no
              information. The bundled worked example, the reference fixture
              and the skill's own self-audit all return 0 now.
    Fixed   — gate 2 accepted any backticked token ending in ':' or '/' as a
              deterministic trigger, so `scripts/`, `examples/` and
              `commands/` — the way every markdown file writes a directory —
              read as one. Against the 31-skill marketplace corpus the
              pattern matched 56 times: 52 folders, and `try:`, `except:` and
              two `data:` URLs. Zero true positives, 15 false PASSes. A
              prefix token now counts only where the prose within 60
              characters says it is the trigger.
    Added   — gate 2 has a second PASS path: a description bounded on both
              sides. "Use for .docx. Do NOT use for PDFs" decides entry as
              precisely as a prefix does, and it is the only shape available
              to a skill that must fire semantically — requiring a prefix
              would ask half the ecosystem to adopt a convention that would
              make it worse. The gate asks whether entry is decided, not
              whether it is prefixed. Its REVIEW line now names the missing
              half: the boundary, not the trigger.
    Added   — exact-status probes in the dev-side negative control, seven of
              them on gate 2. The old harness only asserted FAIL vs not-FAIL,
              which made it structurally blind to a gate that cannot FAIL —
              which is how 15 false PASSes shipped with a green suite. A
              false positive on the PASS side now has a probe watching it.
    Changed — gate 4 no longer PASSes a skill for having no countable
              constraint. That branch was 29 of the 31 marketplace skills: a
              green row that meant "nothing here to check". It reports NOT
              CHECKABLE, as does the [R] preflight when a skill claims no
              bundled paths.

    Known   — the marketplace corpus returns REVIEW 31 of 31 again after the
              gate 2 fix, and this time it is a fact about the corpus rather
              than about the tool. None of those 31 declares a deterministic
              trigger, and one of the 31 bounds its description on both
              sides. PASS is reachable and reached — by the bundled fixtures
              and by this skill — it is simply not reached there. The
              5-of-31 figure quoted while the [:/] bug was live was an
              artifact and should not be requoted.
    Changed — the report's status column is 13 characters wide, and the
              counts line and --log-row note carry a NOT CHECKABLE field.
              Anything parsing the status column needs to know the new label;
              the four exit codes and their meanings are unchanged.
    Changed — a PASS verdict prints how many gates were left undecided, in
              the same sentence. PASS means the lint has no objections left,
              not that the skill is proven, and the report says so.
    Fixed   — the bundled worked example's repaired skill (examples/after)
              and examples/refs/intact returned 2, charged for gates the lint
              never decided. Both now return 0, and tests/test_fixtures.py
              asserts it.

    Changed — gate 6 is renamed "No prior-chat references", and it can PASS.
              It always checked one thing a file can show — phrasing that
              leans on an earlier conversation, "as we discussed", "like last
              time" — and FAILed on it. But it was named for a question no
              lint can answer, "survives cold handoff", so it had no PASS
              branch and printed NOT CHECKABLE on every skill that did not
              trip it: a row that could fail and never pass. It now PASSes a
              clean scan. This supersedes the gate-6 half of the NOT
              CHECKABLE entry above. No exit code changes on any input: NOT
              CHECKABLE was already excluded from the verdict.
    Added   — a "Not graded" line under every verdict, FAIL included:
              whether the skill works in a fresh session, which answering
              takes a run and not a read, followed by the step to take it —
              naming the skill's own trigger when gate 2 found one. --json
              carries it as "not_graded"; the --log-row note says it;
              --quiet keeps the line and drops the step.
    Added   — tests/test_fixtures.py asserts the "Not graded" line on every
              fixture. It changes no exit code, so an exit-code test alone
              would never notice it had gone.

    Known   — gate 5's FAIL branch pairs a scope phrase anywhere in the body
              with a hedge word anywhere else, with no proximity constraint.
              It is unreachable today because the scope vocabulary is narrow
              enough that it fires on almost nothing. Widening that
              vocabulary without first constraining the pair would FAIL good
              skills on sentences kilobytes apart; the fix order is recorded
              in the source comment on gate5().

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
