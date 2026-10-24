#!/usr/bin/env python3
"""
test_fixtures.py — the shipped regression test for skill_audit.py.

Runs the checker against the six bundled fixtures and asserts the exit code
and the preflight rows each one is supposed to produce. It needs no external corpus and
no arguments: clone the repo, run this, get a verdict.

    examples/before/release-notes   must exit 1 (FAIL)   — Gate 4 is a real
                                    anti-pattern and must stay detected.
    examples/after/release-notes    must exit 0 (PASS)   — the repaired skill
                                    must NOT trip a false-positive FAIL, and
                                    every gate the lint can decide is clean.
    examples/refs/broken            must exit 1 (FAIL)   — the reference
                                    preflight must still catch a bundled path
                                    that is not there, while leaving the
                                    workspace paths beside it alone.
    examples/refs/intact            must exit 0 (PASS)   — the same skill with
                                    the path repaired must come back clean.
    examples/desc/refused           must exit 1 (FAIL)   — the description
                                    preflight must still catch a span claude.ai
                                    refuses at upload ("<path>").
    examples/desc/toolong           must exit 1 (FAIL)   — and must still catch
                                    a description past the 1024-character limit,
                                    which carries no angle bracket at all. Two
                                    rules, asserted separately, because a single
                                    fixture carrying both could not tell which
                                    one had stopped firing.

The second assertion is the one that matters. A lint that fails good input
loses a stranger's trust on first contact, and there is no second contact.

Every case also asserts its `[D]` row, which is why the two description
fixtures need no clean sibling: the four fixtures that were already here supply
the PASS path for that preflight, on real skill files rather than on one written
to pass.

Both clean fixtures returned 2 (REVIEW) until the NOT CHECKABLE state landed.
The gates they were being charged for — cold handoff, and a bundled-path check
with no bundled paths — were ones the lint never decided, and a verdict is not
allowed to rest on those. Nothing about the fixtures changed; what changed is
that the checker stopped counting its own blind spots against them.

Every run must also print the "Not graded" line under its verdict. It is the
report saying what no gate covers — whether the skill works in a fresh session
— and it changes no exit code, so an exit-code test alone would never notice
it had gone.

Rules the six fixtures cannot separate are asserted on skills written to a
temporary folder at run time (ROW_CASES): mostly one skill showing the
anti-pattern and the same skill fixed, differing in that one respect.

    gate 2   a prefix declared only in the body is REVIEW; the same prefix
             in the description, quoted rather than backticked, is PASS.
    gate 4   a line budget written in words ("two lines") with nothing
             counting it is FAIL; the same budget, counted, is PASS.
    gate 7   an example whose catch sits in another section is REVIEW; the
             catch inside the example's own section is PASS.

The command line comes next. REFUSE_CASES are SKILL.md files the checker
cannot read as written (a byte-order mark, UTF-16, binary, bytes that are not
UTF-8, an empty file, frontmatter missing or never closed): each must exit 3
and name its reason, never take a verdict code. ARGV_CASES pin usage errors at
exit 4, a path with nothing at it at exit 3 even beside a clean skill (while a
FAIL beside it still exits 1), and run each documented path form once.

NOTES_CASES run the after-example's own check_notes.py, whose exit codes are
what make that skill's hard-fails real. Then the checker's functions are
called directly for the branches no command line reaches, and last this file
runs itself against a checker that grades nothing and one that is not there,
and must exit 1 and 2: a test that cannot fail tests nothing.

    exit 0   every fixture returned its expected code and preflight rows
    exit 1   at least one did not — the checker regressed
    exit 2   setup error (checker or fixture missing)

Note: this is not the same gate as the repository's acceptance test, which
tests for false positives against a large external known-good corpus supplied
by path. That one stays out of the shipped product by design. This one is
small, bundled, and runnable by anyone who downloaded the repo.
"""
import codecs
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# SKILL_AUDIT_TEST_CHECKER is set only by harness_cases below, to prove this
# file fails on a checker that grades nothing.
STUBBED = bool(os.environ.get("SKILL_AUDIT_TEST_CHECKER"))
CHECKER = os.environ.get("SKILL_AUDIT_TEST_CHECKER") or os.path.join(ROOT, "skill_audit.py")

# (path, expected exit code, label, expected [R] status or None, expected [D] status)
# The last two fields assert the preflight lines directly. Exit code alone is
# not enough: a gate FAIL elsewhere would mask a preflight that stopped firing,
# and a check that silently never fires is worse than no check. [D] is asserted
# on every case, PASS included — it is the row with no clean fixture of its own.
CASES = [
    ("examples/before/release-notes", 1, "FAIL", None, "PASS"),
    ("examples/after/release-notes", 0, "PASS", None, "PASS"),
    ("examples/refs/broken", 1, "FAIL", "FAIL", "PASS"),
    ("examples/refs/intact", 0, "PASS", "PASS", "PASS"),
    ("examples/desc/refused", 1, "FAIL", None, "FAIL"),
    ("examples/desc/toolong", 1, "FAIL", None, "FAIL"),
]

PLAIN = "Turns meeting notes into minutes. A fixture for the skill-audit regression test."
TRIGGER = "## Trigger\n\nAny message beginning with `min:` fires this skill. Treat the prefix as a command.\n"

