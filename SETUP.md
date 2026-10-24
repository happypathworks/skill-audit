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
                        with the real output of both runs — plus four
                        single-defect fixtures under refs/ and desc/
      tests/            test_fixtures.py — asserts the six fixtures and its
                        own edge cases still return the exit code they
                        are supposed to
      .claude-plugin/   plugin.json, the manifest a marketplace listing reads
      .github/          the repository's CI workflow and issue templates
      .gitignore        the repository's ignore list

Keep `SKILL.md` and `skill_audit.py` together in the same folder. The skill runs
the script from beside itself.

Everything else is documentation, fixtures and repository furniture. The skill
loader reads `SKILL.md`; the rest is inert and can be deleted if you want the
folder bare — `.claude-plugin/` changes how a project install loads, covered
under Compatibility below. The fixtures
under `examples/` are demonstration inputs, not skills — their frontmatter says
so, and they are nested two levels down where the loader does not look.

## Install

Claude Code reads skills from a folder on your machine. The claude.ai web app,
Cowork and the desktop app's chat read them from your claude.ai account. The
second route is under "Without a terminal" below.

The download is two files, one per route:

- `skill-audit.zip` — this whole folder: the skill, the worked example, the
  tests and the plugin manifest. For Claude Code.
- `skill-audit-upload.zip` — `SKILL.md`, `skill_audit.py`, `SETUP.md`,
  `README.md`, `LICENSE` and `CHANGELOG.md`, and nothing else. For your
  claude.ai account, which refuses a zip that holds a plugin manifest or more
  than one `SKILL.md`; the full zip has both.

### Claude Code

Drop the whole `skill-audit` folder into your skills directory, each skill in
its own folder:

- Claude Code (personal): `~/.claude/skills/skill-audit/`
- Claude Code (one project): `<project>/.claude/skills/skill-audit/`

No dependencies to install. If you have Python 3.8 or newer, you can run this.

**What the install writes: that one folder, and nothing outside it.** No global
package, no shell profile, no change to your `CLAUDE.md` or settings, nothing
fetched from anywhere else, no sign-in. Uninstalling is deleting the folder.
Running the checker writes nothing at all — it reads the skill you point it at
and prints to the terminal.

Installed with `git clone` (see `README.md`), the repository root *is* this
folder, so everything listed above — `.github/` and `tests/` included — lands in
your skills directory. Only `.claude-plugin/` changes how it loads (see
Compatibility); delete what you do not want.

### Without a terminal: claude.ai, Cowork, the desktop app

Nothing to unpack. A step marked **Not verified when 2.0.0 was written** had not
been walked through with this skill on that surface when this release was cut.

**The claude.ai web app.**

1. Open `claude.ai/customize/skills/new/upload`, choose `skill-audit-upload.zip`
   as the **Skill file**, the download as it came, and select **Upload**. A
   skill is switched on as soon as it is uploaded. Choose `skill-audit.zip`
   instead and the upload is refused: "A skill cannot contain a plugin
   manifest" and "Zip must contain exactly one SKILL.md file".
2. Your skills are listed at `claude.ai/customize/skills/yours`, and each one's
   page has its on/off switch.
3. In a new chat, attach the `SKILL.md` you want graded and start the message
   with `audit:`, for example `audit: the SKILL.md I attached`. Claude runs
   `skill_audit.py` in the chat for you.

**Not verified when 2.0.0 was written:** what happens when your account already
has a skill named skill-audit; whether a code-execution setting has to be
switched on before Claude can run the checker, and what that setting is
called; and how Claude finds a file attached to the message.

**Cowork.** Skills on your claude.ai account reach Cowork, so the upload above
is expected to be the whole install. **Not verified when 2.0.0 was written.**

**The desktop app.** Its chat uses the skills on your claude.ai account, so the
upload above is expected to be the install there. Its Code tab runs Claude
Code, so the Claude Code steps above are expected to apply as written. **Not
verified when 2.0.0 was written,** either route.

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
version to fix, and updating Claude Code is the whole fix. **No such listing
exists yet** — nothing has been submitted, so the folder install above is the
only route today. The paragraph is here to state the floor that will apply if
and when one lands, not to describe a door you can currently walk through.

