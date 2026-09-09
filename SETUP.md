# skill-audit — setup

A free skill that grades a Claude skill against a seven-gate quality Floor and
tells you, gate by gate, where it is a product and where it is still a prompt.
It is a lint: it catches the structural tells a machine can catch and says
plainly where a human still has to look.

## What's in the folder

    skill-audit/
      SKILL.md          the skill itself
      skill_audit.py    the checker it runs (Python 3.8+, standard library only)
      SETUP.md          this file
      README.md         what this is, for someone who found the repo first
      LICENSE           MIT
      CHANGELOG.md      dated, versioned releases
      examples/         the worked example — the same skill before and after,
                        with the real output of both runs
      tests/            test_fixtures.py — asserts both fixtures still return
                        the exit code they are supposed to

Keep `SKILL.md` and `skill_audit.py` together in the same folder. The skill runs
the script from beside itself.

Everything else is documentation and fixtures. The skill loader reads `SKILL.md`;
the rest is inert and can be deleted if you want the folder bare. The fixtures
under `examples/` are demonstration inputs, not skills — their frontmatter says
so, and they are nested two levels down where the loader does not look.

## Install

Drop the whole `skill-audit` folder into your skills directory, each skill in
its own folder:

- Claude Code (personal): `~/.claude/skills/skill-audit/`
- Claude Code (one project): `<project>/.claude/skills/skill-audit/`

No dependencies to install. If you can run `python3 --version`, you can run this.

## Compatibility

Checked against the Claude Code documentation on 2026-09-06 and verified running
on Claude Code v2.1.239, Python 3.14.7, Windows 11. Version floors below are what
each route actually requires, not a guess from a release number.

**As a skill — no Claude Code version floor.** `SKILL.md` declares `name` and
`description` and nothing else, and the body uses no version-gated feature: no
`${CLAUDE_PROJECT_DIR}` substitution (which needs v2.1.196 or later), no
`background:` frontmatter and no `yes`/`no` boolean spellings (both v2.1.218 or
later), no `!` commands and no `@` file references. Any Claude Code that reads
`~/.claude/skills/<name>/SKILL.md` runs this one.

**From the community marketplace — no floor beyond a working `/plugin`.** The
listing is a GitHub-sourced marketplace entry pinned to a commit, not an
`archive` source, so the v2.1.224 floor that applies to archive-type sources does
not apply here. If `/plugin` is not recognised in your session, that is the
version to fix, and updating Claude Code is the whole fix. The listing is pending
review; until it lands, use the folder install above.

**Python 3.8 or later, standard library only.** Six imports: `argparse`, `json`,
`os`, `re`, `sys`, and `date` from `datetime`. The floor is checked rather than
asserted — `.github/workflows/acceptance.yml` runs the fixture tests and the
self-audit on 3.8 and 3.12 on every push, so a change that quietly needs a newer
interpreter fails CI. The grammar parses as far back as 3.6; 3.8 is the floor
because that is the oldest version actually exercised. There is no runtime
version guard, so an interpreter below the floor fails at whatever it fails at
rather than saying so.

On most Linux and macOS systems the interpreter is `python3`; on Windows a bare
`python` is the usual spelling and `python3` may not exist. The skill's command
line uses `python3` and says to substitute `python` when that is missing.

**Windows consoles that are not UTF-8.** The report prints an em dash (`—`) in its
header line, and `—` does not exist in the legacy `cp1252` code page. A literal `→`
in a print path once killed the run before any verdict was emitted, with no symptom
on Linux at all; that arrow is gone — the fix line now reads `->` — but the em dash
remains and the same failure class applies to it.
The checker now reconfigures its own output stream with `errors="replace"` rather
than assuming a modern terminal: those characters degrade to replacement marks
and the run completes with the right exit code. This is a standing CI leg, not a
one-off check — `windows-legacy-console` forces `PYTHONIOENCODING=cp1252` on
`windows-latest` and fails the build if a traceback appears or no verdict is
printed.

**The bundled plugin manifest changes project-scope installs.** The repository
ships `.claude-plugin/plugin.json` so the same tree can be listed in the
community marketplace. A side effect: any folder under a skills directory that
contains that manifest loads as a plugin (`skill-audit@skills-dir`) rather than
as a plain skill. Personal installs under `~/.claude/skills/` load it that way
too, but carry none of the extra constraints below. Project installs under `<project>/.claude/skills/` gain two constraints — the
workspace trust dialog has to be accepted before it loads, and it is found only
from the session's primary working directory, where a plain skill would be found
by walking up from a subdirectory. Launch from the repository root. If you want
the plain-skill behaviour instead, delete `.claude-plugin/` from your copy; the
checker and the skill do not read it.

**Every Claude surface.** Agent Skills run on Claude Code, in the claude.ai web
app, in Cowork and in the desktop app, and this one is deliberately plain enough
to run on all of them: a `SKILL.md`, one Python file, the standard library, and
no build step. Nothing here needs a shell, a package manager or a repository.

**Install location differs by surface, and the two do not sync.** A folder you
drop into `~/.claude/skills/` or `.claude/skills/` is local to Claude Code on
that machine. Skills added to your claude.ai account are the ones that reach the
web app, Cowork sessions, cloud sessions and routines. Installing one place does
not install the other, so put it wherever you actually work — or both. This is a
fact about where files live, not a limit on where the skill runs.

## Use

Point it at a skill:

    audit: path/to/some-skill

- `audit: <path>` grades one skill — a folder with a `SKILL.md`, or a `SKILL.md`
  file directly.
- `audit: <folder>` grades every skill in a folder of skills.
- Add `--json` for machine-readable output, `--log-row` for a build-notes row.

Or run the checker directly, without the skill:

    python3 skill_audit.py path/to/some-skill

## Reading the result

Every gate returns one of three signals, and the run exits with a matching code:

- `PASS` — the structural signal is present and positive.
- `REVIEW` — the element is there but a machine can't judge its quality, or the
  gate needs a cold run to settle. Needs your eyes. A description-based trigger
  and an undetected example land here, not on `FAIL` — they are the norm, and a
  regex can't settle them.
- `FAIL` — a high-precision anti-pattern: an explicitly-declared hard-fail with
  no check, a countable constraint with no verification, a soft-only scope exit,
  or context the file does not contain.

    exit 0  PASS     every gate passed
    exit 2  REVIEW   no failures, but a gate needs a human ruling or a deeper pass
    exit 1  FAIL     at least one gate failed — fix the -> items and re-run
    exit 3  ERROR    nothing gradable at that path

A clean run tops out at `REVIEW`, not a green `PASS` — because one gate (does the
skill survive a cold run?) cannot be settled without actually running the skill
in a fresh context. That is honest, not a defect. A `REVIEW` with no `FAIL`s is
the normal, good result.

## What it does not do

It does not rewrite your skill — it diagnoses and points; fixing is a separate
pass. It grades Claude Agent Skills (a `SKILL.md`, optionally with sibling
scripts), not loose prompts or code repositories. Pointed at something that
isn't a skill, it says so and stops rather than inventing a critique.