# (label, description, body, gate, expected status on that gate's row)
ROW_CASES = [
    ("gate 2  prefix in the body only",
     "Turns meeting notes into minutes. Use when the user pastes meeting notes.",
     TRIGGER, "2", "REVIEW"),
    ("gate 2  same prefix, quoted, in the description",
     "Turns meeting notes into minutes. The \"min:\" prefix triggers it.",
     "## Trigger\n\nThe prefix in the description is the whole entry rule.\n", "2", "PASS"),
    ("gate 4  line budget in words, never counted",
     PLAIN, "## Rules\n\nKeep each action to two lines.\n", "4", "FAIL"),
    ("gate 4  same budget, counted before answering",
     PLAIN, "## Rules\n\nKeep each action to two lines. Count them before you answer, and "
            "verify each action is two lines or fewer.\n", "4", "PASS"),
    ("gate 4  same budget, the check confirms it",
     PLAIN, "## Rules\n\nKeep each action to two lines. Run the bundled check before you answer; "
            "the check confirms it.\n", "4", "PASS"),
    ("gate 7  catch in another section",
     PLAIN, "## Example\n\nInput: notes from the Tuesday standup.\n"
            "Output: minutes with three action items.\n\n## Rules\n\n"
            "Write each owner as the notes name them, instead of guessing one.\n", "7", "REVIEW"),
    ("gate 7  catch in the example's own section",
     PLAIN, "## Example\n\nInput: notes in which nobody owns the second action.\n"
            "Output: minutes that leave that owner blank, instead of guessing one.\n\n"
            "## Rules\n\nWrite each owner as the notes name them.\n", "7", "PASS"),
    ("[D]     no description declared",
     "", TRIGGER, "D", "NOT CHECKABLE"),
]


