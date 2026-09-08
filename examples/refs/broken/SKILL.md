---
name: report-packer
description: >-
  Packs a directory of report fragments into a single archive. Primary trigger
  is any message beginning with "pack:" — treat this prefix as a command.
  Without this skill the base model hand-rolls a zip call each time and
  silently drops the manifest, producing an archive that looks right and
  cannot be unpacked.
---

# report-packer

## Trigger

Any message beginning with `pack:` fires this skill.

## How to run it

Build the archive with the bundled packer, then verify it:

```
python3 scripts/pack_fragments.py fragments/
python3 verify.py out.zip
```

The packer reads `word/document.xml` out of each fragment and writes
`../out.zip` beside the working directory. Both of those are paths in the
user's workspace, not files this skill ships — a reference check must leave
them alone.

## Hard-fails (enforced by verify.py)

- **No archive the verifier did not accept.** The response is written around
  `verify.py`'s exit code (`0` ok / `1` corrupt). If it did not run, refuse
  to report success.

Every hard-fail above is backed by that exit code, not by this sentence.

## Scope — and where it refuses

If the path holds no fragments, refuse and say so rather than emitting an
empty archive.

## Worked example (a catch, not a happy path)

A run over 40 fragments emits an archive in 2s. The verifier exits `1`: two
fragments shared a manifest key and the second silently overwrote the first.
The skill reports the collision and names both fragments, instead of the
"packed 40 fragments" line a bare model would have written.
