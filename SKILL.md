---
name: skill-audit
description: >-
  Lints a Claude skill against a seven-gate quality Floor and reports it gate
  by gate, with a specific fix for each miss. Any message beginning with
  "audit:" invokes this skill — treat this prefix as a command. `audit:` followed
  by a path grades one skill; `audit:` pointed at a folder grades each skill
  inside it.
  Without this skill, asked whether a skill is any good, the base model
  writes a thoughtful review, but a different one each time, and none of
  them is a check: it will question what a length limit means, never that
  no step ever counts it. This skill runs
  skill_audit.py and writes the verdict around the exit code the check actually
  returns. Not for writing a skill, or for editing or improving one — its
  description, its trigger, its steps: that is skill-creator's job.
license: MIT
---

# skill-audit

## Trigger

- `audit: <path>` — grade one skill (a directory with a SKILL.md, or a SKILL.md
  file).
- `audit: <folder>` — grade every skill in a folder of skills.
- Append `--json` for machine-readable output, `--quiet` to drop the per-gate
  fix lines, `--log-row` for a one-line row you can paste into build notes.

## How to run it

Run the bundled checker before you write, and build your answer from its
output. Run from this skill's own folder, the command is:

```
python3 skill_audit.py <path>
```

**From anywhere else, put that folder's path in front of `skill_audit.py`.** It
ships beside this `SKILL.md`. The working directory is the user's
project, not the skill folder, and the bare command fails there with "can't
open file". On Claude Code the folder is usually
`~/.claude/skills/skill-audit/` or `<project>/.claude/skills/skill-audit/`;
elsewhere it is wherever the skill was unpacked. Never guess it — read it off
this file's own location. If `python3` is not on `PATH` (the usual case on
Windows), use `python`.

Read its exit code and its gate table. Present the verdict, the per-gate lines,
the `->` fixes, and the *Not graded* line under the verdict with its step. Do
not add gates it did not report, and do not soften a FAIL into a suggestion.

The table opens with two preflights, not gates.

`[D] Upload-safe description` checks the description against the two platform
limits that break silently. Over 1024 characters it is truncated on ingest and
the tail is lost with no warning. Anything shaped like an XML tag is refused
outright — claude.ai answers the upload with *"SKILL.md description cannot
contain XML tags"*, and the usual cause is a placeholder such as `recheck
<path>`, not markup. A `[D]` FAIL is not a design flaw and must not be softened
into one: say what the span or the overage is, and that the fix is in the
frontmatter.

`[R] References resolve` checks that every path the skill *claims to ship*
exists, and reports how many workspace paths it skipped as out of reach. An
`[R]` FAIL is a missing file: ship the file or fix the path. An `[R]` REVIEW is
weaker on purpose — the path is absent but only named in passing, so it is
either a stale reference or prose about a file the reader would write. Do not
promote that REVIEW to a FAIL. Do not extend it to the paths it skipped — those
need a cold run, which this skill does not perform. `--no-refs` skips the
preflight.

## Hard-fails (rules for the reply, read off skill_audit.py's exit code)

- **No verdict the check did not produce.** The response is written around
  `skill_audit.py`'s real exit code (`0` PASS / `2` REVIEW / `1` FAIL). If the
  script did not run, refuse to grade — do not free-hand a review.
- **No grading a non-skill.** If the path has no SKILL.md, the script exits `3`;
  report that and stop, rather than inventing a critique.
- **No promoting a REVIEW to PASS from prose.** A gate the lint marks REVIEW
  stays REVIEW. Only a deeper pass (a cold-run ablation) can raise it, and this
  skill does not perform one.
- **No reporting a PASS verdict without what it leaves out.** `exit 0` means
  every gate the lint *decided* came back clean. The sentence that reports a
  PASS also gives the `NOT CHECKABLE` count as a number, and the *Not graded*
  line in the script's own words, starting "Not graded:": whether the skill
  works in a fresh session, which no lint grades. For example: "PASS (exit 0),
  1 NOT CHECKABLE. Not graded: whether the skill works in a fresh session." A
  PASS reported as "the skill works", or as "all gates passed" when some were
  never decided, is a claim the run did not make.

## Scope — and where it refuses

It grades Claude Agent Skills: a SKILL.md, optionally with sibling scripts.

- If pointed at a loose prompt or a code repository with no SKILL.md: refuse,
  say it is not a gradable skill, and stop.
- If asked to fix or rewrite the skill in the same breath: report the audit,
  then stop. Leave the skill's files unedited and say, naming skill-creator,
  that the rewrite is a separate pass for it. Say it on a PASS too: "nothing to
  fix" is a claim the lint did not make.

## What it cannot do (so it doesn't pretend to)

Each gate reads a short list of phrasings, set out gate by gate in README.md
under "What each gate reads". It FAILs only on those; a weaker match comes back
REVIEW, and a rule written in other words goes unseen. It **cannot** tell you whether your gap statement is true,
whether your example is genuinely deciding, or whether the skill works in a
fresh session. Gates it can see but not judge come back REVIEW; gates a skill
gives it nothing to test come back NOT CHECKABLE and are left out of the
verdict.

## Worked example (a catch, not a happy path)

A skill called `meeting-summarizer` looks fine at a glance: a description, a
`## Hard-fails` section, an example. Run `audit:` on it:

- **Gate 3 → FAIL.** Under "Hard-fails" it declares "this is a hard-fail: never
  ship a summary that invents an action item" — an explicit hard-fail, with
  nothing behind it.
- **Gate 4 → FAIL.** "Keep every summary under 200 words." A countable
  constraint, asserted and hoped — no step that counts the words before the
  model speaks.
- **Gate 5 → FAIL.** "Try to stay on the meeting content and avoid drifting." A
  soft boundary, no named exit — scope you hope holds, not "if X, refuse and do
  Y."

Verdict: **FAIL**, exit `1`, with the exact fix under each line: three declared
rules, and not one of them enforced.

Its keyword-only trigger and its happy-path example come back **REVIEW**, not
FAIL: those are for your eyes.