# Edge cases, one per defect once found, grouped by the kind of mistake.
# Each skill is the smallest that shows the defect.
# (label, {path: text}, gate, statuses that pass); the SKILL.md gets PLAIN as
# its description.
G1_CASES = [
    # false-fail-known-good: a sound skill must not FAIL
    ("[R]     a link to a shipped file with a #fragment",
     {"SKILL.md": "## Setup\n\nFollow [the setup rules](references/guide.md#setup).\n",
      "references/guide.md": "Setup.\n"}, "R", ("PASS",)),
    ("[R]     a link to a shipped file, URL-encoded space",
     {"SKILL.md": "## Setup\n\nFollow [the house guide](references/house%20guide.md).\n",
      "references/house guide.md": "Setup.\n"}, "R", ("PASS",)),
    ("gate 6  a leak phrase named as filler to strip",
     {"SKILL.md": "## Style\n\nStrip filler such as *as we discussed* from the draft.\n"}, "6", ("PASS",)),
    ("gate 6  'as discussed' pointing at a section of the file",
     {"SKILL.md": "## Rules\n\nAs discussed in the Scope boundary section above, stop at contracts.\n"},
     "6", ("PASS",)),
    ("gate 6  'per our' naming a file the skill ships",
     {"SKILL.md": "## Rules\n\nFormat dates per our style guide, `references/style.md`.\n",
      "references/style.md": "ISO dates.\n"}, "6", ("PASS",)),
    ("gate 4  a shipped counter run before replying",
     {"SKILL.md": "## Rules\n\nKeep the summary under 150 words. Run `python count.py draft.txt` "
                  "before replying; it prints the real count and exits 1 over the limit.\n",
      "count.py": "import sys\n"}, "4", ("PASS",)),
    ("gate 3  'refuse and' in a scope exit is not a hard-fail",
     {"SKILL.md": "## Scope\n\nIf the text is a contract, refuse and say so.\n"}, "3", ("PASS", "REVIEW")),
    ("gate 5  a style tip far from a Hard-fails heading",
     {"SKILL.md": "## Hard-fails\n\nThe draft names every owner.\n\n## Style\n\nAvoid jargon.\n"},
     "5", ("PASS", "REVIEW", "NOT CHECKABLE")),
    # description-parse: [D] grades the description as the platform decodes it
    ("[D]     a YAML-escaped angle bracket in the description",
     {"SKILL.md": "---\nname: fixture\ndescription: \"Links one file: links: \\u003cpath\\u003e.\"\n---\n\n"
                  "# fixture\n\nBody.\n"}, "D", ("FAIL",)),
    # ref-mention-unseen: a missing path under a shipped folder, in plain prose
    ("[R]     a missing path under a shipped folder, named in prose",
     {"SKILL.md": "## Setup\n\nRead `references/guide.md`. The layout rules are in references/layout.md.\n",
      "references/guide.md": "Setup.\n"}, "R", ("REVIEW",)),
    # marker-presence-pass: a heading or a keyword is not the thing it names
    ("gate 1  a 'gap' heading over no gap statement",
     {"SKILL.md": "## The gap it closes\n\nSee the trigger below.\n"}, "1", ("REVIEW",)),
    ("gate 2  a prefix the description says no longer invokes it",
     {"SKILL.md": "---\nname: fixture\ndescription: Turns notes into minutes. The `min:` prefix is "
                  "deprecated and no longer invokes this skill.\n---\n\n# fixture\n\nBody.\n"}, "2", ("REVIEW",)),
    ("gate 7  a happy-path example under a 'catch' heading",
     {"SKILL.md": "## Worked example (a catch, not a happy path)\n\nInput: three agreed items.\n"
                  "Output: minutes listing the three items.\n"}, "7", ("REVIEW",)),
    # enforcement-by-mention: the check has to exist, and sit by the rule
    ("gate 3  a hard-fail 'enforced by' a script the skill lacks",
     {"SKILL.md": "## Hard-fails\n\n- Never invent an owner; enforced by check_minutes.py.\n"}, "3", ("FAIL",)),
    ("gate 3  ... the same, with its exit code described",
     {"SKILL.md": "## Hard-fails (enforced by check_minutes.py)\n\n- Never invent an owner. "
                  "`check_minutes.py` exits `1` on one.\n"}, "3", ("FAIL",)),
    # REVIEW, not FAIL: known-good skills are written this way and must not FAIL.
    ("gate 4  a word limit, and 'verify' about something else",
     {"SKILL.md": "## Rules\n\nKeep the minutes under 150 words.\n\n## Setup\n\n"
                  "Verify the front matter parses.\n"}, "4", ("REVIEW",)),
    # constraint-vocab-gap: a limit counts however the number is spelled
    ("gate 4  a compound spelled-out limit, never counted",
     {"SKILL.md": "## Rules\n\nKeep the minutes under three hundred words.\n"}, "4", ("FAIL",)),
    # phrase-across-linebreak: prose is hard-wrapped
    ("gate 6  a leak phrase wrapped across a line",
     {"SKILL.md": "## Rules\n\nUse the format as we\ndiscussed.\n"}, "6", ("FAIL",)),
    # The rows with a written spec.
    # [D] reads the frontmatter as YAML does.
    ("[D]     a quoted 'description' key",
     {"SKILL.md": "---\nname: fixture\n\"description\": Links one file: links: <path>.\n---\n\n# fixture\n\nBody.\n"},
     "D", ("FAIL",)),
    ("[D]     a literal block keeps its indentation",
     {"SKILL.md": "---\nname: fixture\ndescription: |\n  Writes commit messages.\n"
                  + "".join("      - rule %02d keeps the subject line short and plain\n" % i for i in range(20))
                  + "---\n\n# fixture\n\nBody.\n"}, "D", ("FAIL",)),
    ("[D]     a single-quoted '' escape is one character",
     {"SKILL.md": "---\nname: fixture\ndescription: '" + "It''s fine. " * 90 + "'\n---\n\n# fixture\n\nBody.\n"},
     "D", ("PASS",)),
    ("[D]     a frontmatter comment is not description text",
     {"SKILL.md": "---\nname: fixture\ndescription: >-\n  Turns notes into minutes.\n"
                  "# version: <set by the release script>\n---\n\n# fixture\n\nBody.\n"}, "D", ("PASS",)),
    # [R] reads markdown links and command lines as written.
    ("[R]     a titled link to a missing shipped file",
     {"SKILL.md": "## Setup\n\nRead [the schema](references/schema.md \"Field schema\").\n",
      "references/other.md": "x\n"}, "R", ("FAIL",)),
    ("[R]     a reference-style link to a missing shipped file",
     {"SKILL.md": "## Setup\n\nRead [the schema][s].\n\n[s]: references/schema.md\n",
      "references/other.md": "x\n"}, "R", ("FAIL",)),
    ("[R]     a missing script run with an interpreter flag",
     {"SKILL.md": "## Run\n\n```\npython3 -u scripts/build_index.py\n```\n",
      "scripts/other.py": "x = 1\n"}, "R", ("FAIL",)),
    ("[R]     a script the model writes into the user's repo, then runs",
     {"SKILL.md": "## Run\n\nWrite the migration to `scripts/migrate_0042.py` in the user's repository, "
                  "then run:\n\n```\npython3 scripts/migrate_0042.py --dry-run\n```\n",
      "scripts/check.py": "x = 1\n"}, "R", ("PASS", "NOT CHECKABLE")),
    ("[R]     a line reference to a shipped file",
     {"SKILL.md": "## Rules\n\nThe threshold lives in one place: see `scripts/lint.py:3`.\n",
      "scripts/lint.py": "LIMIT = 50\n"}, "R", ("PASS",)),
    # SA-NARROW: R3's heuristic majors. Each gate FAILs only on the phrasings
    # SKILL.md and README.md list for it; a weaker match is REVIEW.
    ("gate 1  an incidental verb ('Skip blank lines') is not a gap statement",
     {"SKILL.md": "## Rules\n\nSkip blank lines in the diff.\n"}, "1", ("REVIEW",)),
    ("gate 2  folders beside 'followed by' are not a prefix",
     {"SKILL.md": "---\nname: fixture\ndescription: Python helper. `src/` followed by `tests/`, refactor, lint, format.\n"
                  "---\n\n# fixture\n\nBody.\n"}, "2", ("REVIEW",)),
    ("gate 2  'never use' about formats is not a boundary",
     {"SKILL.md": "---\nname: fixture\ndescription: Converts old formats people never use anymore. Use when the user "
                  "asks about files.\n---\n\n# fixture\n\nBody.\n"}, "2", ("REVIEW",)),
    ("gate 3  an install fence is not a check behind a hard-fail",
     {"SKILL.md": "## Hard-fails\n\nThis is a hard-fail: never ship notes without a date.\n\n## Install\n\n"
                  "```bash\ngit clone https://example.com/notes\n```\n"}, "3", ("FAIL",)),
    ("gate 3  a hard-fail checked by a script the skill lacks, exit code described",
     {"SKILL.md": "## Hard-fails\n\nThis is a hard-fail: never publish without a changelog entry. "
                  "`check_release.py` checks it, and a non-zero exit code stops the release.\n"}, "3", ("FAIL",)),
    ("gate 3  'hard-fail' with a non-breaking hyphen",
     {"SKILL.md": "## Rules\n\nThis is a hard‑fail: never ship notes without a date.\n"}, "3", ("FAIL",)),
    ("gate 3  a check shipped in scripts/",
     {"SKILL.md": "## Hard-fails\n\nThis is a hard-fail: never send a message over the limit. "
                  "`scripts/check_msg.py` exits 1 on one.\n", "scripts/check_msg.py": "import sys\n"}, "3", ("PASS",)),
    ("gate 3  a check shipped as a Node module",
     {"SKILL.md": "## Hard-fails\n\nThis is a hard-fail: never send a message over the limit. "
                  "`check.mjs` exits 1 on one.\n", "check.mjs": "process.exit(0);\n"}, "3", ("PASS",)),
    ("gate 3  'There are no hard-fails' declares none",
     {"SKILL.md": "## Rules\n\nThere are no hard-fails in this skill. Never invent a date.\n"}, "3", ("PASS", "REVIEW")),
    ("gate 4  'no longer than 50 characters', never counted",
     {"SKILL.md": "## Rules\n\nKeep the subject line no longer than 50 characters.\n"}, "4", ("FAIL",)),
    ("gate 4  'under fourteen lines', never counted",
     {"SKILL.md": "## Rules\n\nKeep the summary under fourteen lines.\n"}, "4", ("FAIL",)),
    ("gate 4  'no more than' written as the symbol, never counted",
     {"SKILL.md": "## Rules\n\nKeep each post ≤ 280 characters.\n"}, "4", ("FAIL",)),
    ("gate 4  a limit counted with wc",
     {"SKILL.md": "## Rules\n\nKeep the body to 120 words. Run `wc -w body.txt` and cut until it reports 120 or "
                  "fewer.\n"}, "4", ("PASS",)),
    ("gate 4  a fact about the world is not a rule on the output",
     {"SKILL.md": "## Background\n\nMessages over 160 characters are split into parts by the carrier.\n"},
     "4", ("PASS", "NOT CHECKABLE")),
    ("gate 5  SKILL.md's own worked example scope line",
     {"SKILL.md": "## Rules\n\nTry to stay on the meeting content and avoid drifting.\n"}, "5", ("FAIL",)),
    ("gate 5  'gently steer back' under Out of scope",
     {"SKILL.md": "## Out of scope\n\nBilling questions. Gently steer the conversation back to the meeting.\n"},
     "5", ("FAIL",)),
    ("gate 5  a negated stop is not a named exit",
     {"SKILL.md": "## Scope\n\nOut of scope: billing. Try to stay on the meeting; if the user pushes, don't stop "
                  "them.\n"}, "5", ("FAIL",)),
    ("gate 5  'say ..., name the skill, and stop' is a named exit",
     {"SKILL.md": "## Scope\n\nOut of scope: release notes. When asked for them, say the changelog is not this "
                  "skill's job, name the release-notes skill, and stop. Avoid partial drafts.\n"}, "5", ("PASS",)),
    ("gate 5  'avoid' beside a boundary is weaker wording: REVIEW, not FAIL",
     {"SKILL.md": "## Out of scope\n\nBilling questions. Avoid long tangents about pricing.\n"}, "5", ("REVIEW",)),
    ("gate 6  'as last time'",
     {"SKILL.md": "## Rules\n\nUse the same structure as last time.\n"}, "6", ("FAIL",)),
    ("gate 6  'our last conversation'",
     {"SKILL.md": "## Rules\n\nUse the format we agreed on in our last conversation.\n"}, "6", ("FAIL",)),
    ("gate 6  'as discussed in Step 2' points into the file",
     {"SKILL.md": "## Rules\n\nAs discussed in Step 2, keep each owner as written.\n"}, "6", ("PASS",)),
    ("gate 6  'per our convention in the Naming section below'",
     {"SKILL.md": "## Rules\n\nName files per our convention in the Naming section below.\n"}, "6", ("PASS",)),
    ("gate 6  'like before/after pairs' is a layout",
     {"SKILL.md": "## Rules\n\nLay the changes out like before/after pairs.\n"}, "6", ("PASS",)),
    ("gate 7  'instead of' about formatting is not a catch",
     {"SKILL.md": "## Example\n\nInput: three bugs fixed.\nOutput: a list, using bullets instead of numbers.\n"},
     "7", ("REVIEW",)),
    # README's own stated rules: the pointer verbs, the mention rule, the
    # gate 6 exemptions.
    ("[R]     'See references/style.md', unbackticked and missing",
     {"SKILL.md": "## House style\n\nSee references/style.md for the heading order.\n",
      "references/overview.md": "x\n"}, "R", ("FAIL",)),
    ("[R]     'defined in references/fields.md', unbackticked and missing",
     {"SKILL.md": "## Fields\n\nThe field list is defined in references/fields.md.\n",
      "references/overview.md": "x\n"}, "R", ("FAIL",)),
    ("gate 3  'hard-fail' only in code, no script",
     {"SKILL.md": "## How to use it\n\nList every job marked `hard-fail: true` first, then the rest.\n"},
     "3", ("PASS", "REVIEW", "NOT CHECKABLE")),
    ("gate 3  'hard stop' only in quotes, no script",
     {"SKILL.md": "## How to use it\n\nList every clause that contains the phrase \"hard stop\" or "
                  "\"terminate\".\n"}, "3", ("PASS", "REVIEW", "NOT CHECKABLE")),
    ("gate 6  'as discussed in `references/style.md`', a shipped file",
     {"SKILL.md": "## Format\n\nUse the headings as discussed in `references/style.md`.\n",
      "references/style.md": "x\n"}, "6", ("PASS",)),
    ("gate 6  'as discussed in references/style.md', unbackticked, shipped",
     {"SKILL.md": "## Format\n\nUse the headings as discussed in references/style.md.\n",
      "references/style.md": "x\n"}, "6", ("PASS",)),
    ("gate 6  'as discussed in references/style.md', not shipped, still FAILs",
     {"SKILL.md": "## Format\n\nUse the headings as discussed in references/style.md.\n",
      "references/other.md": "x\n"}, "6", ("FAIL",)),
    ("gate 6  'per our convention in / the Naming section below', wrapped",
     {"SKILL.md": "## Format\n\nAs discussed in Step 2, owners come first. Name files per our convention in\n"
                  "the Naming section below.\n\n## Naming\n\nrecap-DATE.md\n"}, "6", ("PASS",)),
    ("gate 6  a blank line is a paragraph break, not a wrap",
     {"SKILL.md": "## Format\n\nName files per our\n\nNaming section below.\n"}, "6", ("FAIL",)),
    ("gate 1  'without this skill' only in quotes is a mention",
     {"SKILL.md": "## Why it exists\n\nReviewers flag phrases like \"without this skill\" in a recap as "
                  "filler, so the recap leaves them out.\n"}, "1", ("REVIEW",)),
    ("gate 7  the catch word only in code",
     {"SKILL.md": "## Example\n\nInput: a stand-up where Dana says she will take the build.\n"
                  "Output: a recap listing Dana as owner. Items nobody took are tagged `silently-dropped`.\n"},
     "7", ("REVIEW",)),
    ("gate 7  the catch word only in quotes",
     {"SKILL.md": "## Example\n\nInput: a stand-up where Dana says \"no catch, I'll take the build\".\n"
                  "Output: a recap listing Dana as owner of the build.\n"}, "7", ("REVIEW",)),
    ("gate 4  a limit written with a thousands separator, nothing counts it",
     {"SKILL.md": "## Output\n\nKeep the note under 1,500 characters.\n"}, "4", ("FAIL",)),
    ("gate 4  the same limit without the separator still FAILs",
     {"SKILL.md": "## Output\n\nKeep the note under 1500 characters.\n"}, "4", ("FAIL",)),
    ("gate 3  'enforced by check.py' when it ships as scripts/check.py",
     {"SKILL.md": "## Hard-fails (enforced by check.py)\n\n- **No unbalanced ledger.** `scripts/check.py` "
                  "exits `1` when it does not balance.\n",
      "scripts/check.py": "import sys\nsys.exit(0)\n"}, "3", ("PASS",)),
    ("gate 3  'enforced by check.py' when no check.py ships anywhere still FAILs",
     {"SKILL.md": "## Hard-fails (enforced by check.py)\n\n- **No unbalanced ledger.** Never emit an "
                  "unbalanced ledger.\n",
      "scripts/other.py": "import sys\nsys.exit(0)\n"}, "3", ("FAIL",)),
    ("gate 4  a word limit inside a fenced code block is shown, not used",
     {"SKILL.md": "## The prompt it writes\n\n```\nYou are a support agent. Keep the reply under 50 words.\n```\n"},
     "4", ("NOT CHECKABLE", "PASS")),
    ("gate 4  the same limit outside the fence still FAILs",
     {"SKILL.md": "## The reply\n\nKeep the reply under 50 words.\n\n```\npython3 ledger.py invoices.csv\n```\n"},
     "4", ("FAIL",)),
    ("gate 4  a limit a shipped script enforces by its exit code",
     {"SKILL.md": "## Output\n\nKeep the post under 280 characters. `scripts/count_chars.py draft.txt` exits 1\n"
                  "when the draft is over the limit; post only after it exits 0.\n",
      "scripts/count_chars.py": "import sys\nsys.exit(0)\n"}, "4", ("PASS", "REVIEW")),
    ("gate 4  a hard-fail's check that 'exits 1 when' in another section verifies no limit",
     {"SKILL.md": "## Hard-fails (enforced by check.py)\n\n- **No bad row.** `check.py` exits `1` when one remains.\n\n"
                  "## Output\n\nNever go over 300 words.\n",
      "check.py": "import sys\nsys.exit(0)\n"}, "4", ("FAIL",)),
    ("gate 4  a limit quoted as an example's input is a mention",
     {"SKILL.md": "## Example\n\nInput: a prompt file that says \"Keep the reply under 50 words.\" Output: the skill\n"
                  "flags it.\n"}, "4", ("PASS", "NOT CHECKABLE", "REVIEW")),
    ("gate 4  the same limit unquoted still FAILs",
     {"SKILL.md": "## Output\n\nKeep the reply under 50 words.\n"}, "4", ("FAIL",)),
    ("gate 4  a fact about a limit, with a directive in another clause",
     {"SKILL.md": "## Output\n\nSlack truncates messages over 4,000 characters, so never paste a whole log.\n"},
     "4", ("NOT CHECKABLE", "PASS", "REVIEW")),
    ("gate 4  a fact about a limit, 'so the skill always' in another clause",
     {"SKILL.md": "## Output\n\nPosts over 280 characters are rejected by the API, so the skill always posts a "
                  "thread.\n"}, "4", ("NOT CHECKABLE", "PASS", "REVIEW")),
    ("gate 4  a directive and its limit in one clause still FAILs",
     {"SKILL.md": "## Output\n\nThe API is slow, so keep every post under 280 characters.\n"}, "4", ("FAIL",)),
    ("gate 3  a check described in words, the user's config file named nearby",
     {"SKILL.md": "## Hard-fails\n\n- Never report the build green unless `npm test` exits 0: the exit code is the\n"
                  "  check. Its settings live in the user's `vitest.config.js`.\n"}, "3", ("PASS", "REVIEW")),
    ("gate 3  the only check a missing script, described in words, still FAILs",
     {"SKILL.md": "## Hard-fails\n\n- Never report the build green unless `check_build.py` exits 0: the exit\n"
                  "  code is the check.\n"}, "3", ("FAIL",)),
    ("gate 5  'if ..., stop and say so' hard-wrapped across two lines",
     {"SKILL.md": "## Scope\n\nNot for Excel workbooks. Where possible, the user should export to CSV first; if\n"
                  "the file you are given is still a workbook, stop and say so.\n"}, "5", ("PASS", "REVIEW")),
    ("gate 5  the same section with no exit still FAILs",
     {"SKILL.md": "## Scope\n\nNot for Excel workbooks. Where possible, the user should export to CSV first.\n"},
     "5", ("FAIL",)),
    ("gate 6  'the transcript of the previous session' from a file the user gives",
     {"SKILL.md": "## Style\n\nRead the transcript of the previous session from the path the user gives, and\n"
                  "summarise what it decided.\n"}, "6", ("PASS",)),
    ("gate 6  'our previous session' still FAILs",
     {"SKILL.md": "## Style\n\nUse the headings from our previous session.\n"}, "6", ("FAIL",)),
]


