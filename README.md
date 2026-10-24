# skill-audit

Points at a Claude skill and grades it against a seven-gate quality floor —
published in full further down this page. Reports gate by gate, with one
concrete fix per miss, and exits with a code you can script against.

Free, MIT, no dependencies. If you have Python 3.8 or newer, you can run this.

## The gap it closes

Ask a model "is this skill any good?" and it will critique the prose, often
well, and differently every time. What it misses is the rule nothing enforces:
it asks what a length limit means, never whether any step counts it. The read
that a review from memory skips is the mechanical one: whether the trigger is
a real prefix or a pile of synonyms, whether each hard-fail has a check behind
it or is just a sentence, whether the one example shows a catch or the happy
path.

This runs that read every time, the same way, and reports what it actually found.

## It grades itself

```
skill_audit — skill-audit
           SKILL.md
           scripts: skill_audit.py

  [D] Upload-safe description    PASS          description is 781 of 1024 chars and holds no XML-tag shape.
  [R] References resolve         PASS          All 1 bundled path(s) resolve. (1 workspace path(s) skipped — not this skill's to resolve)
  [1] Names the gap              PASS          A gap/failure-mode statement is present.
  [2] Deterministic entry        PASS          A deterministic entry (prefix or unambiguous condition) is present (`audit:`).
  [3] Enforced hard-fails        PASS          Hard-fails are present and the skill ships a script (skill_audit.py).
  [4] Verify before voice        NOT CHECKABLE No countable/spec'd constraint detected; gate not applicable.
        -> If the skill does have a hard constraint (a count, a spec), make sure it's verified, not asserted.
  [5] Loud failure, named exit   PASS          Scope boundaries name an explicit exit (if X, refuse and do Y).
  [6] No prior-chat references   PASS          No phrasing that leans on an earlier chat ("as we discussed", "like last time").
  [7] Deciding example           PASS          A worked example is present and shows a catch, not just the happy path.

FAIL 0   REVIEW 0   NOT CHECKABLE 1   PASS 8

VERDICT: PASS
Every gate the lint can decide came back clean. One gate it cannot decide is marked NOT CHECKABLE above — read its -> line.
Not graded: whether the skill works in a fresh session. The lint reads files; only a run shows what a model does with them.
        -> Open a session where your own project instructions do not load, install the skill from its archive, give it a real task that starts with `audit:`, and check what it does against what the skill promises.
```

Read the third column before the verdict. A gate comes back `PASS`, `REVIEW`,
`FAIL` — or `NOT CHECKABLE`, which is the tool declining to hold an opinion
when a skill gives a gate nothing it can test. Those rows do not count against
the verdict, and their count is printed beside it.

Then read the line under the verdict, because it is the one no gate covers.
Whether a skill works in a fresh session — somewhere its author's context does
not reach — takes running it, and a lint only reads files. So the report says
so under every verdict, with the step to take, instead of printing a green row
it did not earn. `PASS` means *nothing found and nothing owed*, not *the skill
works*: eight clean rows here, one row it cannot decide, and a run still to do.

## The preflights

Before the gates, two integrity checks. Neither is about quality. Each catches
something that stops a skill being a skill, which no gate below can see.

### `[D] Upload-safe description`

The description is the one field the platform reads before it reads anything
else, and two limits on it break silently.

**Past 1024 characters it is truncated on ingest.** The tail is dropped, nothing
warns, and if the trigger sentence or the boundaries lived in the tail, the skill
quietly fires on things its author ruled out — while the file on disk still says
it does not.

**Anything shaped like an XML tag is refused outright.** claude.ai answers the
upload with *"SKILL.md description cannot contain XML tags"* and installs
nothing. The cause is almost always a placeholder rather than markup: `recheck
<path>`. Claude Code accepts the same file, so the skill can be written,
installed, audited clean and used locally for weeks before the web app turns it
down — and the refusal names the field, not the span. The server-side rule is
unpublished, so this matches any `<...>` span.

Both are `FAIL` rather than `REVIEW`, for the same reason: a skill the platform
will not take as written is not a skill with a design problem. It is a skill
that does not arrive. The fix is in the frontmatter and nowhere else.

### `[R] References resolve`

Verifies that
every path the skill *claims to ship* actually exists — a renamed helper, a
deleted script, a `references/` file that moved. Gate 3 cannot see this: once
a script ships, it counts the skill "enforced", and a stale reference to some
other file does not change that.

