# skill-audit

Points at a Claude skill and grades it against a seven-gate quality floor —
published in full further down this page. Reports gate by gate, with one
concrete fix per miss, and exits with a code you can script against.

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

  [R] References resolve         PASS          All 1 bundled path(s) resolve. (1 workspace path(s) skipped — not this skill's to resolve)
  [1] Names the gap              PASS          A gap/failure-mode statement is present.
  [2] Deterministic entry        PASS          A deterministic entry (prefix or unambiguous condition) is present (`audit:`).
  [3] Enforced hard-fails        PASS          Hard-fails are present and the skill ships a script (skill_audit.py).
  [4] Verify before voice        PASS          A hard constraint is present and a verification step is described.
  [5] Loud failure, named exit   PASS          Scope boundaries name an explicit exit (if X, refuse and do Y).
  [6] No prior-chat references   PASS          No phrasing that leans on an earlier chat ("as we discussed", "like last time").
  [7] Deciding example           PASS          A worked example is present and shows a catch, not just the happy path.

FAIL 0   REVIEW 0   NOT CHECKABLE 0   PASS 8

VERDICT: PASS
Every gate came back clean.
Not graded: whether the skill works in a fresh session. The lint reads files; only a run shows what a model does with them.
        -> Open a session where your own project instructions do not load, install the skill from its archive, give it a real task that starts with `audit:`, and check what it does against what the skill promises.
```

Read the third column before the verdict. A gate comes back `PASS`, `REVIEW`,
`FAIL` — or `NOT CHECKABLE`, which is the tool declining to hold an opinion
when a skill gives a gate nothing it can test. Those rows do not count against
the verdict, and their count is printed beside it.

Then read the line under the verdict, because it is the one no gate covers.
Whether a skill works in a fresh session — somewhere its author's context does
not reach — takes running it, and a lint only reads files. So the report says
so under every verdict, with the step to take, instead of printing a green row
it did not earn. `PASS` means *nothing found and nothing owed*, not *the skill
works*: eight clean rows here, and a run still to do.

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
so it is counted as skipped and never flagged. A path on a line that announces
itself as illustrative (`**Examples**: references/finance.md for financial
schemas`) is skipped too — that names a file *you* might write.

**A missing path is only a `FAIL` when the skill points at it** — links it,
runs it, or introduces it with a pointer verb (`see`, `load`, `defined in`).
Named once in passing and absent, it comes back `REVIEW` instead. The reason is
specific: a skill documenting skill layout writes `references/patterns.md` as
advice in the same form it writes a file it really ships, so the two are
indistinguishable on the page and calling one broken would be inventing
evidence.

Measured against a known-good corpus of 32 skills — every skill in Anthropic's
official plugin marketplace, plus a local one — the whole lint returns zero
`FAIL`s.

Pass `--no-refs` to skip it.

## The seven gates

| | Gate | A failure looks like |
|---|---|---|
| 1 | Names the gap | The skill never says what goes wrong without it. It reads as a nice-to-have because nothing establishes the need. |
| 2 | Deterministic entry | Entry is undecided: a pile of synonyms, or a description that says what the skill is for and never what it is not for. It fires when it shouldn't and stays quiet when it should. A prefix decides entry; so does a description bounded on both sides — this gate asks whether entry is *decided*, not whether it is prefixed. |
| 3 | Enforced hard-fails | Rules stated as prose with nothing checking them. A rule with no check behind it is a preference. |
| 4 | Verify before voice | A countable constraint — a character limit, a spec, a format — that nothing counts. The output is written around an estimate. |
| 5 | Loud failure, named exit | Scope language with a soft exit. "Try to stay in scope" instead of "if X, refuse and do Y". |
| 6 | No prior-chat references | The skill leans on a conversation it does not contain — "as we discussed", "like last time". A fresh session never had that conversation, so it quietly does something else. |
| 7 | Deciding example | The only example is the happy path, so it demonstrates nothing that could have gone wrong. |

Gate 6 is the part of a bigger question that a file can show. The bigger
question — does the skill work in a fresh session at all? — is not a gate,
because answering it means running the skill, and the report says so under
every verdict. The worked example in `examples/` carries a line that shows why:
"Match the tone used in the last few releases" leans on context the file does
not carry, in words no phrase list would catch. A run catches it.

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

Runs wherever Claude runs — Claude Code, the claude.ai web app, Cowork, and the
desktop app. This is a standard Agent Skill: a `SKILL.md` plus one Python file,
nothing to build and nothing to fetch. There is no minimum Claude Code version
either; the skill uses no version-gated feature.

Where you install it differs by surface, and the two locations do not sync. A
folder under `~/.claude/skills/` or `.claude/skills/` is local to Claude Code on
that machine; skills added to your claude.ai account are the ones available in
the web app, Cowork, cloud sessions and routines. Installing one does not install
the other. That is about where the files live, not about where the skill can run.

Python 3.8 or later, standard library only. That floor is checked, not claimed —
CI runs the fixtures and the self-audit on 3.8 and 3.12 on every push, plus a
Windows leg that forces a legacy `cp1252` console so the report is known to
render where it once crashed.

`SETUP.md` has the full statement, including what each install route requires.

## Use

    audit: path/to/some-skill

- `audit: <path>` — grade one skill (a folder with a `SKILL.md`, or a `SKILL.md`).
- `audit: <folder>` — grade every skill in a folder of skills.
- `--json` for machine-readable output, `--quiet` to drop the per-gate fix
  lines, `--log-row` for a one-line row you can paste into build notes.

Or run the checker directly, without the skill:

    python3 skill_audit.py path/to/some-skill

## Exit codes

    exit 0   PASS     every gate the lint can decide came back clean, and
                     none needs a human ruling. Undecided gates are listed
                     as NOT CHECKABLE and do not block this
    exit 2   REVIEW   no failures, but a gate needs a human ruling
    exit 1   FAIL     a gate failed, or a bundled file is missing — fix the
                     -> items and re-run
    exit 3   ERROR    nothing gradable at that path

Script against `1` — that is the one that means something went wrong. `0` means
the lint is out of objections, which is not the same as the skill being proven:
read the `NOT CHECKABLE` rows, and the *Not graded* line under the verdict,
before you close the question.

## Worked example

`examples/` holds the same skill twice — once before anyone checked it, once
after each gate was answered — with the real output of both runs and a
gate-by-gate account of what changed and why. Start there.

    python3 skill_audit.py examples/before/release-notes   # exit 1, FAIL
    python3 skill_audit.py examples/after/release-notes    # exit 0, PASS
    python3 skill_audit.py examples/refs/broken            # exit 1, missing file
    python3 skill_audit.py examples/refs/intact            # exit 0, refs resolve

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