def skill_md_folder_case():
    """A folder holding a directory named SKILL.md is refused, not a crash."""
    code, out, err = in_temp({"skill/SKILL.md/notes.txt": b"x\n"},
                             lambda d: run([CHECKER, os.path.join(d, "skill")]))
    ok = code == 3 and "Traceback" not in err
    return report(ok, "a directory named SKILL.md", "exit %d" % code, out + err)


def skill_row(files, gate):
    """The status on one gate's row for a skill written from {path: text}."""
    files = dict(files)
    if not files["SKILL.md"].startswith("---"):  # a case may carry its own frontmatter
        files["SKILL.md"] = "---\nname: fixture\ndescription: %s\n---\n\n# fixture\n\n%s" % (PLAIN, files["SKILL.md"])
    _code, out, _err = in_temp({"fixture/" + k: v.encode("utf-8") for k, v in files.items()},
                               lambda d: run([CHECKER, os.path.join(d, "fixture"), "--json"]))
    try:
        rows = json.loads(out)["gates"]
    except (ValueError, KeyError, TypeError):
        return None
    return next((r["status"] for r in rows if str(r["gate"]) == gate), None)


GOOD = b"---\nname: fixture\ndescription: %s\n---\n\n# fixture\n\nBody.\n" % PLAIN.encode("utf-8")

