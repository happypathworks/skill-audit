# skill-audit

Points at a Claude skill and grades it against a published seven-gate quality
floor. Reports gate by gate, with one concrete fix per miss, and exits with a
code you can script against.

Free, MIT, no dependencies. If you can run `python3 --version`, you can run this.

## The gap it closes

Ask a model "is this skill any good?" and it writes a confident, agreeable
paragraph that checks nothing. The read that does not survive being done from
memory is the mechanical one: whether the trigger is a real prefix or a pile of
synonyms, whether each hard-fail has a check behind it or is just a sentence,
whether the one example shows a catch or the happy path.

This runs that read every time, the same way, and reports what it actually found.

## It grades itself

```
skill_audit — skill-audit
           SKILL.md
           scripts: skill_audit.py

  [1] Names the gap              PASS   A gap/failure-mode statement is present.
  [2] Deterministic entry        PASS   A deterministic entry (prefix or unambiguous condition) is present.
  [3] Enforced hard-fails        PASS   Hard-fails are present and the skill ships a script (skill_audit.py).
  [4] Verify before voice        PASS   A hard constraint is present and a verification step is described.
  [5] Loud failure, named exit   PASS   Scope boundaries name an explicit exit (if X, refuse and do Y).
  [6] Survives cold handoff      REVIEW Cold-handoff survival can't be settled by a static lint.
        → Prove it by running the skill in a clean context on a fixture (an ablation) and comparing the result.
  [7] Deciding example           PASS   A worked example is present and shows a catch, not just the happy path.

FAIL 0   REVIEW 1   PASS 6

VERDICT: REVIEW
No detectable failures. The REVIEW gates need a human ruling or a deeper pass (a static lint can't settle them). This is the normal result for a decent skill.

```

`REVIEW` with no `FAIL`s is the target, not a consolation prize. Gate 6 cannot
be settled by a static lint — proving a skill survives a cold handoff means
running it in a clean context, which is something a person does. A tool that
printed a green `PASS` there would be lying about what it checked.

## The preflight

Before the gates, one integrity check. `[R] References resolve` verifies that
every path the skill *claims to ship* actually exists — a renamed helper, a
deleted script, a `references/` file that moved. Gate 3 cannot see this: it
counts a skill "enforced" if any script sits in its directory, which a stale
reference still satisfies.

It is deliberately narrow. A path counts only where the skill's own layout
vouches for it — its first segment is a directory the skill ships, or it is a
bare script the skill tells you to **run** in a skill that ships scripts.
Everything else a SKILL.md mentions (`word/document.xml` inside a document
being unpacked, `.claude/settings.json` in the user's repo, an output path, a
script the model is told to write) is a workspace path: it cannot resolve here,
so it is counted as skipped and never flagged. Verified against 31 known-good
skills with zero false positives.

Pass `--no-refs` to skip it.

## The seven gates

| | Gate | A failure looks like |
|---|---|---|
| 1 | Names the gap | The skill never says what goes wrong without it. It reads as a nice-to-have because nothing establishes the need. |
| 2 | Deterministic entry | The trigger is a pile of synonyms instead of a prefix or an unambiguous condition. It fires when it shouldn't and stays quiet when it should. |
| 3 | Enforced hard-fails | Rules stated as prose with nothing checking them. A rule with no check behind it is a preference. |
| 4 | Verify before voice | A countable constraint — a character limit, a spec, a format — that nothing counts. The output is written around an estimate. |
| 5 | Loud failure, named exit | Scope language with a soft exit. "Try to stay in scope" instead of "if X, refuse and do Y". |
| 6 | Survives cold handoff | The skill references context it does not contain. In a fresh session it quietly does something else. |
| 7 | Deciding example | The only example is the happy path, so it demonstrates nothing that could have gone wrong. |

## Install

Drop the folder into your skills directory:

    git clone https://github.com/happypathworks/skill-audit.git \
      ~/.claude/skills/skill-audit

Or, for one project:

    git clone https://github.com/happypathworks/skill-audit.git \
      <project>/.claude/skills/skill-audit

No `git`? Download the repository as a ZIP and unpack it to the same place — the
folder only has to be named `skill-audit` and sit directly inside a skills
directory.

Nothing to install after that. Python 3.8+, standard library only.

## Compatibility

Claude Code only. Skills do not run in the claude.ai web app or in the Claude
desktop app's chat, and a skill folder you install locally is not visible to
Cowork or cloud sessions. There is no minimum Claude Code version: this skill
uses no version-gated feature.

Python 3.8 or later, standard library only. That floor is checked, not claimed —
CI runs the fixtures and the self-audit on 3.8 and 3.12 on every push, plus a
Windows leg that forces a legacy `cp1252` console so the report is known to
render where it once crashed.

`SETUP.md` has the full statement, including what each install route requires.

## Use

    audit: path/to/some-skill

- `audit: <path>` — grade one skill (a folder with a `SKILL.md`, or a `SKILL.md`).
- `audit: <folder>` — grade every skill in a folder of skills.
- `--json` for machine-readable output, `--log-row` for a build-notes row.

Or run the checker directly, without the skill:

    python3 skill_audit.py path/to/some-skill

## Exit codes

    exit 0   PASS     every gate passed
    exit 2   REVIEW   no failures, but a gate needs a human ruling
    exit 1   FAIL     a gate failed, or a bundled file is missing — fix the
                     → items and re-run
    exit 3   ERROR    nothing gradable at that path

## Worked example

`examples/` holds the same skill twice — once before anyone checked it, once
after each gate was answered — with the real output of both runs and a
gate-by-gate account of what changed and why. Start there.

    python3 skill_audit.py examples/before/release-notes   # exit 1, FAIL
    python3 skill_audit.py examples/after/release-notes    # exit 2, REVIEW
    python3 skill_audit.py examples/refs/broken            # exit 1, missing file
    python3 skill_audit.py examples/refs/intact            # exit 2, refs resolve

## Tests

    python3 tests/test_fixtures.py

Asserts both fixtures still return the exit code they are supposed to. The
second assertion is the one that matters: a lint that fails good input loses a
stranger's trust on first contact, and there is no second contact.

## What it does not do

It does not rewrite your skill — it diagnoses and points; fixing is a separate
pass. It grades Claude Agent Skills (a `SKILL.md`, optionally with sibling
scripts), not loose prompts or code repositories. Pointed at something that
isn't a skill, it says so and stops rather than inventing a critique.

It is a lint. It catches the structural tells a machine can catch, and it says
plainly where a human still has to look.

## License

MIT. See `LICENSE`. Use it, fork it, strip the parts you don't want.

## Who makes this

Happy Path Works builds Claude skills as systems: explicit triggers, enforced
hard-fails, stated scope boundaries, a worked example per skill.

Changes to this tool, and the next ones as they ship, go out on the list:
[happypathworks.beehiiv.com](https://happypathworks.beehiiv.com/subscribe?utm_source=skill-audit).
No cadence promised beyond that — it is a changelog you do not have to poll.

Questions and bug reports: hello@happypath.works
