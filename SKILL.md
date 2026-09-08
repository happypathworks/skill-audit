---
name: skill-audit
description: >-
  Lints a Claude skill against a seven-gate quality Floor and reports it gate
  by gate, with a specific fix for each miss. Primary trigger is any message
  beginning with "audit:" — treat this prefix as a command. `audit:` followed
  by a path grades one skill; `audit:` pointed at a folder grades each skill
  inside it.
  Without this skill, asked whether a skill is any good, the base model
  free-associates a plausible-sounding review and never mechanically checks the
  structural tells — a keyword-only trigger, hard-fails asserted in prose, a
  happy-path example — that separate a product from a prompt. This skill runs
  skill_audit.py and writes the verdict around the exit code the check actually
  returns.
license: MIT
---

# skill-audit

Point it at a skill; it grades that skill against the seven-gate Floor and hands
back a gate-by-gate verdict with one concrete fix per miss. It is a lint, not a
verdict on your taste: it catches the structural tells a machine can catch, and
it says plainly where a human still has to look.

## The gap it closes

Ask a bare model "is this skill any good?" and it will write you a confident,
agreeable paragraph that checks nothing. The thing that does not survive being
done from memory is the *mechanical* read — counting whether the trigger is a
real prefix or a pile of keywords, whether each hard-fail has a check behind it
or is just a sentence, whether the one example shows a catch or the happy path.
This skill runs that read every time, the same way, and reports it.

## Trigger

Any message beginning with `audit:` fires this skill. Treat the prefix as a
command, not a topic.

- `audit: <path>` — grade one skill (a directory with a SKILL.md, or a SKILL.md
  file).
- `audit: <folder>` — grade every skill in a folder of skills.
- Append `--json` for machine-readable output, `--log-row` for a build-notes row.

## How to run it

Run the bundled checker and build your answer from its output:

```
python3 skill_audit.py <path>
```

If `python3` is not on `PATH` — the usual case on Windows — run the same command
with `python`. Nothing else about the invocation changes.

Read its exit code and its gate table. Present the verdict, the per-gate lines,
and the `→` fixes. Do not add gates it did not report, and do not soften a FAIL
into a suggestion — the point of the tool is that the verdict is mechanical.

The table opens with `[R] References resolve` — a preflight, not a gate. It
checks that every path the skill *claims to ship* exists, and reports how many
workspace paths it skipped as out of reach. Report it as the script gives it:
an `[R]` FAIL is a missing file, not a design flaw, and the fix is to ship the
file or fix the path. Do not extend it to the paths it skipped — those need a
cold run, which this skill does not perform. `--no-refs` skips the preflight.

## Hard-fails (enforced by skill_audit.py)

- **No verdict the check did not produce.** The response is written around
  `skill_audit.py`'s real exit code (`0` PASS / `2` REVIEW / `1` FAIL). If the
  script did not run, refuse to grade — do not free-hand a review.
- **No grading a non-skill.** If the path has no SKILL.md, the script exits `3`;
  report that and stop, rather than inventing a critique.
- **No promoting a REVIEW to PASS from prose.** A gate the lint marks REVIEW
  stays REVIEW. Only a deeper pass (a cold-run ablation) can raise it, and this
  skill does not perform one.

Every hard-fail above is backed by the exit code the script returns, not by this
sentence.

## Scope — and where it refuses

It grades Claude Agent Skills: a SKILL.md, optionally with sibling scripts. It
diagnoses and points; it does **not** rewrite your skill — that is a separate
pass (skill-creator's job). 

- If pointed at a loose prompt or a code repository with no SKILL.md: refuse,
  say it is not a gradable skill, and stop.
- If asked to fix or rewrite the skill in the same breath: report the audit
  first, then treat the rewrite as a distinct request.

## What it cannot do (so it doesn't pretend to)

The lint settles the mechanical gates — trigger shape, prose-vs-checked
hard-fails, soft-vs-named scope exits, example-vs-catch. It **cannot** tell you
whether your gap statement is true, whether your example is genuinely deciding,
or whether the skill survives a cold run. Those come back REVIEW on purpose. A
clean lint is a REVIEW at best, never a green PASS — because presence is not
quality, and only running the skill cold can prove the last gate. That honesty
is the tool.

## Worked example (a catch, not a happy path)

A skill called `meeting-summarizer` looks fine at a glance: a description, a
`## Hard-fails` section, an example. Run `audit:` on it:

- **Gate 3 → FAIL.** Under "Hard-fails" it declares "this is a hard-fail: never
  ship a summary that invents an action item" — an explicit hard-fail, with
  nothing behind it. No script, no check, no exit code. The lint sees the
  declaration, finds no enforcement, and FAILs: a hard-fail that lives in a
  sentence is a suggestion. A reader nods along and moves on.
- **Gate 4 → FAIL.** "Keep every summary under 200 words." A countable
  constraint, asserted and hoped — no step that counts the words before the
  model speaks. Verify before voice.
- **Gate 5 → FAIL.** "Try to stay on the meeting content and avoid drifting." A
  soft boundary, no named exit — scope you hope holds, not "if X, refuse and do
  Y."

Verdict: **FAIL**, exit `1`, with the exact fix under each line. The skill that
read as competent is a prompt wearing a product's clothes — three declared rules
and not one of them enforced — and the tool says so in the time it takes to run,
instead of the paragraph of agreeable nothing a bare model would have written.

(Its keyword-only trigger and its happy-path example come back **REVIEW**, not
FAIL: a description-based trigger is the ecosystem norm, and a lint can't
prove an example fails to decide — those are for your eyes, not the machine's.)