# Inputs the checker must refuse with exit 3 rather than grade. Each one came
# back REVIEW (exit 2) before refusals existed: a verdict on a file the lint
# could not read. (label, SKILL.md bytes, a word the stderr refusal must carry)
REFUSE_CASES = [
    ("UTF-8 byte-order mark", codecs.BOM_UTF8 + GOOD, "byte-order mark"),
    ("UTF-16", GOOD.decode("utf-8").encode("utf-16"), "SKILL.md is UTF-16"),
    ("binary", bytes(range(256)), "NUL"),
    ("not UTF-8", GOOD.replace(b"Body.", b"Caf\xe9."), "not UTF-8"),
    ("empty", b"", "empty"),
    ("no frontmatter", b"# fixture\n\nBody.\n", "no frontmatter"),
    ("frontmatter never closed", b"---\nname: fixture\n\n# fixture\n", "never closed"),
]

# The command line, run from the skill folder. Usage errors exit 4: argparse's
# own code is 2, which is REVIEW here. The documented path forms each run
# once: a SKILL.md passed as a file, a folder of skills, --json over several,
# --log-row. (label, argv after the checker, expected exit code, text stdout
# or stderr must carry, or None)
ARGV_CASES = [
    ("no arguments", [], 4, "usage error"),
    ("an unknown flag", ["--no-such-flag", "examples/after/release-notes"], 4, "usage error"),
    ("a flag cut short is unknown, not a prefix", ["--jso", "examples/after/release-notes"], 4, "usage error"),
    ("'--no' is unknown, not --no-refs", ["--no", "examples/after/release-notes"], 4, "usage error"),
    ("a clean skill beside a path that is not there",
     ["examples/after/release-notes", "examples/no-such-skill"], 3, "no such file or folder"),
    ("a FAIL beside a path that is not there",
     ["examples/before/release-notes", "examples/no-such-skill"], 1, "REFUSED"),
    ("a file that is not a SKILL.md",
     ["examples/after/release-notes/check_notes.py"], 3, "not a SKILL.md"),
    ("a folder with no skill in it", ["tests"], 3, "no skill folder under it"),
    ("a SKILL.md passed as a file", ["examples/after/release-notes/SKILL.md"], 0, "VERDICT: PASS"),
    ("a folder of skills", ["examples/refs"], 1, "=" * 60),
    ("--json over two skills", ["examples/desc", "--json"], 1, '"verdict": "FAIL"'),
    ("--log-row", ["examples/before/release-notes", "--log-row", "--quiet"], 1, "| FAIL | 1 FAIL / "),
    ("--log-row on a PASS with an undecided gate", ["examples/refs/intact", "--log-row"], 0,
     "NOT CHECKABLE at gate 4"),
]