It is deliberately narrow. A path counts only where the skill's own layout
vouches for it — its first segment is a directory the skill ships, or it is a
bare script the skill tells you to **run** in a skill that ships scripts.
Everything else a SKILL.md mentions (`word/document.xml` inside a document
being unpacked, `.claude/settings.json` in the user's repo, an output path, a
script the model is told to write) is a workspace path: it cannot resolve here,
so it is counted as skipped and never flagged. A path on a line that announces
itself as illustrative (`**Examples**: references/finance.md for financial
schemas`) is skipped too — that names a file *you* might write.

**A missing path is only a `FAIL` when the skill points at it** — links it,
runs it, or introduces it with a pointer verb (`see`, `load`, `defined in`).
Named once in passing and absent, it comes back `REVIEW` instead. The reason is
specific: a skill documenting skill layout writes `references/patterns.md` as
advice in the same form it writes a file it really ships, so the two are
indistinguishable on the page and calling one broken would be inventing
evidence.

Measured against a known-good corpus of 32 skills — every skill in Anthropic's
official plugin marketplace, plus this one — this preflight returns zero
`FAIL`s. The lint as a whole returns one, and it is not a reference problem: a
template skill in the marketplace carries `<name>` in its description, which
`[D]` catches because claude.ai refuses that description at upload. Measured
2026-09-19; the marketplace changes on Anthropic's release schedule, so the
figure is dated rather than maintained.

Pass `--no-refs` to skip it.

## The seven gates

| | Gate | A failure looks like |
|---|---|---|
| 1 | Names the gap | The skill never says what goes wrong without it. It reads as a nice-to-have because nothing establishes the need. |
| 2 | Deterministic entry | Entry is undecided: a pile of synonyms, or a description that says what the skill is for and never what it is not for. It fires when it shouldn't and stays quiet when it should. A prefix decides entry; so does a description bounded on both sides — this gate asks whether entry is *decided*, not whether it is prefixed. A prefix counts where the model choosing a skill reads it, in the description (backticked or quoted); declared only in the body, it is REVIEW. |
| 3 | Enforced hard-fails | Rules stated as prose with nothing checking them. A rule with no check behind it is a preference. |
| 4 | Verify before voice | A countable constraint — a character, word or line limit, a range, a spec, in digits or in words — that nothing counts. The output is written around an estimate. |
| 5 | Loud failure, named exit | Scope language with a soft exit. "Try to stay in scope" instead of "if X, refuse and do Y". |
| 6 | No prior-chat references | The skill leans on a conversation it does not contain — "as we discussed", "like last time". A fresh session never had that conversation, so it quietly does something else. |
| 7 | Deciding example | The only example is the happy path, so it demonstrates nothing that could have gone wrong. The catch has to sit in the example's own section; an aside ("for example", "e.g.") is not a worked example. |

Gate 6 is the part of a bigger question that a file can show. The bigger
question — does the skill work in a fresh session at all? — is not a gate,
because answering it means running the skill, and the report says so under
every verdict. The worked example in `examples/` carries a line that shows why:
"Match the tone used in the last few releases" leans on context the file does
not carry, in words no phrase list would catch. A run catches it.

### What each gate reads

The gates read phrasing, not intent. Each one decides on the short list of
phrasings below and nothing else: a rule written in other words goes unseen,
and a weaker match comes back REVIEW, never FAIL. Matching ignores case, and a
phrase shown in quotes, italics or code in the skill is a mention, not a use.

1. **Names the gap.** PASS on a sentence holding "without this skill", "without
   the skill", "the base model", "left alone", "the gap", "the failure mode",
   "doesn't survive", "gets it wrong", "inconsistently", or "otherwise" followed
   in the same sentence by wrong, fails, breaks, drift or miss. Otherwise REVIEW.
   It never FAILs, and it does not judge whether the gap is real.
2. **Deterministic entry.** Read in the description only. PASS on a backticked
   or quoted token ending in `:` or `/` with "trigger", "prefix", "fires on",
   "invoked with", "treat ... as a command", or a message that "begins with" it,
   within 60 characters; on "any message beginning with", "primary trigger is",
   "hard trigger" or "when the user types"; or on a "Use when", "Use for" or
   "when the user" line together with "do not use this", "not for", "when not
   to", "skip this" or "instead ... use". The same declaration in the body only is REVIEW, and so is
   anything else. It never FAILs.
