---
name: Bug report
about: The checker did something wrong
title: ''
labels: ''
assignees: ''
---

**What you ran**

```
python3 skill_audit.py <path>
```

**What it printed**

Paste the full output, including the exit code.

**What you expected instead**

One sentence is enough.

**The skill it was pointed at**

If you can share the `SKILL.md`, paste it or link it. If you can't, say which
gate is wrong and roughly what the file looks like at that point — a false
positive on gate 2 and a false positive on gate 5 are different bugs.

**Python version**

`python3 --version` (or `python --version` on Windows).

**Claude Code version, if you ran it as a skill**

`claude --version`. Skip this if you ran the checker directly.

**Operating system and terminal**

Name the OS and the terminal you ran in. Output encoding is a real bug class
here — the report uses `→` and `—`, and a console on a legacy code page has
broken the run before.
