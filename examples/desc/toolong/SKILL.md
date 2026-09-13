---
name: standup-notes
description: >-
  Turns a raw standup recording or a pile of chat fragments into the written
  standup note the team actually reads, with blockers separated from progress
  and every name spelled the way that person spells it. Demonstration input for
  skill_audit's [D] preflight: this description is over the platform's hard
  limit, and that is the only thing wrong with it. Entry is the `standup:`
  prefix, and the skill also fires without it on any of the following: "write
  up the standup", "daily note", "scrum notes", "what did we
  say this morning", "turn this transcript into the standup", "summarise
  yesterday's standup", "standup for Tuesday", a pasted meeting transcript with
  three or more speakers, a voice memo recorded before 10am, a list of bullets
  with names in front of them, or a screenshot of a chat thread that reads like
  a standup. Not for retros, not for sprint planning, not for one-to-ones, not
  for incident write-ups, not for status reports to anyone outside the team, and
  not for anything that needs a decision recorded rather than a state reported.
---

# standup-notes

**Demonstration input, not a working skill.** It exists so the `[D]` preflight
has something to fail on that is not an angle bracket, and it holds no XML-tag
shape anywhere — so a run against it shows the two halves of the preflight are
independent.

The description is past 1024 characters. Nothing refuses it: the platform
ingests the skill, truncates the field, and drops the tail. What goes over the
edge here is the end of the *Not for* sentence — the boundaries the author
wrote, the half of the description that stops the skill firing on a retro or a
sprint plan. The skill still installs. It just fires on the things its author
ruled out, while the file on disk still says it does not, which is why this
costs more debugging time than the outright refusal does.

The fix is to cut it to length by hand, so that the author chooses what goes.
