# Changelog

Every release, dated and versioned. Pirated copies go stale; this file is how
you tell.

## v2.0.0 — 2026-10-27

    Added   — SETUP.md: install steps for the claude.ai web app, Cowork
              and the desktop app. Before, its steps covered the skills
              folder on your machine, and the other surfaces got one
              sentence: that your claude.ai account is where their skills
              live. Each step not yet walked through with this skill is
              marked so.
    Added   — skill-audit-upload.zip, a second download for the claude.ai
              account (web chat, the desktop app, Cowork): SKILL.md,
              skill_audit.py and the four documents. The account upload
              refused skill-audit.zip, which holds the plugin manifest and
              six fixture SKILL.md files: "A skill cannot contain a plugin
              manifest" and "Zip must contain exactly one SKILL.md file".
              skill-audit.zip is unchanged and is still the Claude Code
              download. SETUP.md says which file goes where.

    Changed — exit codes: a usage error (an unknown flag, no path) exits 4,
              not 2. argparse's own code was 2, which is REVIEW here, so a
              mistyped flag read as "a gate needs a ruling".
    Changed — exit 3 is now REFUSED, not ERROR, and covers a SKILL.md the
              lint cannot read as written: a UTF-8 byte-order mark, UTF-16,
              binary, bytes that are not UTF-8, an empty file, and
              frontmatter missing or never closed. Each graded REVIEW (exit 2)
              until this change. The reason and its fix print on stderr as
              "skill_audit: REFUSED PATH: REASON."
    Changed — every path given must hold something gradable. A path with
              nothing at it is refused (exit 3) even beside a skill that
              grades; before, it was dropped and the other skill's verdict
              stood as the run's. Across several inputs any FAIL still exits
              1, then any refusal 3, then REVIEW 2.
    Changed — tests/test_fixtures.py asserts each refusal and each usage
              exit, runs each documented path form (a SKILL.md as a file, a
              folder of skills, --json, --log-row), runs the after-example's
              check_notes.py on every exit it documents, and runs itself
              against a checker that grades nothing to prove it can fail
              (51 cases, was 12).
    Fixed   — gate 4: "the check confirms it" did not count as a
              verification step, so a skill that counts its limit and says
              so that way got a false FAIL. A confirm with "it" or "them"
              as its object now counts; "confirm that ..." still does not,
              because that is usually a question for the user.
    Fixed   — examples/after/release-notes/check_notes.py crashed with exit 1
              (a tripped hard-fail, by its own table) when its output stream
              could not encode the em dash it prints: a cp437 console or
              pipe, or a POSIX C locale. It now substitutes the character and
              exits as documented. UTF-8 output is byte-identical.
    Changed — gate 2: a prefix counts as a deterministic entry only where
              the description declares it, because the description is the
              one field read when a skill is chosen. A prefix declared only
              in the body is REVIEW, with the fix. The description may quote
              the prefix ("audit:") as well as backtick it.
    Changed — gate 4: a countable constraint is recognised in lines,
              sentences, bullets, pages, paragraphs, items and rows as well
              as characters and words; in spelled-out numbers ("above two
              lines") as well as digits; and as a range ("2-3 sentences",
              "between 3 and 5 bullets"). Each still needs a limiting word
              or construction beside it: a bare "(1-2 words)" is not a rule.
    Changed — gate 7: the catch has to sit inside the worked example's own
              section. A worked example is one set out under a heading, an
              Input:/Output: pair or a bold "Example" label; when the only
              examples are inline ("for example", "e.g.", a mention of "the
              worked example") the row is NOT CHECKABLE, not PASS. A `#` line
              inside a code fence is not a heading.
    Changed — tests/test_fixtures.py asserts each of the three as a pair:
              the anti-pattern, and the same skill fixed.
    Measured — on 33 skills from Anthropic's official plugin marketplace
              (2026-10-06): no new FAIL and no verdict changed. Gate 7 moved
              from PASS to REVIEW on four and to NOT CHECKABLE on two, and
              from REVIEW to NOT CHECKABLE on one; gate 4 moved from NOT
              CHECKABLE to PASS on two.
    Fixed   — gate 4: a limit written with a thousands separator ("under
              1,500 characters") was not seen, so it graded NOT CHECKABLE
              where "under 1500 characters" FAILs.
    Fixed   — gate 4: a limit inside a fenced code block (a prompt
              template the skill writes) is shown, not used, and no longer
              FAILs. A verification step inside a fence still counts.
    Fixed   — gate 3: a script named after "enforced by" is met when a
              script of that name ships anywhere in the skill, such as in a
              scripts/ folder; before, only one beside SKILL.md counted, and
              the gate FAILed.
    Fixed   — gate 4: a number stated as a fact no longer FAILs because a
              directing word sits in another clause ("Slack truncates
              messages over 4,000 characters, so never paste a whole log").
    Fixed   — gate 4: a limit in quotes, italics or inline code is a
              mention, as README says for every gate.
    Fixed   — gate 4: a check beside the limit that "exits 1 when" it is
              broken counts as verifying it.
    Fixed   — gate 3: a check described in words is no longer voided by an
              unrelated file named in another sentence (a config file of the
              user's); a missing script named as the check still FAILs.
    Changed — gate 4: skill-audit's own SKILL.md now reads NOT CHECKABLE
              there (its only limit is quoted in the worked example, a
              mention); README's self-audit block is the new live run.
    Fixed   — gate 5: a named exit hard-wrapped across two lines ("if\n
              the file ..., stop and say so") is read as one sentence.
    Fixed   — gate 6: reads "our previous session" (and last, prior,
              earlier) as README lists it; "the transcript of the previous
              session" the user hands over is a file, not a prior turn.
    Changed — a flag cut short ("--jso", "--no") is a usage error (exit 4);
              before, it was read as the flag it prefixes.

## v1.2.3 — 2026-09-23

    Changed — asked to audit a skill and rewrite it in the same breath, the
              audit now reports and stops. It leaves the skill's files
              unedited and says the rewrite is a separate pass for
              skill-creator. The earlier wording, "report the audit first,
              then treat the rewrite as a distinct request", let a session
              go on to edit the skill it had just graded, and one did.
    Changed — nothing in skill_audit.py, the fixture regression test or
              its expectations. Every verdict and every exit code is what
              v1.2.2 returned.

## v1.2.2 — 2026-09-22

    Changed — the gap statement, in the description, in "The gap it
              closes" in SKILL.md and README.md, and at the close of the
              worked example, re-measured on Claude Opus 5.5 (2026-09-22).
              Asked whether a skill is any good, a bare model now writes a
              thoughtful review; what it still misses is the rule nothing
              enforces. It questions what a length limit means, never
              whether any step counts it. The description is 652
              characters, down from 698.
    Changed — README: the reference-preflight corpus figure is
              re-measured and dated (2026-09-19). The preflight returns zero
              FAILs across 32 skills; the lint as a whole returns one, a
              marketplace template whose description claude.ai refuses. This
              reached the public repository on 2026-09-19 and the download
              with this release.
    Changed — wording only, where a phrase the release checks block had
              been hidden by a line break: the trigger sentence in the
              description, the same sentence in three example skills
              (examples/after/release-notes, examples/refs/broken and
              examples/refs/intact), and one sentence in README's "The gap
              it closes". The trigger itself is unchanged: a message
              beginning with `audit:`.
    Changed — nothing in skill_audit.py, the fixture regression test or
              its expectations. Every verdict and every exit code is what
              v1.2.1 returned.

## v1.2.1 — 2026-09-18

    Added   — a statement of what this tool does not grade: a skill's
              installer. What a setup script writes outside the skill
              folder, what it downloads, and what an uninstall leaves behind
              are out of scope, in SETUP.md and README.md alike. The checker
              opens one file, SKILL.md, and looks for every other file by
              name only, so a skill can pass every gate and still come with
              an install that writes far outside its own folder.
    Added   — SETUP.md states this tool's own footprint: the install
              writes one folder and nothing outside it, nothing is fetched,
              uninstalling is deleting the folder, and running the checker
              writes nothing.
    Fixed   — SETUP.md's folder listing had fallen behind the folder. It
              now lists all six fixtures, and the .claude-plugin/, .github/
              and .gitignore entries it had left out.
    Changed — nothing in skill_audit.py or SKILL.md. Every verdict and
              every exit code is what v1.2.0 returned.

## v1.2.0 — 2026-09-13

    Added   — [D] Upload-safe description, a second preflight beside [R]. It
              grades the `description:` field against the two platform limits
              that break silently, and FAILs on either. Over 1024 characters
              the field is truncated on ingest: the tail is dropped, nothing
              warns, and a trigger sentence or a boundary that lived in the
              tail simply stops being there. Anything shaped like an XML tag
              is refused outright — claude.ai answers the upload with "SKILL.md
              description cannot contain XML tags" and installs nothing. FAIL
              rather than REVIEW, because a skill the platform will not take as
              written is not a skill with a design problem. It is a skill that
              does not arrive.
    Fixed   — the checker graded a skill PASS that then failed at upload. Met
              2026-09-12 on a real description reading `brand: recheck <path>`
              — a placeholder, not markup. Claude Code accepts that file, so
              nothing local raised it: the skill was written, installed,
              audited clean at exit 0, and turned down by the web app. There
              was no description-length check either. That is the class of
              break this tool exists to catch, on the surface most of its
              readers use.
    Added   — two fixtures. examples/desc/refused carries the refused span and
              nothing else wrong; examples/desc/toolong is 1048 characters
              with no angle bracket anywhere, so a run against it shows the two
              rules are independent. Two rules, two fixtures, asserted
              separately — one fixture carrying both defects could not say
              which rule had stopped firing. tests/test_fixtures.py now runs
              six cases and asserts the [D] row on every one of them,
              including the four that were already there: those supply the
              PASS path, on real skill files rather than on one written to
              pass.
    Changed — every report carries one more row, so a clean run reads PASS 9
              where it read PASS 8. Anything counting rows needs to know. The
              four exit codes and their meanings are unchanged, and no skill's
              verdict moves unless its own description trips one of the two
              rules.

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