**Python 3.8 or later, standard library only.** Six imports: `argparse`, `json`,
`os`, `re`, `sys`, and `date` from `datetime`. The floor is checked rather than
asserted — `.github/workflows/acceptance.yml` runs the fixture tests and the
self-audit on 3.8 and 3.12 on every push, so a change that quietly needs a newer
interpreter fails CI. The grammar parses as far back as 3.6; 3.8 is the floor
because that is the oldest version actually exercised. An interpreter below
the floor is refused by name, with exit 4 and no verdict.

On most Linux and macOS systems the interpreter is `python3`; on Windows a bare
`python` is the usual spelling and `python3` may not exist. The skill's command
line uses `python3` and says to substitute `python` when that is missing.

**Windows consoles that are not UTF-8.** The report prints an em dash (`—`) in its
header line, and `—` does not exist in the legacy `cp437` and `cp850` code pages.
The checker reconfigures its own output stream with `errors="replace"` rather
than assuming a modern terminal: those characters degrade to replacement marks
and the run completes with the right exit code. The CI leg
`windows-legacy-console` forces `PYTHONIOENCODING=cp1252` on `windows-latest`
and fails the build on a traceback or a missing verdict. cp1252 does have the
em dash, so that leg guards the characters it lacks, such as `→`; cp437 and
cp850 are not run in CI.

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
no build step. Nothing here needs a package manager or a repository, only
Python 3 to run the checker.

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
- Add `--json` for machine-readable output, `--quiet` to drop the per-gate fix
  lines, `--log-row` for a one-line row you can paste into build notes.

Or run the checker directly, without the skill:

    python3 skill_audit.py path/to/some-skill

## Reading the result

Every gate returns one of four signals, and the run exits with a code built from
the ones it decided:

- `PASS` — the structural signal is present and positive.
- `REVIEW` — the element is there but a machine can't judge its quality. Needs
  your eyes. A description-based trigger and a happy-path example land here, not
  on `FAIL` — they are the norm, and a regex can't settle them.
- `FAIL` — a high-precision anti-pattern: an explicitly-declared hard-fail with
  no check, a countable constraint with no verification, a soft-only scope exit,
  or phrasing that leans on a conversation the file does not contain.
- `NOT CHECKABLE` — the lint declined to decide. Either the skill had no premise
  for the gate to test (no countable constraint, no bundled paths), or the
  detector's vocabulary is narrow enough that a boundary phrased unusually and
  no boundary at all look the same. These rows do not count against the verdict.

    exit 0  PASS     every decided gate came back clean, and none needs a ruling
    exit 2  REVIEW   no failures, but a gate needs a human ruling or a deeper pass
    exit 1  FAIL     at least one gate failed — fix the -> items and re-run
    exit 3  REFUSED  an input it will not grade: nothing gradable at a path, or
                     a SKILL.md it cannot read as written (a byte-order mark,
                     UTF-16, not UTF-8, empty, frontmatter missing or never
                     closed). The reason and its fix print on stderr
    exit 4  USAGE    the command line was wrong (an unknown flag, or no
                     path), or Python is older than 3.8

`3` and `4` are never verdicts. Across several skills, any FAIL exits `1`, then
any refused input `3`, then any REVIEW `2`. `exit 1` is the code worth scripting against. `exit 0` does not mean the skill is
proven — it means the lint has no objections left, with however many gates it
never decided printed right beside the verdict.

Under every verdict there is one more line, and it is not a gate: *Not graded:
whether the skill works in a fresh session.* Reading a file cannot establish
that — it takes running the skill somewhere its author's context does not
reach — so the tool says so, and prints the step to take, naming the skill's
own trigger when it found one. The count next to `VERDICT:` and the line under
it are the parts to read before you close the question.

## What it does not do

It does not rewrite your skill — it diagnoses and points; fixing is a separate
pass. It grades Claude Agent Skills (a `SKILL.md`, optionally with sibling
scripts), not loose prompts or code repositories. Pointed at something that
isn't a skill, it says so and stops rather than inventing a critique.

It grades the skill, not its installer. What a setup script writes outside the
skill folder, what it downloads, and what an uninstall leaves behind are out of
scope: the checker opens one file, `SKILL.md`, and looks for every other file
by name only. A skill can pass every gate and still come with an install that
writes far outside its own folder. Read that install before you run it.