# A PASS with two undecided rows prints the plural count. The fixture is
# examples/refs/intact with its worked example cut to an inline mention, which
# leaves gate 4 and gate 7 NOT CHECKABLE and every other row PASS.
INLINE_EXAMPLE = "For example, a run that finds two fragments sharing a manifest key reports the collision.\n"

# The worked example's own check, examples/after/release-notes/check_notes.py.
# The after-example says its hard-fails are real because this script exits
# non-zero; these cases run it so that claim is tested, not just shipped.
# (label, changelog text or None for a path that is not there, argv after the
# changelog, summary text or None, expected exit code)
CHANGELOG = "# Changelog\n\n## Unreleased\n\n- Faster export\n\n## v2.1.0\n\n- New dashboard\n"
NOTES_CASES = [
    ("a file with no ## sections", "just prose\n", [], None, 3),
    ("a changelog that is not there", None, [], None, 3),
    ("version found, summary within budget", CHANGELOG, ["--version", "v2.1.0"], "A new dashboard.", 0),
    ("version the changelog does not contain", CHANGELOG, ["--version", "v9.9.9"], None, 1),
    ("summary over the 200-character budget", CHANGELOG, [], "x" * 201, 1),
    ("summary that ships an Unreleased entry", CHANGELOG, [], "Faster export.", 1),
    ("a summary file that is not there", CHANGELOG, ["--summary-file", "missing.txt"], None, 3),
    ("a version that only prefixes one in the changelog", CHANGELOG, ["--version", "v2.1"], None, 1),
    ("an Unreleased entry written as a '*' bullet",
     CHANGELOG.replace("- Faster export", "* Faster export"), [], "Faster export.", 1),
    ("an entry under a Keep-a-Changelog [Unreleased] heading", CHANGELOG.replace("## Unreleased", "## [Unreleased]"),
     [], "Faster export.", 1),
]
NOTES = os.path.join(ROOT, "examples", "after", "release-notes", "check_notes.py")

# The same script on an output stream that cannot encode its em dash: a cp437
# console or pipe, or a POSIX C locale (ascii). Both paths that print the dash
# must still exit as documented, never with a traceback's exit 1, which reads
# as FAIL. (encoding, then a NOTES_CASES row)
NOTES_ENCODING_CASES = [(enc,) + row for enc in ("cp437", "ascii")
                        for row in (NOTES_CASES[0], NOTES_CASES[2])]


def run(argv, cwd=None, encoding="utf-8"):
    """(exit code, stdout, stderr) of a Python script, decoded leniently.

    text=True would decode the child's output with the parent's locale
    encoding, which is not necessarily the encoding the child wrote in (a
    Windows console under a legacy code page is the case that bites). These
    tests grade exit codes and a few words; they must never die decoding the
    output they only echo on failure. So: decode explicitly, never strictly.
    """
    proc = subprocess.run([sys.executable] + argv, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace",
                          env=dict(os.environ, PYTHONIOENCODING=encoding))
    return proc.returncode, proc.stdout, proc.stderr


