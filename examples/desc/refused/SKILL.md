---
name: link-auditor
description: >-
  Checks every link in a markdown file and reports the dead ones with the line
  each sits on. Entry is the `links:` prefix and nothing else: "links: <path>"
  checks one file, "links:" alone checks the working directory. Not for
  rewriting links, and not for anything that is not markdown. Demonstration
  input for skill_audit's [D] preflight — the angle-bracket placeholder above
  is the only thing wrong with this file.
---

# link-auditor

**Demonstration input, not a working skill.** It exists so the `[D]` preflight
has something to fail on. What the seven gates below say about it is beside the
point — the `[D]` row is what this fixture is for, and it is the row that makes
the verdict `FAIL`.

The description says `links: <path>`. claude.ai refuses that upload outright:
*"SKILL.md description cannot contain XML tags"*. The span is a placeholder,
not markup, and the platform does not care. Claude Code installs the same file
without complaint, so nothing local ever raises it — the skill works for its
author, is audited clean, and is turned down the first time a stranger tries to
install it on the web app.

The fix is one character class: write `links: PATH`. Nothing else about the file
has to change, which is the part worth noticing — this is not a quality problem
wearing a different hat.
