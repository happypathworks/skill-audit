---
name: release-notes
description: >-
  EXAMPLE FIXTURE — a deliberately flawed skill, used as the "before" half of
  the skill-audit worked example. It is not a working skill and is not meant to
  be installed. Helps write release notes. Use for release notes, changelogs,
  version notes, shipping updates, patch notes, and release announcements.
---

# Release Notes

This skill writes release notes from a changelog.

## When to use it

Use it whenever you need release notes. It is good for changelogs and
release announcements too.

## Rules

- Never invent a version number.
- Never mention an unreleased feature.
- Keep the summary under 200 characters.

## Style

Match the tone used in the last few releases.

## Example

Input: a changelog with three entries.

Output:

    ## v2.1.0

    Added dark mode. Fixed a crash on export. Updated dependencies.