3. **Enforced hard-fails.** FAIL on "hard-fail" or "hard stop", with any hyphen
   or none, when no script ships anywhere in the skill (`.py`, `.sh`, `.js`,
   `.mjs`, `.cjs`, `.ts`, `.rb`, `.pl`, `.ps1`, `.bat`) and no check is described
   in words ("exit code", "non-zero", "the check returns", "run the check"), or
   when the only check named is a script missing from the skill. "There are no
   hard-fails" declares none. Rule-like wording without the token ("you must",
   "never ...") is REVIEW.
4. **Verify before voice.** FAIL on a limit written as a limiting word (under,
   over, at most, up to, within, no more than, no longer than, fewer than, ≤,
   between ... and ..., keep ... to) with a number in digits or words and a unit
   (characters, words, lines, sentences, bullets, pages, paragraphs, items,
   rows), in a clause that directs the output (keep, limit, must, should,
   never, always, do not, "is wrong", a soft or hard budget; a clause after
   ", so" or ", but" directs only itself), when nothing in the skill verifies
   it (verify, confirm, re-run, count the, `wc`, "until it reports", "before
   replying", or, in the limit's own section, a check that "exits 1 when" over
   it). A verifying step in another section is REVIEW.
   A number stated as a fact ("messages over 160 characters are split") is not
   a rule on the output: NOT CHECKABLE.
5. **Loud failure, named exit.** FAIL on "try to stay on" (or in, within),
   "steer ... back", "avoid drifting", "stay on topic", "be careful", "where
   possible" or "try not to", in a section about scope (an "Out of scope" line,
   "not for", "do not use for", a hard-fail) that names no exit. A named exit is
   "if ..., refuse" (or stop, decline, hand off, say so), "refuse and ...", or
   "say ..., name the other skill, and stop"; a negated one ("don't stop them")
   is none. "Avoid", "should not" or "try to" beside a boundary is REVIEW.