def in_temp(files, fn):
    """Write {relative path: bytes} to a temp folder, call fn(folder), clean up."""
    tmp = tempfile.mkdtemp(prefix="skill-audit-case-")
    try:
        for rel, content in files.items():
            full = os.path.join(tmp, *rel.split("/"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as fh:
                fh.write(content)
        return fn(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def row_status(description, body, gate):
    """The status on one gate's row, for a skill written to a temp folder."""
    skill = "---\nname: fixture\ndescription: %s\n---\n\n# fixture\n\n%s" % (description, body)
    _code, out, _err = in_temp({"fixture/SKILL.md": skill.encode("utf-8")},
                               lambda d: run([CHECKER, os.path.join(d, "fixture"), "--json"]))
    try:
        rows = json.loads(out)["gates"]
    except (ValueError, KeyError, TypeError):  # no report: the checker did not grade
        return None
    return next((r["status"] for r in rows if str(r["gate"]) == gate), None)


def badge(stdout, tag):
    """The status word on the report row carrying `tag`, or None if absent.

    NOT CHECKABLE first: it is the only multi-word status, and a parser that
    cannot name it reports None, which reads as "the row was missing" — a
    different bug from the one that would be happening.
    """
    line = next((l for l in stdout.splitlines() if tag in l), "")
    return next((s for s in ("NOT CHECKABLE", "FAIL", "REVIEW", "PASS")
                 if s in line), None)


def report(ok, label, detail, echo=""):
    """Print one case's line, and the child's output under a failure."""
    print("  %-5s %-48s %s" % ("ok" if ok else "FAIL", label, detail))
    for line in ([] if ok else echo.splitlines()):
        print("        | %s" % line)
    return 0 if ok else 1


def fixture_case(rel, expected, label, ref_status, desc_status):
    code, out, _err = run([CHECKER, os.path.join(ROOT, rel)])
    ref_got, desc_got = badge(out, "[R]"), badge(out, "[D]")
    not_graded = any(l.startswith("Not graded:") for l in out.splitlines())
    # Every problem is named, not only the first: a regression that moves
    # the exit code and a preflight at once should say both.
    problems = [msg for bad, msg in (
        (code != expected, "exit %d, expected %d (%s)" % (code, expected, label)),
        (ref_status is not None and ref_got != ref_status,
         "[R] preflight %s, expected %s" % (ref_got, ref_status)),
        (desc_got != desc_status, "[D] preflight %s, expected %s" % (desc_got, desc_status)),
        (not not_graded, "no \"Not graded\" line under the verdict"),
    ) if bad]
    detail = "; ".join(problems) or "exit %d (%s, [D] %s%s)" % (
        code, label, desc_got, "" if ref_status is None else ", [R] %s" % ref_got)
    return report(not problems, rel, detail, out)


def refuse_case(label, content, word):
    code, _out, err = in_temp({"fixture/SKILL.md": content},
                              lambda d: run([CHECKER, os.path.join(d, "fixture")]))
    ok = code == 3 and "REFUSED" in err and word in err
    return report(ok, label, "exit 3, refused by name" if ok else
                  "exit %s, expected 3 naming %r" % (code, word), err)


def argv_case(label, argv, want, text):
    code, out, err = run([CHECKER] + argv, cwd=ROOT)
    ok = code == want and text in out + err
    return report(ok, label, "exit %d" % code if ok else
                  "exit %d, expected %d carrying %r" % (code, want, text), out + err)


def plural_case():
    with open(os.path.join(ROOT, "examples", "refs", "intact", "SKILL.md"), "rb") as fh:
        text = fh.read().decode("utf-8")
    text = text[:text.index("## Worked example")] + INLINE_EXAMPLE
    files = {"intact/SKILL.md": text.encode("utf-8")}
    for rel in ("verify.py", "scripts/pack.py"):
        with open(os.path.join(ROOT, "examples", "refs", "intact", *rel.split("/")), "rb") as fh:
            files["intact/" + rel] = fh.read()
    code, out, _err = in_temp(files, lambda d: run([CHECKER, os.path.join(d, "intact")]))
    ok = code == 0 and "2 gates it cannot decide" in out
    return report(ok, "a PASS with two undecided gates", "exit %d" % code, out)


def notes_case(label, changelog, args, summary, want, encoding="utf-8"):
    files = {} if changelog is None else {"CHANGELOG.md": changelog.encode("utf-8")}
    if summary is not None:
        files["draft.txt"] = summary.encode("utf-8")

    def go(d):
        argv = [NOTES, os.path.join(d, "CHANGELOG.md")] + args
        return run(argv + (["--summary-file", os.path.join(d, "draft.txt")] if summary is not None else []),
                   cwd=d, encoding=encoding)
    code, out, err = in_temp(files, go)
    ok = code == want and "Traceback" not in err
    where = "" if encoding == "utf-8" else " (%s)" % encoding
    return report(ok, "check_notes.py  " + label + where, "exit %d" % code if ok else
                  "exit %d, expected %d" % (code, want), out + err)


def unit_cases():
    """The checker's own functions, called in this process. Each covers a
    branch no command line reaches: the code that keeps the checker alive
    where stdout cannot be reconfigured or a folder cannot be listed, and
    parse_frontmatter's answer for text with no frontmatter, which a caller
    importing the engine gets even though the command line refuses such a file
    before it is parsed. Returns the number of failures."""
    spec = importlib.util.spec_from_file_location("skill_audit_under_test", CHECKER)
    sa = importlib.util.module_from_spec(spec)
    real = sys.stdout
    sys.stdout = io.StringIO()  # no reconfigure(): the import must survive it
    try:
        spec.loader.exec_module(sa)
    finally:
        sys.stdout = real
    listdir = os.listdir

    def unlistable(path):
        raise OSError("not listable: %s" % path)
    os.listdir = unlistable
    try:
        md = os.path.join(ROOT, "examples", "refs", "intact", "SKILL.md")
        scripts = sa.load_skill(md)["scripts"]
        refs = sa._bundle_refs({"dir": os.path.dirname(md)})
    finally:
        os.listdir = listdir
    checks = [
        ("import with a stdout that cannot be reconfigured", sa.NOTCHECK == "NOT CHECKABLE"),
        ("an unlistable skill folder lists no scripts", scripts == []),
        ("an unlistable skill folder claims no bundled paths", refs == ([], [], set())),
        ("parse_frontmatter on text with no frontmatter", sa.parse_frontmatter("# x\n") == ({}, "# x\n")),
        ("parse_frontmatter on frontmatter never closed",
         sa.parse_frontmatter("---\nname: x\n") == ({}, "---\nname: x\n")),
        ("an offset before the first heading", sa._section_of("intro\n# H\n", [(6, 10)], 2) == (0, 6)),
    ]
    return sum(report(ok, label, "ok" if ok else "wrong answer") for label, ok in checks)


def floor_case():
    """The checker loaded by an interpreter that reports itself as Python 3.7:
    it exits 4 and names the 3.8 floor, instead of failing later on a line an
    old interpreter cannot run. Returns the number of failures."""
    spec = importlib.util.spec_from_file_location("skill_audit_below_floor", CHECKER)
    sa = importlib.util.module_from_spec(spec)
    real_version, real_err, err, code = sys.version_info, sys.stderr, io.StringIO(), None
    sys.version_info, sys.stderr = (3, 7, 9, "final", 0), err
    try:
        spec.loader.exec_module(sa)
    except SystemExit as exc:
        code = exc.code
    finally:
        sys.version_info, sys.stderr = real_version, real_err
    ok = code == 4 and "3.8" in err.getvalue()
    return report(ok, "a Python below the 3.8 floor is refused by name", "exit %s" % code, err.getvalue())


def harness_cases():
    """This harness, run against a checker that grades nothing and against one
    that is not there. A test that cannot fail tests nothing: if every case
    above went green on a checker that exits 0 and prints one line, the
    assertions would be the defect. Returns the number of failures."""
    def go(d):
        stub = os.path.join(d, "stub.py")
        with open(stub, "w", encoding="utf-8") as fh:
            fh.write("print('stub')\n")
        out = []
        for label, checker, want in (("a checker that grades nothing", stub, 1),
                                     ("a checker that is not there", os.path.join(d, "none.py"), 2)):
            proc = subprocess.run([sys.executable, os.path.abspath(__file__)], capture_output=True,
                                  env=dict(os.environ, SKILL_AUDIT_TEST_CHECKER=checker))
            out.append(report(proc.returncode == want, "this test, on " + label,
                              "exit %d (want %d)" % (proc.returncode, want)))
        return sum(out)
    return in_temp({}, go)


def readme_cases():
    """Two README claims, checked on this skill's own SKILL.md. "The seven
    gates": the report grades exactly gates 1-7, beside its two preflights.
    "Who makes this" names explicit triggers, enforced hard-fails, stated
    scope boundaries and a worked example per skill: the skill shipped here
    passes the gates that grade those four (2, 3, 5 and 7). Returns the
    number of failures."""
    _code, out, _err = run([CHECKER, ROOT, "--json"])
    try:
        rows = {str(r["gate"]): r["status"] for r in json.loads(out)["gates"]}
    except (ValueError, KeyError, TypeError):  # no report: the checker did not grade
        rows = {}
    numbered = sorted(g for g in rows if g.isdigit())
    own = {g: rows.get(g) for g in ("2", "3", "5", "7")}
    return (report(numbered == [str(n) for n in range(1, 8)], "the report grades the seven gates",
                   "gates %s" % (",".join(numbered) or "none"), out)
            + report(set(own.values()) == {"PASS"}, "this skill passes gates 2, 3, 5 and 7",
                     " ".join("%s %s" % kv for kv in own.items()), out))


def main():
    missing =[rel for rel, *_rest in CASES if not os.path.isdir(os.path.join(ROOT, rel))]
    if not os.path.isfile(CHECKER) or missing:
        print("test_fixtures: setup error: %s" % ("checker not found at %s" % CHECKER
              if not os.path.isfile(CHECKER) else "fixture missing: " + ", ".join(missing)),
              file=sys.stderr)
        return 2

    failures = sum(fixture_case(*c) for c in CASES)
    for label, description, body, gate, want in ROW_CASES:
        got = row_status(description, body, gate)
        failures += report(got == want, label, "[%s] %s" % (gate, got) if got == want else
                           "[%s] %s, expected %s" % (gate, got, want))
    for label, files, gate, wants in G1_CASES:
        got = skill_row(files, gate)
        failures += report(got in wants, label, "[%s] %s" % (gate, got) if got in wants else
                           "[%s] %s, expected %s" % (gate, got, " or ".join(wants)))
    failures += sum(refuse_case(*c) for c in REFUSE_CASES)
    failures += sum(argv_case(*c) for c in ARGV_CASES)
    failures += plural_case()
    failures += skill_md_folder_case()
    failures += sum(notes_case(*c) for c in NOTES_CASES)
    failures += sum(notes_case(*c[1:], encoding=c[0]) for c in NOTES_ENCODING_CASES)
    failures += readme_cases()
    total = (len(CASES) + len(ROW_CASES) + len(G1_CASES) + len(REFUSE_CASES) + len(ARGV_CASES) + 2 + len(NOTES_CASES)
             + len(NOTES_ENCODING_CASES) + 2)
    if not STUBBED:  # the real checker only: these import it, or run this file
        failures += unit_cases() + floor_case() + harness_cases()
        total += 6 + 1 + 2

    print("")
    if failures:
        print("test_fixtures: %d of %d cases did not grade as expected." % (failures, total))
        return 1
    print("test_fixtures: %d/%d ok." % (total, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
