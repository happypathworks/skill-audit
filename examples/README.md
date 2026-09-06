# Worked example — one skill, before and after

This is the same skill twice. `before/` is what a useful, well-meant, entirely
ordinary skill looks like before anyone has checked it. `after/` is the same
skill with each gate answered. Nothing was rewritten for style; every change
exists because a gate named something specific.

Run it yourself:

    python3 skill_audit.py examples/before/release-notes
    python3 skill_audit.py examples/after/release-notes

Both fixtures are demonstration inputs. Their frontmatter says so, and neither
is meant to be installed as a working skill.

---

## before/ — `FAIL`, exit 1

The skill is not badly written. It is clear, it is short, and a person reading
it would know roughly what to do. That is exactly the problem the Floor exists
to catch: readable and reliable are different properties, and only one of them
survives a cold context.

```
skill_audit — release-notes
           examples/before/release-notes/SKILL.md

  [1] Names the gap              REVIEW No gap statement detected.
        → State in one sentence what the base model gets wrong or does inconsistently without this skill.
  [2] Deterministic entry        REVIEW No trigger mechanism detected at all.
        → Declare how the skill fires — a deterministic entry (a prefix or unambiguous condition) is the most predictable.
  [3] Enforced hard-fails        REVIEW Rule-like imperatives are present but no explicit hard-fail is declared or enforced.
        → If any of these must always hold, name it as a hard-fail and back it with a check rather than leaving it as prose.
  [4] Verify before voice        FAIL   A countable/spec'd constraint is present but no verification step was detected.
        → Write the output around a verified result — run the check first, then speak. (Gate 4)
  [5] Loud failure, named exit   REVIEW No scope boundary detected.
        → Confirm the skill can't be pulled out of scope, or add a boundary with a named exit.
  [6] Survives cold handoff      REVIEW Cold-handoff survival can't be settled by a static lint.
        → Prove it by running the skill in a clean context on a fixture (an ablation) and comparing the result.
  [7] Deciding example           REVIEW An example is present but reads like a happy path.
        → Confirm at least one example shows the skill catching a case that would otherwise go wrong. (Gate 7)

FAIL 1   REVIEW 6   PASS 0

VERDICT: FAIL
At least one gate failed on a detectable anti-pattern. Fix the → items and re-run.

before exit: 1
```

## after/ — `REVIEW`, exit 2

```
skill_audit — release-notes
           examples/after/release-notes/SKILL.md
           scripts: check_notes.py

  [1] Names the gap              PASS   A gap/failure-mode statement is present.
  [2] Deterministic entry        PASS   A deterministic entry (prefix or unambiguous condition) is present.
  [3] Enforced hard-fails        PASS   Hard-fails are present and the skill ships a script (check_notes.py).
  [4] Verify before voice        PASS   A hard constraint is present and a verification step is described.
  [5] Loud failure, named exit   PASS   Scope boundaries name an explicit exit (if X, refuse and do Y).
  [6] Survives cold handoff      REVIEW Cold-handoff survival can't be settled by a static lint.
        → Prove it by running the skill in a clean context on a fixture (an ablation) and comparing the result.
  [7] Deciding example           PASS   A worked example is present and shows a catch, not just the happy path.

FAIL 0   REVIEW 1   PASS 6

VERDICT: REVIEW
No detectable failures. The REVIEW gates need a human ruling or a deeper pass (a static lint can't settle them). This is the normal result for a decent skill.

after exit: 2
```

`REVIEW` with no `FAIL`s is the target, not a consolation prize. Gate 6 cannot
be settled by a static lint — proving a skill survives a cold handoff means
running it in a clean context, which is a thing a person does, not a thing a
regex concludes. A tool that printed a green `PASS` there would be lying to
you about what it checked.

---

## What actually changed, gate by gate

| Gate | before | after | The change |
|---|---|---|---|
| 1 Names the gap | REVIEW | PASS | Added the sentence that says what goes wrong without the skill: invented version numbers, unreleased features announced, budgets estimated instead of counted. |
| 2 Deterministic entry | REVIEW | PASS | The keyword pile ("release notes, changelogs, version notes, shipping updates, patch notes") became one prefix: `rel:`. A pile of synonyms is a hope that the model guesses; a prefix is a decision. |
| 3 Enforced hard-fails | REVIEW | PASS | The three `Never` bullets stayed, but each one now names the exit code `check_notes.py` returns when it trips. A rule with no check behind it is a preference. |
| 4 Verify before voice | **FAIL** | PASS | "Keep the summary under 200 characters" was a countable constraint with nothing counting it. Now the count is run before the notes are written, and the real number is printed. |
| 5 Loud failure, named exit | REVIEW | PASS | "Use it whenever you need release notes" had no boundary at all. Now: not a changelog → refuse, say so, exit 3. |
| 6 Survives cold handoff | REVIEW | REVIEW | Unchanged, and unchangeable by lint. "Match the tone used in the last few releases" was removed — it pointed at context the file does not contain — but proving survival still takes an ablation run. |
| 7 Deciding example | REVIEW | PASS | The happy-path example (three entries in, three entries out) was replaced with the case that decides it: a changelog where the obvious answer is wrong twice. |

## The part worth stealing

Gate 4 is the only outright `FAIL` in `before/`, and it is the cheapest one to
ship by accident. "Keep the summary under 200 characters" reads like a
constraint. It behaves like a wish. The difference between the two versions is
not better prose — it is a nine-line script that counts and exits non-zero.

That is the whole argument, in one gate: the thing that separates a product
from a prompt is usually not the writing. It is whether anything checks.