6. **No prior-chat references.** FAIL on "as discussed", "as we discussed",
   "per our", "like last time", "as last time", "like before", "our last
   conversation" (or previous, chat, session, thread), "earlier in this chat",
   "as established above", or "you already know ... from our chat". Not when the
   phrase points into the file ("as discussed in Step 2", "per our convention in
   the Naming section below") or at a file the skill ships. Anything else PASSes.
7. **Deciding example.** Reads an example set out under its own heading, as an
   Input:/Output: pair, or under a bold Example label. PASS when that section
   says "catch", "would otherwise", "gets it wrong", "instead of" followed by an
   -ing word, "would have", "silently", "base model", "mistake", "trap", "fails"
   or "naive"; otherwise REVIEW. Examples given only inline ("for example",
   "e.g.") are NOT CHECKABLE.

## Install

Drop the folder into your skills directory:

    git clone https://github.com/happypathworks/skill-audit.git \
      ~/.claude/skills/skill-audit

Or, for one project:

    git clone https://github.com/happypathworks/skill-audit.git \
      <project>/.claude/skills/skill-audit

No `git`? Download the repository as a ZIP and unpack it to the same place — the
folder only has to be named `skill-audit` and sit directly inside a skills
directory.

Nothing to install after that. Python 3.8+, standard library only.

## Compatibility

Runs wherever Claude runs — Claude Code, the claude.ai web app, Cowork, and the
desktop app. This is a standard Agent Skill: a `SKILL.md` and the one Python file it
runs, nothing to build and nothing to fetch. There is no minimum Claude Code version
either; the skill uses no version-gated feature.

Where you install it differs by surface, and the two locations do not sync. A
folder under `~/.claude/skills/` or `.claude/skills/` is local to Claude Code on
that machine; skills added to your claude.ai account are the ones available in
the web app, Cowork, cloud sessions and routines. Installing one does not install
the other. That is about where the files live, not about where the skill can run.

Python 3.8 or later, standard library only. That floor is checked, not claimed —
CI runs the fixtures and the self-audit on 3.8 and 3.12 on every push, plus a
Windows leg that forces a legacy `cp1252` console so the report is known to
render there.

`SETUP.md` has the full statement, including what each install route requires.

## Use

    audit: path/to/some-skill

- `audit: <path>` — grade one skill (a folder with a `SKILL.md`, or a `SKILL.md`).
- `audit: <folder>` — grade every skill in a folder of skills.
- `--json` for machine-readable output, `--quiet` to drop the per-gate fix
  lines, `--log-row` for a one-line row you can paste into build notes.

Or run the checker directly, without the skill:

    python3 skill_audit.py path/to/some-skill

## Exit codes

    exit 0   PASS     every gate the lint can decide came back clean, and
                     none needs a human ruling. Undecided gates are listed
                     as NOT CHECKABLE and do not block this
    exit 2   REVIEW   no failures, but a gate needs a human ruling
    exit 1   FAIL     a gate failed, or a file the skill points at is missing — fix the
                     -> items and re-run
    exit 3   REFUSED  an input the lint will not grade: nothing gradable at a
                     path, or a SKILL.md it cannot read as written (a
                     byte-order mark, UTF-16, bytes that are not UTF-8, an
                     empty file, frontmatter missing or never closed). The
                     reason and its fix print on stderr
    exit 4   USAGE    the command line was wrong (an unknown flag, or no
                     path), or Python is older than 3.8

Script against `1` — that is the one that means something went wrong. `0` means
the lint is out of objections, which is not the same as the skill being proven:
read the `NOT CHECKABLE` rows, and the *Not graded* line under the verdict,
before you close the question.

`3` and `4` are never verdicts. Across several skills, any FAIL exits `1`;
otherwise any refused input exits `3`, then any REVIEW `2`, else `0`. So a `0`
or a `2` never stands for an input the lint did not grade, and `1` still
catches every FAIL. `--help` exits `0`.

## Calling it from a script

- stdout carries the reports of the skills it graded, and nothing else.
  Refusals and usage errors go to stderr.
- With `--json`, stdout is one JSON object for one graded skill, a list of
  them for several, and empty when nothing was graded. Each object has the keys
  `name`, `path`, `verdict` (`PASS`, `REVIEW` or `FAIL`), `scripts`,
  `broken_refs`, `gates` and `not_graded`. Each entry in `gates` has `gate`,
  `title`, `status`, `message` and `fix`; `status` is `PASS`, `REVIEW`, `FAIL`
  or `NOT CHECKABLE`.
- A refusal prints as `skill_audit: REFUSED PATH: REASON.` with a `->` fix line
  under it.

## Worked example

`examples/` holds the same skill twice — once before anyone checked it, once
after each gate was answered — with the real output of both runs and a
gate-by-gate account of what changed and why. Start there.

    python3 skill_audit.py examples/before/release-notes   # exit 1, FAIL
    python3 skill_audit.py examples/after/release-notes    # exit 0, PASS
    python3 skill_audit.py examples/refs/broken            # exit 1, missing file
    python3 skill_audit.py examples/refs/intact            # exit 0, refs resolve
    python3 skill_audit.py examples/desc/refused           # exit 1, <path> refused
    python3 skill_audit.py examples/desc/toolong           # exit 1, over 1024 chars

## Tests

    python3 tests/test_fixtures.py

Asserts the six fixtures, and the edge cases written into the test, still return the exit code — and the preflight rows —
they are supposed to, and that unreadable input is refused with `3` and usage
errors exit `4`. The clean ones are the assertions that matter: a lint that
fails good input loses a stranger's trust on first contact, and there is no
second contact.

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

It is a lint. It catches the structural tells a machine can catch, and it says
plainly where a human still has to look.

## License

MIT. See `LICENSE`. Use it, fork it, strip the parts you don't want.

## Who makes this

Happy Path Works builds Claude skills as systems: explicit triggers, enforced
hard-fails, stated scope boundaries, a worked example per skill.

Changes to this tool, and the next ones as they ship, go out on the list:
[happypathworks.beehiiv.com](https://happypathworks.beehiiv.com/subscribe?utm_source=skill-audit).
No cadence promised beyond that — it is a changelog you do not have to poll.

Questions and bug reports: hello@happypath.works

## Independence and AI assistance

Happy Path Works is an independent project. It is **not affiliated with,
endorsed by, or sponsored by Anthropic**. Claude, Claude Code and Anthropic are
trademarks of Anthropic PBC, used here only to describe what this tool works
with. This tool requires your own Claude access; it resells nothing.

This tool and its documentation are developed with AI assistance, and a human
reviews everything before it ships. That is the same standard the seven gates
enforce — a claim gets verified before it gets written down — and it applies to
the people writing them too.
