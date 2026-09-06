---
name: release-notes
description: >-
  EXAMPLE FIXTURE — the repaired "after" half of the skill-audit worked
  example. It is a demonstration input, not a skill meant to be installed.
  Turns a changelog into release notes. PRIMARY TRIGGER is any message
  beginning with `rel:` — treat that prefix as a command. `rel:` followed by a
  path reads that changelog; bare `rel:` reads the newest unreleased section.
  Without this skill the base model writes release notes from memory of the
  diff, silently invents version numbers that look plausible, and blows the
  200-character summary budget because it never counts.
---

# release-notes

Turns a changelog into release notes, with the version number and the summary
length verified before anything is written.

## The gap it closes

Asked for release notes, the base model writes a confident paragraph from
whatever it remembers of the changes. Three things do not survive being done
from memory: the version number (it invents one that looks right), the
unreleased/released boundary (it announces things that have not shipped), and
the summary budget (it estimates 200 characters instead of counting them).
This skill checks all three mechanically before it writes a word.

## Trigger

Any message beginning with `rel:` fires this skill. Treat the prefix as a
command, not a topic.

- `rel: <path>` — read that changelog file.
- `rel:` — read the newest unreleased section of `CHANGELOG.md`.

## How to run it

```
python check_notes.py <changelog-path> --version <vX.Y.Z> --summary-file <draft.txt>
```

Read its exit code and build the response around what it returned. Do not
write the notes before the check has run.

## Hard-fails (enforced by check_notes.py)

- **No version number the changelog did not contain.** `check_notes.py` exits
  `1` if the version in the draft is absent from the source file. Never supply
  one from context or inference.
- **No unreleased entry in shipped notes.** Entries under an `Unreleased`
  heading exit `1`. There is no judgment call here and no "but it's basically
  done".
- **No unverified summary length.** The summary is no more than 200 characters,
  and that is counted, not estimated. `check_notes.py` verifies the count before
  you write and exits `1` over budget, printing the real number.

## Scope boundary

This skill reads a changelog and writes release notes from it.

If the input is not a changelog, refuse and say so. A diff, a commit log, an
issue tracker export, or a prose description of changes are all out of scope.
Exit with:

```
release-notes: not a changelog at <path> — nothing to read. (exit 3)
```

Do not reconstruct a changelog from a diff in order to proceed. The reason the
version and unreleased checks work is that the source file is authoritative;
a reconstructed source is an invented source wearing the same name.

## Example — the one that decides it

A changelog whose newest section is:

```
## Unreleased
- Added dark mode.

## v2.0.4 — 2026-03-11
- Fixed a crash on export.
```

The tempting answer is `v2.1.0 — Added dark mode, fixed a crash on export`,
which is wrong twice: `v2.1.0` appears nowhere in the file, and dark mode has
not shipped. The check catches both before anything is written:

```
$ python check_notes.py CHANGELOG.md --version v2.1.0 --summary-file draft.txt
  version 'v2.1.0' not found in CHANGELOG.md
  entry 'Added dark mode.' is under Unreleased
  summary: 50 / 200 characters — ok
exit 1
```

Correct output is notes for `v2.0.4` covering the export crash, and a line
saying dark mode is unreleased and therefore excluded.
