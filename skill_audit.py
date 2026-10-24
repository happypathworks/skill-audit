#!/usr/bin/env python3
"""
skill_audit.py — mechanical lint of a Claude skill against the seven-gate Floor.

This is the lint, not the verdict. It is decisive only where a machine can be
precise: it FAILs on an explicitly-declared hard-fail with no check behind it,
a countable constraint asserted without verification, a scope boundary that
says "try to stay in scope" instead of naming an exit, and phrasing that leans
on a conversation the file does not contain. Everything softer — whether the
trigger is a prefix or a description, whether an example is present and
genuinely *deciding*, whether the one-sentence gap is *true* — comes back
REVIEW for a human, because presence is not quality and a regex cannot settle
it. This tool reports what it can see honestly and never pretends to judge
more than it can.

A gate can also come back NOT CHECKABLE, which is the lint declining to hold
an opinion — the skill had no premise for the gate to test (no countable
constraint, no bundled paths), or the detector's vocabulary is narrow enough
that absence and unfamiliar phrasing look identical (scope boundary, worked
example). Those rows carry a -> line naming what a human would have to do, and
they do not count against the verdict. A verdict built on rows the tool never
decided is the thing this state exists to stop.

NOT GRADED
    One question sits outside every gate: does the skill work in a fresh
    session? Answering it means running the skill where its author's context
    does not reach, and a lint only reads files. Named for that question,
    Gate 6 could FAIL on the one tell a file shows --
    phrasing that leans on an earlier chat -- and never PASS: a row that could
    fail and never pass, which is a to-do wearing a gate's badge. Gate 6 now
    grades what it reads, and can PASS. The fresh-session question is printed
    under every verdict as "Not graded", with the steps to run it.

USAGE
    python skill_audit.py <path> [<path> ...] [options]

    <path>          a skill directory (containing SKILL.md), a SKILL.md file,
                    or a folder of skills (each in its own subdirectory).

    --json          machine-readable output
    --no-refs       skip the reference-resolution preflight
    --quiet         suppress per-gate evidence, print the gate line + verdict
    --log-row       emit a markdown row for a build-notes gate log

EXIT CODES
    0   PASS    every gate the lint can decide came back clean, and none needs
                a human ruling. Gates 4, 5, 7 and both preflights can each land
                on a premise they cannot test — those rows report NOT CHECKABLE
                and are excluded from the verdict — and whether the skill works
                in a fresh session is not graded at all. So 0 means "nothing
                found and nothing owed", not "everything proven". Read the NOT
                CHECKABLE rows and the Not graded line before treating a 0 as
                the end of the question.
    2   REVIEW  no failures, but at least one gate needs a human ruling or a
                deeper pass. This is the normal result for a decent skill.
    1   FAIL    at least one gate failed on a high-precision anti-pattern: an
                explicitly-declared hard-fail with no backing check, a countable
                constraint with no verification, a scope boundary whose exit is
                an intention rather than an action, or context the file does not
                contain -- or a preflight found a description the platform will
                not take as written, or a file the skill POINTS AT (links, runs,
                or names with a pointer verb) and does not ship. Fix and re-run.
    3   REFUSED an input the lint will not grade: nothing gradable at a path,
                or a SKILL.md it cannot read as written (a byte-order mark,
                UTF-16, bytes that are not UTF-8, an empty file, frontmatter
                missing or never closed). Named on stderr with its fix.
    4   USAGE   the command line itself was wrong.
                So is a Python older than 3.8, which is refused by name.
    3 and 4 are never verdicts: a REVIEW printed for a file the lint could
    not read is a verdict on nothing. Across several inputs, FAIL outranks
    REFUSED, which outranks REVIEW and PASS.

THE [D] PREFLIGHT
    Before the Floor, two integrity checks. This is the first, and it grades
    the one field the platform reads before it reads anything else:
    `description`. Two limits apply to it. Both are silent, and no gate below
    can see either.

    1024 characters is the hard limit. Past it the description is truncated on
    ingest -- the tail is gone and nothing warns. A trigger sentence that lived
    in the lost tail stops firing, which reads as the model being unreliable
    and is not that.

    Anything shaped like an XML tag is refused outright. claude.ai answers the
    upload with "SKILL.md description cannot contain XML tags", and the usual
    cause is a placeholder rather than markup: `recheck <path>`. Claude Code
    accepts the same file, so a skill can be written, installed, audited and
    used locally for weeks before the web app turns it down -- and the refusal,
    when it comes, names the field and not the span. The server-side rule is
    unpublished, so this matches any <...> span.

    Both are FAIL rather than REVIEW, for one reason: a skill the platform will
    not take as written is not a skill with a design problem. It is a skill
    that does not arrive.

THE [R] PREFLIGHT
    The second integrity check: every path the skill claims to ship must exist.
    It runs before the Floor because a skill pointing at a file that is not
    there is broken the way a build break is broken, and no gate below can see
    it -- Gate 3 counts a skill "enforced" if ANY script sits in its directory,
    which a renamed or deleted one still satisfies.

    It grades only paths the skill's own layout vouches for: a path whose first
    segment is a directory the skill ships, or a bare script it tells you to RUN
    in a skill that ships scripts. Everything else in a SKILL.md -- runtime
    paths inside a document being unpacked, files in the user's repo, outputs,
    a script the model is told to write -- is a workspace path, cannot resolve
    here, and is reported as skipped rather than flagged. That line is the whole
    design: the check is narrow so that a FAIL means something.

    One more exemption: a path on a line that announces
    itself as illustrative ("**Examples**: `references/finance.md` for
    financial schemas") is naming a file the READER might write, not one this
    skill ships. Skills about writing skills are full of these, and they land
    under a references/ directory the skill does happen to ship -- the exact
    coincidence the first-segment rule cannot see through. The exemption is
    scoped to the line; a heading two paragraphs up exempts nothing.

WHAT THIS IS NOT
    It does not rewrite your skill. It diagnoses and points; fixing is your
    pass, or the skill-creator's. It grades Claude Agent Skills (a SKILL.md,
    optionally with sibling scripts), not loose prompts or code repositories.
"""

import argparse
import bisect
import codecs
import json
import os
import re
import sys
from datetime import date
from urllib.parse import unquote

# The floor is Python 3.8. An older interpreter is refused here, by name,
# rather than left to die later on a line it cannot run.
if sys.version_info < (3, 8):
    sys.stderr.write("skill_audit: needs Python 3.8 or newer; this is Python %d.%d "
                     "(exit 4, no verdict)\n" % tuple(sys.version_info[:2]))
    sys.exit(4)

# Windows consoles default to a legacy code page (cp1252 on en-US). The
# report, and any evidence quoted out of an audited SKILL.md, can contain
# characters that page cannot encode; unguarded, that raises
# UnicodeEncodeError mid-print and kills the run. Degrade the character
# instead of dying. Guarded because stdout is not always a reconfigurable
# text stream (test harnesses, pipes wrapped by other tools).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError, OSError):  # pragma: no cover
        pass

# ------------------------------------------------------------------ gates ----

GATES = [
    (1, "Names the gap"),
    (2, "Deterministic entry"),
    (3, "Enforced hard-fails"),
    (4, "Verify before voice"),
    (5, "Loud failure, named exit"),
    (6, "No prior-chat references"),
    (7, "Deciding example"),
]

# NOT CHECKABLE is the third per-gate state, and it exists because REVIEW was
# doing three unrelated jobs at once: "I checked and found a problem", "I
# checked and found nothing wrong", and "I could not check". Only the first is
# a finding about the skill. Rows that mean the third now say so and do not
# gate the verdict — a gate the lint cannot decide is not evidence against the
# work, and printing it as REVIEW made every report read the same. It is not a
# softer PASS: it is the lint declining to hold an opinion, and the -> line
# under it names what a human would have to do to settle it.
NOTCHECK = "NOT CHECKABLE"
STATUSES = ("FAIL", "REVIEW", NOTCHECK, "PASS")  # worst-first: badge width and the per-status counts
BADGE_W = max(len(s) for s in STATUSES)

SCRIPT_EXT = {".py", ".sh", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl", ".ps1", ".bat"}

EXIT_PASS, EXIT_FAIL, EXIT_REVIEW, EXIT_REFUSED, EXIT_USAGE = 0, 1, 2, 3, 4


# -------------------------------------------------------------- load skill ---

def find_skill_md(directory):
    for name in os.listdir(directory):
        if name.lower() == "skill.md" and os.path.isfile(os.path.join(directory, name)):
            return os.path.join(directory, name)
    return None


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def parse_frontmatter(text):
    """Return (frontmatter_dict, body). Naive YAML: enough for name/description."""
    if not text.startswith("---"):
        return {}, text
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw, body = m.group(1), m.group(2)
    fm, key, buf = {}, None, []
    for line in raw.splitlines():
        if line.startswith("#"):  # a comment at column 0 belongs to no value
            continue
        # a key may be quoted ("description":) or spaced (description :)
        top = re.match(r"""^(["']?)([A-Za-z0-9_-]+)\1\s*:\s*(.*)$""", line)
        if top and not line.startswith((" ", "\t")):
            if key is not None:
                fm[key] = _scalar(buf)
            key = top.group(2).lower()
            buf = [top.group(3)]
        else:
            buf.append(line)
    if key is not None:
        fm[key] = _scalar(buf)
    return fm, body


def _scalar(lines):
    """One frontmatter value as the platform's YAML parser decodes it."""
    block = re.match(r"^\|([-+]?)\s*$", lines[0].strip())
    if block:
        # A literal block keeps each line's indentation past the block's own,
        # and its newlines; the default chomping keeps one final newline.
        rest = lines[1:]
        ind = min((len(l) - len(l.lstrip()) for l in rest if l.strip()), default=0)
        v = "\n".join(l[ind:] for l in rest).rstrip("\n")
        return v if not v or block.group(1) == "-" else v + "\n"
    v = re.sub(r"^[>|][-+]?\s*", "", " ".join(b.strip() for b in lines).strip()).strip()
    if len(v) > 1 and v[0] == v[-1] == '"':
        # A double-quoted scalar is decoded by the platform: "\u003cpath\u003e"
        # arrives as <path>, so [D] has to read it decoded too.
        return _yaml_unescape(v[1:-1])
    if len(v) > 1 and v[0] == v[-1] == "'":
        return v[1:-1].replace("''", "'")  # '' is one quote in a single-quoted scalar
    return v.strip('"').strip("'")


YAML_ESCAPE = re.compile(r"\\(?:u([0-9A-Fa-f]{4})|U([0-9A-Fa-f]{8})|x([0-9A-Fa-f]{2})|(.))")
YAML_SIMPLE = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "/": "/", " ": " ", "0": "\0"}


def _yaml_unescape(s):
    """YAML double-quoted escapes: \\uXXXX, \\UXXXXXXXX, \\xXX and the common one-letter ones."""
    def one(m):
        code = m.group(1) or m.group(2) or m.group(3)
        return chr(int(code, 16)) if code else YAML_SIMPLE.get(m.group(4), m.group(0))
    return YAML_ESCAPE.sub(one, s)


FRONTMATTER_FIX = ("Open SKILL.md with a frontmatter block: a --- line, name: and "
                   "description: lines, and a closing --- line.")


def refusal(path, reason, fix):
    """A SKILL.md, or a path, the lint will not grade. Exit 3, never a verdict."""
    return {"refused": True, "path": path, "reason": reason, "fix": fix}


def read_skill_md(md):
    """(text, None) for a SKILL.md the lint can grade, else (None, refusal).

    Each refusal below is a file that would otherwise get a verdict. Read
    with errors="replace", a byte-order mark hides the frontmatter and grades
    REVIEW with [D] NOT CHECKABLE; UTF-16 and binary bytes decode to
    replacement characters and grade REVIEW; an empty file, or one with no
    frontmatter, grades REVIEW, "the normal result for a decent skill". A
    verdict on a file the lint could not read says something about nothing.
    """
    with open(md, "rb") as fh:
        raw = fh.read()
    if raw.startswith(codecs.BOM_UTF8):
        return None, refusal(md, "SKILL.md starts with a UTF-8 byte-order mark, so its "
                             "frontmatter does not begin at the first byte",
                             "Save SKILL.md as UTF-8 without a byte-order mark (BOM).")
    if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return None, refusal(md, "SKILL.md is UTF-16 (or UTF-32) text", "Save SKILL.md as UTF-8.")
    if b"\x00" in raw:
        return None, refusal(md, "SKILL.md contains NUL bytes: it is binary, or UTF-16 "
                             "without a byte-order mark", "Save SKILL.md as UTF-8 text.")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        return None, refusal(md, "SKILL.md is not UTF-8 (the first bad byte is at offset %d)"
                             % e.start, "Save SKILL.md as UTF-8.")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        return None, refusal(md, "SKILL.md is empty", FRONTMATTER_FIX + " Then write the body.")
    if not text.startswith("---"):
        return None, refusal(md, "SKILL.md has no frontmatter: its first line is not ---",
                             FRONTMATTER_FIX)
    if not FRONTMATTER_RE.match(text):
        return None, refusal(md, "SKILL.md's frontmatter is never closed, or is empty: no "
                             "--- line follows the name and description", FRONTMATTER_FIX)
    return text, None


def load_skill(path):
    """Return a skill dict, a refusal dict, or None if no SKILL.md is here."""
    if os.path.isdir(path):
        md = find_skill_md(path)
        if not md:
            return None
        skill_dir = path
    elif os.path.isfile(path) and os.path.basename(path).lower() == "skill.md":
        md = path
        skill_dir = os.path.dirname(os.path.abspath(md))
    else:
        return None

    text, refused = read_skill_md(md)
    if refused:
        return refused
    fm, body = parse_frontmatter(text)

    scripts = []
    try:
        for name in os.listdir(skill_dir):
            full = os.path.join(skill_dir, name)
            if os.path.isfile(full) and os.path.splitext(name)[1].lower() in SCRIPT_EXT:
                scripts.append(name)
    except OSError:
        pass

    # Gate 3's checks: a script anywhere in the skill, scripts/check.py as much
    # as a check.py beside SKILL.md.
    checks = []
    for root, dirs, names in os.walk(skill_dir):
        # A folder holding its own SKILL.md is another skill, and its checks are its own.
        dirs[:] = sorted(d for d in dirs if d not in ("node_modules", ".git", "__pycache__")
                         and not os.path.isfile(os.path.join(root, d, "SKILL.md")))
        checks += sorted(os.path.relpath(os.path.join(root, n), skill_dir).replace(os.sep, "/")
                         for n in names if os.path.splitext(n)[1].lower() in SCRIPT_EXT)

    name = fm.get("name") or os.path.basename(skill_dir) or os.path.basename(md)
    return {
        "path": md,
        "dir": skill_dir,
        "name": name,
        "description": fm.get("description", ""),
        "body": body,
        "full": text,
        "scripts": scripts,
        "checks": checks,
    }


NOTHING_GRADABLE_FIX = ("Point me at a skill directory (with a SKILL.md), a SKILL.md file, "
                        "or a folder of skills.")


def collect_skills(paths):
    """Expand paths into skill and refusal dicts (supports a folder of skills).

    A path that yields nothing is a refusal of its own. Dropped silently, a
    mistyped second path left the first one's verdict standing as the run's.
    """
    found, seen = [], set()

    def add(sk):
        if sk and sk["path"] not in seen:
            seen.add(sk["path"])
            found.append(sk)
        return bool(sk)

    for p in paths:
        sk = load_skill(p)
        if sk:
            add(sk)
            continue
        hit = False
        if os.path.isdir(p):
            for child in sorted(os.listdir(p)):
                cd = os.path.join(p, child)
                if os.path.isdir(cd):
                    hit = add(load_skill(cd)) or hit
        if not hit:
            why = ("no such file or folder" if not os.path.exists(p) else
                   "no SKILL.md here, and no skill folder under it" if os.path.isdir(p) else
                   "a file, but not a SKILL.md")
            add(refusal(p, "nothing gradable: " + why, NOTHING_GRADABLE_FIX))
    return found


# ------------------------------------------------------------ detectors ------

def has(patterns, text, flags=re.IGNORECASE):
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            return m
    return None


GAP_MARKERS = [
    r"does\s?n'?t?\s+survive", r"\bwithout this skill\b", r"\bwithout the skill\b",
    r"\bthe base model\b", r"\bleft alone\b",
    r"\bthe gap\b", r"\bthe failure mode\b", r"\botherwise\b[^.\n]{0,60}\b(wrong|fails?|breaks?|drift|miss)",
    r"\bgets? (?:this |it )?wrong\b", r"\binconsistent(?:ly)?\b",
]

# a deterministic entry: a prefix/condition, not a keyword pile
#
# A backticked token ending in ':' or '/' is the SHAPE of a trigger prefix
# (`audit:`, `pl/`) and also the shape of a directory (`scripts/`), a Python
# keyword (`try:`) and a URI scheme (`data:`). Shape alone cannot separate
# them: measured against 31 known-good skills the bare pattern matched 56
# times, 52 of them folders and the other 4 syntax, for zero true positives
# and 15 false PASSes. So the token is necessary and never sufficient — the
# prose within TRIGGER_WINDOW characters has to say the token is the trigger.
# This is the same discipline GAP_MARKERS uses to keep "otherwise ... wrong"
# inside one sentence; here it is what stops a folder from being a trigger.
#
# The token may be quoted rather than backticked. A description is a YAML
# scalar and is usually written that way -- 'Any message beginning with
# "audit:"' -- and the description is where a prefix has to be (gate2).
_PREFIX_CORE = r"[A-Za-z][\w-]{0,23}[:/]"
PREFIX_TOKEN = (r"`" + _PREFIX_CORE + r"`"
                r"|\"" + _PREFIX_CORE + r"\""
                r"|\u201c" + _PREFIX_CORE + r"\u201d"
                r"|'" + _PREFIX_CORE + r"'"
                r"|\u2018" + _PREFIX_CORE + r"\u2019")
TRIGGER_WINDOW = 60
# Phrases about HOW THE SKILL IS ENTERED, not merely about the same subject.
# A bare topical word cannot be here: `\bcommand\b` next to `commands/` in a
# document about commands matched every time, which is the false positive in a
# different coat. Each entry has to be a claim that something fires.
TRIGGER_CONTEXT = [
    r"\btrigger", r"\bprefix\b", r"\bfires? on\b",
    # "begins with" is a trigger claim only when it is a MESSAGE that begins
    # with the token. Bare, it matched "start with the reusable resources
    # identified above: `scripts/`" — ordinary English, not an entry rule.
    r"\b(?:message|prompt|request|input|line)s?\b[^.\n]{0,24}\b(?:begin|start|open)(?:s|ning)?\s+with\b",
    r"\binvoked? (?:with|by|as)\b", r"\bwhen the user types\b",
    r"\btreat\b[^.\n]{0,20}\bas (?:a )?(?:command|prefix|trigger)\b",
]

# Phrases that declare a deterministic entry on their own, no token needed.
ENTRY_PHRASES = [
    r"\bprimary trigger is\b", r"\bhard trigger\b", r"\bdeterministic (?:entry|trigger)\b",
    r"\bany message beginning with\b", r"\bmessages? (?:that )?(?:begin|start)(?:s|ning)? with\b",
    # NOT a bare "starts with `...`": that matched plugin-structure's path rule
    # "Must start with `./`", which is a constraint on a config value and has
    # nothing to do with how the skill is entered. The subject has to be the
    # thing the user sends.
    r"\b(?:message|prompt|request|input|line)s?\b[^.\n]{0,24}\b(?:begin|start|open)(?:s|ning)?\s+with\b[^.\n]{0,30}`",
    r"\bwhen the user types\b",
    r"\btreat (?:any message|the prefix)\b",
]
ENTRY_MARKERS = ENTRY_PHRASES  # kept for callers that want the phrases alone

KEYWORD_TRIGGER_MARKERS = [
    # "Use when/for/whenever ...", with or without an intervening object:
    # "Use when the user asks", "Use this skill for .docx", "Use it whenever".
    r"\buse\s+(?:this\s+|the\s+|it\s+)?(?:skill\s+)?(?:when(?:ever)?|for)\b",
    r"\btrigger(?:s)? (?:on|include)\b", r"\btriggers include\b",
    r"\bkeywords?\b", r"\bwhen the user\b", r"\bapplies? (?:when|to)\b",
]

# The other way entry can be decided: a description that bounds it on both
# sides. "Use for .docx. Do NOT use for PDFs" fires semantically and is still
# unambiguous — it names the adjacent requests it must not take. Requiring a
# prefix instead would ask half the ecosystem to adopt a convention that would
# make it worse: nobody should have to type `docx:` to get a Word file handled.
# The gate asks whether entry is DECIDED, not whether it is PREFIXED.
ENTRY_NEGATIVE_MARKERS = [
    r"\b(?:do not|don't|never)\s+(?:use|trigger|invoke|apply)\s+(?:this|it|the skill|for|when|on|with)\b",
    r"\bnot for\b", r"\bwhen (?:not to|to not)\b", r"\bskip (?:this|it)\b",
    r"\bnot a (?:substitute|replacement)\b",
    r"\binstead of\b[^.\n]{0,60}\buse\b",
    r"\buse\b[^.\n]{0,40}\binstead\b",
]

# hard-fail claims. An explicit token with no backing check FAILs; imperative
# rule phrasing ("you must", "never <verb>", "always <verb>") with no explicit
# token and no backing check comes back REVIEW, however many there are.
# "refuse and" is not on the list: it is a scope exit, which gate 5 grades,
# and a script-free skill that refuses out-of-scope input declares no hard-fail.
HARDFAIL_EXPLICIT = [r"hard[\s\-‐-–]?fail", r"\bhard[\s\-‐-–]?stop\b"]
# "There are no hard-fails in this skill" declares none.
HARDFAIL_NEGATED = re.compile(r"\b(?:no|without|zero|not any)\s+(?:\w+\s+)?$", re.IGNORECASE)
IMPERATIVE_RULE = [
    r"\byou must\b", r"\bmust not\b", r"\bmust never\b", r"\bmust always\b",
    r"\bmust\s+\w+", r"\bshall not\b", r"\bnever\s+\w+", r"\balways\s+\w+",
    r"\bdo not\s+\w+", r"\bdon'?t\s+\w+", r"\brefuse\b", r"\breject\b", r"\babort\b",
]
ENFORCED_BY = re.compile(r"\benforced by\s+`?([\w./-]+\.(?:py|sh|js))`?", re.IGNORECASE)
SCRIPT_NAME = re.compile(r"(?<![\w./-])(?![Nn]ode\.js\b)[\w./-]+\.(?:py|sh|js|mjs|cjs)\b")
# A check described in words ("unless the check returns 0"), with no script
# shipped or named. A named script missing from the skill is no check.
ENFORCEMENT_MARKERS = [
    r"\bexit code\b", r"\bnon-?zero\b", r"\breturns? \d",
    r"\brun (?:the )?(?:check|script|audit|linter?)\b",
    r"\bthe check (?:returns|fails|passes)\b", r"\bverif(?:y|ies|ied) (?:with|by running)\b",
]

# verify-before-voice
#
# A countable constraint is written the way people write one: in lines and
# pages as well as characters, in words ("above two lines") as well as
# digits, and as a range ("2-3 sentences"). Each shape still needs a limiting
# word or a limiting construction beside it -- a bare "(1-2 words)" aside is
# not a rule the output must keep, and charging it as one would FAIL good
# skills.
_NUMW = (r"(?:thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen"
         r"|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve"
         r"|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand)")
# "three hundred", "twenty-five": a spelled number can run to several words;
# "1,500" is the same limit as "1500"
_NUM = r"(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|" + _NUMW + r"(?:[\s-]+" + _NUMW + r")*)"
_NUMR = _NUM + r"(?:\s*(?:-|\u2013|\u2014|to|or)\s*" + _NUM + r")?"
_UNIT = r"(?:characters?|chars?|words?|lines?|sentences?|bullets?|pages?|paragraphs?|items?|rows?)"
_LIMIT = (r"(?:under|over|at most|at least|up to|within|max(?:imum)?|min(?:imum)?"
          r"|no more than|not more than|no fewer than|fewer than|more than|less than"
          r"|limit(?:ed)? to|above|below|exceed(?:s|ing)?|capped at"
          r"|no longer than|not longer than|no shorter than|longer than|shorter than)")
# Not "past" or "beyond": "the description is past 1024 characters" states a
# fact about a file. Leaving them out misses "a bullet runs past two lines",
# which costs a NOT CHECKABLE; reading them would cost a FAIL on good skills.
CONSTRAINT_MARKERS = [
    r"\bcharacter count\b", r"\bchar(?:acter)? limit\b", r"\bword count\b",
    r"\bexactly \d", r"\bno more than \d",
    # a length spec, not a stray "(1-2 words)" aside: require a limiting word
    r"\b(?:under|over|at most|at least|up to|within|max|min|no fewer than|limit(?:ed)? to)\s+\d+\s*(?:characters?|chars?|words?)\b",
    # "spec" alone is not a constraint. In engineering prose it is almost
    # always a noun for a document -- "the MCP spec", "REPORT SPEC", "design
    # doc, plan, spec" -- and matching it bare FAILed three known-good skills
    # on a word that had nothing to do with a countable rule. The constraint
    # is the skill promising its own output CONFORMS to one.
    r"\b(?:conform(?:s|ing)?\s+to|match(?:es|ing)?|against|validate[sd]?\s+against)\s+(?:the\s+|its\s+|this\s+)?spec(?:ification)?\b",
    r"\bto\s+spec\b", r"\bmust match\b", r"\bcountable\b",
    # "above two lines", "under 3-5 bullets", "within one page"
    r"\b" + _LIMIT + r"\s+" + _NUMR + r"\s+" + _UNIT + r"\b",
    # "two lines at most", "3 bullets maximum"
    r"\b" + _NUMR + r"\s+" + _UNIT + r"\s+(?:at most|max(?:imum)?|or (?:fewer|less))\b",
    r"\b" + _NUM + r"\s+at most\b",
    # "between 3 and 5 bullets"
    r"\bbetween\s+" + _NUM + r"\s+and\s+" + _NUM + r"\s+" + _UNIT + r"\b",
    # "keep each bullet to one line", "limit the summary to 2-3 sentences"
    r"\b(?:keep|limit|cap|trim|hold)\b[^.\n]{0,40}?\bto\s+" + _NUMR + r"\s+" + _UNIT + r"\b",
    # "a soft four lines and a hard five"
    r"\b(?:soft|hard)\s+(?:limit\s+of\s+)?" + _NUM + r"\s+" + _UNIT + r"\b",
    # "<= 280 characters", "≤ 280 characters"
    r"(?:≤|<=)\s*" + _NUM + r"\s*" + _UNIT + r"\b",
]
# A constraint is a rule on the output only in a sentence that directs:
# "Keep the summary under 200 words". "Messages over 160 characters are split
# by the carrier" states a fact, and a fact is nothing to count.
DIRECTIVE = re.compile(r"\b(?:keep|limit|cap|trim|hold|must|should|never|always|do not|don't|make sure|ensure"
                       r"|stay|write|use|return|reply|output|no more than|at most|exactly|aim for"
                       r"|is wrong|is too long|not allowed|soft|hard|budget|limit|max(?:imum)?|min(?:imum)?)\b"
                       r"|≤|<=",
                       re.IGNORECASE)
VERIFY_MARKERS = [
    r"\bverif(?:y|ies|ied|ication)\b", r"\bcount (?:and|then) (?:confirm|check|verify)\b",
    r"\bbefore (?:emitting|responding|the response|you (?:respond|write))\b",
    r"\bconfirm(?:s|ed)? (?:the|each|every|it|them)\b", r"\bre-?run\b", r"\bcheck (?:the )?(?:count|output|result)\b",
    r"\bmeasure(?:d|s)? (?:the|it)\b",
    r"\bbefore (?:replying|answering|you (?:reply|answer))\b",
    r"\bprints? the (?:real |actual )?(?:count|number|length)\b",
    r"`wc\b", r"\buntil it (?:reports|returns|prints|shows)\b", r"\bcount (?:the|them|it|each|every)\b",
    r"\blen\(",
]
# A shipped check that fails over the limit ("exits 1 when the draft is over",
# "post only after it exits 0") verifies it only beside the limit: elsewhere it
# is any hard-fail's check, and reading it there would turn FAILs into REVIEW.
VERIFY_BESIDE = VERIFY_MARKERS + [r"\bexits?\s+`?(?:1|non-?zero)`?\s+(?:when|if)\b", r"\bafter it exits\s+`?0`?"]

# scope boundaries / named exits
SCOPE_MARKERS = [
    r"\bout of scope\b", r"\bscope boundar", r"\bdo not use (?:this )?(?:for|when|outside)\b",
    r"\bnot for\b", r"\bhard[\s-]?fail", r"\bwhen to (?:not|never) use\b",
]
NAMED_EXIT_MARKERS = [
    # a condition paired with an explicit action (allow periods inside the gap,
    # e.g. "...no SKILL.md: refuse" — the dot in a filename must not break it)
    r"\bif\b[^\n]{0,90}?\b(refuse|stop|abort|decline|hand off|handoff|do not proceed|say so)\b",
    r"\botherwise[, ]+[^\n]{0,40}\b(refuse|stop|hand|say|do)\b",
    # an explicit refusal used as the exit, in any of its common shapes
    r"\brefuse\b[^\n]{0,30}?[,]\s*\w", r"\brefuse and\b",
    r"\b(refuse|decline)\s+(?:to\s+)?(?:grade|emit|proceed|use|continue)\b",
    r"\b→\s*(refuse|stop|decline|hand)\b", r"\bif X, (?:refuse|do)\b",
    # "say it is out of scope, name the pdf skill, and stop"
    r"\b(?:say|tell|explain)\b[^.\n]{0,100}?\band (?:stop|refuse|decline|hand off)\b",
    r"\bname the [\w-]+ skill\b",
]
# "if the user pushes, don't stop them" names no exit.
EXIT_NEGATED = re.compile(r"\b(?:don'?t|do not|never|not)\s+(?:\w+\s+)?$", re.IGNORECASE)
# A soft exit FAILs on these phrasings. The first four are scope statements on
# their own: "Try to stay on the meeting content" needs no "Out of scope" beside it.
SOFT_SCOPE_SELF = [
    r"\btry to stay (?:on|in|within|inside|focused)\b", r"\bsteer\b[^.\n]{0,40}\bback\b",
    r"\bavoid (?:drifting|going off[\s-]topic)\b", r"\bstay on (?:topic|track|task)\b",
]
SOFT_SCOPE_MARKERS = SOFT_SCOPE_SELF + [r"\btry to stay\b", r"\bbe careful\b", r"\bwhere possible\b",
                                        r"\btry not to\b"]
# Weaker: "avoid", "should not", "try to" beside a scope boundary is REVIEW.
SOFT_SCOPE_WEAK = [r"\bshould (?:not|avoid)\b", r"\bavoid\b", r"\btry to\b"]

# cold-handoff killers: references to context the file does not contain
# \s+ between words, because markdown prose is hard-wrapped. "As discussed in
# the Scope section above" points into the file, and "per our style guide,
# `references/style.md`" names a file the skill ships: neither leans on a chat.
CONTEXT_LEAK_MARKERS = [
    r"\bas\s+(?:we\s+)?discussed\b(?!\s+(?:above|below)\b"
    r"|\s+(?:in|under)\b[^.\n]{0,40}?\b(?:section|heading|step|table|part)s?\b)",
    r"\bper\s+our\b(?![^.\n]{0,60}(?:`|\]\(|\b(?:section|heading|step|table|below|above)\b))",
    r"\bas\s+(?:above|before)\s+in\s+(?:this|the)\s+(?:chat|thread|conversation)\b",
    r"\blike\s+(?:last\s+time|before\b(?![/-]|\s+and\s+after))", r"\bas\s+last\s+time\b",
    # "our" only, as README lists it: "the transcript of the previous session"
    # the user hands over is a file, not a prior turn.
    r"\bour\s+(?:last|previous|prior|earlier)\s+(?:conversation|chat|session|thread|discussion)\b",
    r"\bearlier\s+in\s+(?:this|the)\s+(?:chat|thread)\b",
    r"\bas\s+established\s+(?:above|earlier)\b",
    # "you already know" needs a discourse-deictic object to be a leak. Bare,
    # it FAILed a known-good skill for telling the reader they know their own
    # phone contacts -- a fact about the world, not about a prior turn.
    r"\byou\s+already\s+know\b[^.\n]{0,60}\bfrom\s+(?:our|this|the)\s+(?:chat|thread|conversation|session|discussion)\b",
    r"\byou\s+already\s+know\b[^.\n]{0,40}\bfrom\s+(?:above|earlier|before)\b",
    r"\byou\s+already\s+know\s+(?:this|that|the\s+drill|how\s+this\s+(?:goes|works)|what\s+(?:I|we)\s+mean)\b",
]

# A phrase in code, single emphasis or quotes is named, not used: "strip
# filler such as *as we discussed*" forbids the phrase rather than leaning on it.
# README states this for every gate, so gates 1, 3, 4, 6 and 7 all read _masked().
LEAK_MENTION = re.compile(r"`[^`]*`|(?<![*\w])\*(?!\*)[^*\n]+\*(?![*\w])|(?<!\w)_[^_\n]+_(?!\w)"
                          "|\"[^\"\\n]*\"|\u201c[^\u201d\\n]*\u201d")


def _masked(text):
    """The text with mentioned phrases blanked, same length and same lines;
    a code span keeps its backticks, so "per our ... `file`" still sees one."""
    def blank(m):
        s = m.group(0)
        if s.startswith("`") and len(s) > 1:
            return "`" + re.sub(r"[^\n]", "x", s[1:-1]) + "`"
        return re.sub(r"[^\n]", " ", s)
    return LEAK_MENTION.sub(blank, text)


# A hard-wrapped line break inside a paragraph is a space. Not before a blank
# line, a heading, a list item, a table row, a fence or a quote: those start a
# new block. Same length, so offsets still index the original.
SOFT_WRAP = re.compile(r"\n(?![ \t]*(?:\n|$|#|[-*+][ \t]|\d+[.)][ \t]|\||```|~~~|>))")


def _unwrapped(text):
    return SOFT_WRAP.sub(" ", text)


# "as discussed in references/style.md": the path a leak phrase points at, in
# the rest of its sentence.
LEAK_TARGET = re.compile(r"[\w][\w./-]*\.\w+")


def _points_at_shipped(sk, tail):
    """True when `tail` (the text after a leak phrase) names a file the skill ships."""
    tail = re.split(r"\.(?=\s|$)", tail[:80], maxsplit=1)[0]
    for tok in LEAK_TARGET.findall(tail):
        tok = tok.rstrip(REF_TRAILING)
        if not REF_REJECT.search(tok) and os.path.isfile(os.path.join(sk["dir"], *tok.split("/"))):
            return True
    return False

# worked example
#
# Two kinds of marker. A worked example is something the file sets out -- a
# heading, an Input:/Output: pair, a bold "Example" label -- and it has a
# section of its own, which is where its catch has to be (gate7). An inline
# aside ("for example", "e.g.") or a mention ("the worked example in
# examples/") is a clause in a sentence about something else: it shows no
# case going wrong, and the section around it is not the example's.
WORKED_EXAMPLE_MARKERS = [
    r"^#+\s+.*\b(?:examples?|walkthrough)\b",
    r"^\s*(?:Input|User|Prompt|Output)\s*:",
    r"\*\*example\b", r"^\s*(?:Example|Ex\.)\s*\d",
    r"\bhere'?s (?:an|a) example\b", r"\bsample (?:input|output|run|skill|call)\b",
]
INLINE_EXAMPLE_MARKERS = [r"\bfor (?:example|instance)\b", r"\be\.g\.\b",
                          r"\bworked example\b", r"\bwalkthrough\b"]
EXAMPLE_MARKERS = WORKED_EXAMPLE_MARKERS + INLINE_EXAMPLE_MARKERS
CATCH_MARKERS = [
    r"\bcatch(?:es|ing)?\b", r"\bcaught\b", r"\bwould otherwise\b", r"\bgets? (?:it )?wrong\b",
    r"\binstead of \w+ing\b", r"\bwould have\b", r"\bsilently\b", r"\b(?:bare|base) model\b", r"\bmistake\b", r"\btrap\b", r"\bgotcha\b", r"\bbefore\b.*\bafter\b",
    r"\bfails?\b", r"\bthe bad case\b", r"\bnaive\b", r"\bna(?:ï|i)ve\b",
]


# ------------------------------------------------------------ gate checks ----

def gate1(sk):
    # Headings dropped: "## The gap it closes" over "See below" states no gap.
    text = sk["description"] + "\n" + re.sub(r"(?m)^#{1,6}\s.*$", "", sk["body"])
    if has(GAP_MARKERS, _masked(text)):  # "without this skill" in quotes is a mention
        return "PASS", "A gap/failure-mode statement is present.", \
            "Confirm it names one specific thing the base model gets wrong — not a vague benefit."
    return "REVIEW", "No gap statement detected.", \
        "State in one sentence what the base model gets wrong or does inconsistently without this skill."


def _declared_prefix(text):
    """A backticked or quoted prefix token the surrounding prose calls a trigger.

    The token alone is worthless (see PREFIX_TOKEN). Returns the match only
    when TRIGGER_CONTEXT appears within TRIGGER_WINDOW characters either side,
    which is what separates `audit:` in "primary trigger is `audit:`" from
    `scripts/` in "executable code lives in `scripts/`".
    """
    for m in re.finditer(PREFIX_TOKEN, text):
        lo = max(0, m.start() - TRIGGER_WINDOW)
        hi = min(len(text), m.end() + TRIGGER_WINDOW)
        clause = re.split(r"[.;\n]", text[m.end():hi], maxsplit=1)[0]
        if has(TRIGGER_CONTEXT, text[lo:hi]) and not has(PREFIX_RETIRED, clause):
            return m
    return None


# "`min:` is deprecated and no longer invokes this skill": named, and retired.
# Read in the token's own clause only, so "`min:` fires it; `minutes:` no
# longer does" keeps `min:`.
PREFIX_RETIRED = [r"\bdeprecated\b", r"\bno longer\b", r"\bretired\b",
                  r"\b(?:does|do) not (?:invoke|trigger|fire)\b"]


def _as_code(m):
    """A declared prefix as the report prints it: backticked, however quoted."""
    return "`%s`" % m.group(0)[1:-1]


def gate2(sk):
    # The description is the only text read when a skill is chosen; the body
    # is read after. A prefix the body declares therefore cannot route a
    # message to this skill, however clearly it is written there, so a
    # deterministic entry counts only where the router reads it.
    text = sk["description"]
    prefix = _declared_prefix(text)
    if prefix or has(ENTRY_PHRASES, text):
        detail = (" (%s)" % _as_code(prefix)) if prefix else ""
        return "PASS", "A deterministic entry (prefix or unambiguous condition) is present%s." % detail, ""
    # Entry decided in prose rather than in punctuation: the description says
    # both when to fire and when not to. Unambiguous without a prefix, and the
    # only shape available to a skill that has to fire semantically.
    if has(KEYWORD_TRIGGER_MARKERS, sk["description"]) \
            and has(ENTRY_NEGATIVE_MARKERS, sk["description"]):
        return "PASS", "Entry is bounded on both sides: the description says when to fire and when not to.", ""
    in_body = _declared_prefix(sk["body"])
    if in_body or has(ENTRY_PHRASES, sk["body"]):
        shown = (" (%s)" % _as_code(in_body)) if in_body else ""
        return "REVIEW", "A deterministic entry is declared in the body%s but not in the description." % shown, \
            "Only the description is read when a skill is chosen, so an entry the body declares cannot route " \
            "a message here. Say it in the description: 'Any message beginning with `foo:` invokes this " \
            "skill.' (Gate 2)"
    text = sk["description"] + "\n" + sk["body"]
    if has(KEYWORD_TRIGGER_MARKERS, text):
        return "REVIEW", "Entry is description/keyword-based — the ecosystem norm, but the boundary is unstated.", \
            "This fires semantically, and nothing says which adjacent requests it must decline. Either add a hard " \
            "trigger (a prefix like `foo:`) or bound the description on both sides — what it is for, and what it is " \
            "not for. Naming the near-miss cases is what makes semantic entry predictable. (Gate 2)"
    return "REVIEW", "No trigger mechanism detected at all.", \
        "Declare how the skill fires — a deterministic entry (a prefix or unambiguous condition) is the most predictable."


def _count(patterns, text):
    return sum(1 for pat in patterns if re.search(pat, text, re.IGNORECASE))


def _explicit_hardfail(text):
    """A hard-fail token the text declares, not one it denies ("no hard-fails")."""
    for pat in HARDFAIL_EXPLICIT:
        for m in re.finditer(pat, text, re.IGNORECASE):
            if not HARDFAIL_NEGATED.search(text[max(0, m.start() - 24):m.start()]):
                return m
    return None


SENTENCE_END = re.compile(r"[.!?](?=\s|$)")


def _described_check(text):
    """A check described in words in a sentence that names no script. A script
    named in that sentence is the check, and none ships (README: "when the only
    check named is a script missing from the skill"); a file named in another
    sentence, such as the user's vitest.config.js, is not the check."""
    text = _unwrapped(text)
    for pat in ENFORCEMENT_MARKERS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            lo = max([e.end() for e in SENTENCE_END.finditer(text, 0, m.start())] or [0])
            nxt = SENTENCE_END.search(text, m.end())
            if not SCRIPT_NAME.search(text[lo:nxt.start() if nxt else len(text)]):
                return True
    return False


def gate3(sk):
    text = sk["body"]
    # `hard-fail: true` in code, or "hard stop" in quotes, is content the skill
    # reads, not a rule it declares (README: a mention, not a use).
    explicit = bool(_explicit_hardfail(_masked(text)))
    imperatives = _count(IMPERATIVE_RULE, text)
    checks = sk.get("checks", sk["scripts"])
    # Enforced: a script ships, or a check is described in words and no script
    # is named. A script the text names but the skill lacks is no check.
    enforced = bool(checks)

    def shipped(name):  # "enforced by check.py" is met by scripts/check.py as well
        return os.path.isfile(os.path.join(sk["dir"], *name.split("/"))) or \
            any(c == name or c.endswith("/" + name) for c in checks)
    if any(not shipped(m.group(1)) for m in ENFORCED_BY.finditer(text)):
        enforced = False  # "enforced by check.py", and check.py is not in the skill
    described = not checks and _described_check(text)
    if not explicit and imperatives == 0:
        return "REVIEW", "No hard-fails declared.", \
            "If this skill has a constraint that must always hold, name it as a hard-fail and back it with a check."
    if enforced:
        return "PASS", "Hard-fails are present and the skill ships a script (%s)." % ", ".join(sk["scripts"] or checks), \
            "Confirm every claimed hard-fail is actually covered by a check — a lint can't map claim to check."
    if described:
        return "PASS", "Hard-fails are present and the skill references a mechanical check.", \
            "Confirm every claimed hard-fail is actually covered by a check — a lint can't map claim to check."
    if explicit:
        return "FAIL", "A hard-fail is explicitly declared but asserted in prose with no backing check.", \
            "A hard-fail that lives in a sentence is a suggestion. Back each with a check that returns a real " \
            "signal (exit code, count, diff) before the skill emits. (Gate 3)"
    return "REVIEW", "Rule-like imperatives are present but no explicit hard-fail is declared or enforced.", \
        "If any of these must always hold, name it as a hard-fail and back it with a check rather than leaving it as prose."


# Where a directing word stops reaching a limit: a sentence end, or a clause
# joined by "so"/"but". "Slack truncates messages over 4,000 characters, so
# never paste a whole log" directs the pasting, not the count (README: a
# number stated as a fact is NOT CHECKABLE).
CLAUSE_END = re.compile(r"[.;\n]|,\s+(?:so|but)\b", re.IGNORECASE)


def _directive(pattern_list, text):
    """The first constraint match whose clause directs the output."""
    for pat in pattern_list:
        for m in re.finditer(pat, text, re.IGNORECASE):
            lo = max([e.end() for e in CLAUSE_END.finditer(text, 0, m.start())] or [0])
            nxt = CLAUSE_END.search(text, m.end())
            hi = nxt.start() if nxt else len(text)
            if DIRECTIVE.search(text[lo:hi]):
                return m
    return None


def _defenced(text):
    """The text with fenced code blanked, same length and same lines: a limit
    inside a prompt template the skill writes is shown, not a rule on its own
    output (README: a phrase in code is a mention, not a use)."""
    out, inside = [], False
    for line in text.splitlines(keepends=True):
        if FENCE.match(line):
            inside = not inside
            out.append(line)
        else:
            out.append(re.sub(r"[^\n]", " ", line) if inside else line)
    return "".join(out)


def gate4(sk):
    text = sk["body"]
    # Constraints are read outside fences and with mentions blanked (a limit
    # quoted as an example's input is shown, not set); a verify step may sit
    # in either (```wc -w reply.md```), so it is read from the text as written.
    plain = _masked(_defenced(text))
    constraints = _directive(CONSTRAINT_MARKERS, plain)
    # In the constraint's own section: "verify the front matter parses" under
    # Setup does not count a word limit set under Rules.
    starts = [0] + [m.start() for m in re.finditer(r"(?m)^#{1,6}\s", plain) if m.start() > 0]
    verify = next((True for a, b in zip(starts, starts[1:] + [len(text)])
                   if has(CONSTRAINT_MARKERS, plain[a:b]) and has(VERIFY_BESIDE, text[a:b])), None)
    if not constraints:
        # Not a PASS: a gate with no premise has not been satisfied; it has
        # not been asked.
        return NOTCHECK, "No countable/spec'd constraint detected; gate not applicable.", \
            "If the skill does have a hard constraint (a count, a spec), make sure it's verified, not asserted."
    if verify:
        return "PASS", "A hard constraint is present and a verification step is described.", ""
    if has(VERIFY_MARKERS, text):
        # A step elsewhere may still count it ("verify" under Setup, the limit
        # under Rules). Known-good skills are written this way, so this is a
        # question for a reader, not a FAIL.
        return "REVIEW", "A countable/spec'd constraint is present, and a verification step, but not in the same " \
            "section.", "Confirm the step actually counts this constraint, or move the count beside it. (Gate 4)"
    return "FAIL", "A countable/spec'd constraint is present but no verification step was detected.", \
        "Write the output around a verified result — run the check first, then speak. (Gate 4)"


def _named_exit(text):
    """A named exit that is not negated ("don't stop them" names none). Read
    with soft wraps joined: "if\\nthe file ..., stop" is one sentence."""
    text = _unwrapped(text)
    for pat in NAMED_EXIT_MARKERS:
        for m in re.finditer(pat, text, re.IGNORECASE | re.MULTILINE):
            verb = m.lastindex and m.start(m.lastindex)
            if verb and EXIT_NEGATED.search(text[max(0, verb - 20):verb]):
                continue
            return m
    return None


def _soft_beside_scope(text, soft_list=None):
    """The first soft phrase in a section that is about scope and names no exit.

    Paired across the whole file, a Hard-fails heading at the top and "Avoid
    jargon" in a style tip at the bottom read as a soft scope exit. A section
    is about scope when it holds a scope marker or a SOFT_SCOPE_SELF phrase.
    """
    for section in re.split(r"(?m)^(?=#{1,6}\s)", _strip_table_rows(text)):
        if (has(SCOPE_MARKERS, section) or has(SOFT_SCOPE_SELF, section)) and not _named_exit(section):
            soft = has(soft_list or SOFT_SCOPE_MARKERS, section)
            if soft:
                return soft
    return None


def _strip_table_rows(text):
    """Drop markdown table rows before looking for a scope boundary.

    A scope phrase inside a table cell is usually describing the artifact the
    skill *produces* -- "a short **Out of scope** list bounds the reader's
    worry" -- not the skill's own boundary. Reading it as the latter FAILed a
    known-good skill for documenting a section heading.
    """
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("|"))


def gate5(sk):
    text = sk["body"]
    scope = has(SCOPE_MARKERS, _strip_table_rows(text)) or has(SOFT_SCOPE_SELF, _strip_table_rows(text))
    named = _named_exit(text)
    soft = _soft_beside_scope(text)
    if scope and soft:
        # The anti-pattern this gate FAILs on is scope-as-intention. Naming the
        # soft phrase is the point: quoting "try to stay in scope" at a skill
        # that never wrote it is a fix the author cannot act on.
        return "FAIL", "Scope language is present but the exit is soft (%r)." % soft.group(0), \
            "Replace that with 'if X, refuse and do Y' — a named action, not an intention. (Gate 5)"
    if scope and named:
        return "PASS", "Scope boundaries name an explicit exit (if X, refuse and do Y).", ""
    weak = _soft_beside_scope(text, SOFT_SCOPE_WEAK)
    if scope and weak:
        return "REVIEW", "A scope boundary sits beside softer wording (%r) and the lint found no named exit." \
            % weak.group(0), "Confirm the boundary ends in an action — 'if X, refuse and do Y'. (Gate 5)"
    if scope:
        return "REVIEW", "A scope boundary is present but the lint found no named exit.", \
            "Confirm the boundary ends in an action — 'if X, refuse and do Y' — rather than trailing off. (Gate 5)"
    # Absence here is not a verdict. SCOPE_MARKERS is a short list of literal
    # phrases, and a boundary written in any other idiom reads as absence — so
    # the lint cannot tell "this skill declares no boundary" from "this skill
    # declares one I don't know the words for". Measured against 31 known-good
    # skills the whole list matched one string, inside a table row that
    # _strip_table_rows correctly drops. The scope-and-soft FAIL branch above
    # pairs only inside one section (_soft_beside_scope); before that, those two
    # detectors are far enough apart in a long file to pair unrelated
    # sentences, and widening the first arms the second.
    return NOTCHECK, "No scope boundary detected.", \
        "Confirm the skill can't be pulled out of scope, or add a boundary with a named exit."


def _context_leak(sk):
    """The first leak phrase that is used, not mentioned, and points at no
    file the skill ships. Read with soft wraps joined, so README's own exempt
    example still exempts when ordinary markdown breaks it across two lines."""
    body = _unwrapped(sk["body"])
    masked = _masked(body)
    for pat in CONTEXT_LEAK_MARKERS:
        for m in re.finditer(pat, masked, re.IGNORECASE):
            if not _points_at_shipped(sk, body[m.end():]):
                return m
    return None


def gate6(sk):
    leak = _context_leak(sk)
    if leak:
        return "FAIL", "The skill leans on a conversation it does not contain (%r)." % leak.group(0), \
            "A fresh session never had that conversation. Put what it refers to into the skill itself. (Gate 6)"
    # This gate grades what it reads. Its premise is always present -- the
    # phrasing it looks for would be in the body, and the body is always
    # there to scan -- so a clean scan is a decided PASS, not a vacuous one.
    # Whether the skill works in a fresh session is still no gate's to
    # decide: print_report names it under every verdict (NOT_GRADED).
    return "PASS", "No phrasing that leans on an earlier chat (\"as we discussed\", \"like last time\").", ""


HEADING = re.compile(r"^(#{1,6})\s+\S")
FENCE = re.compile(r"^\s*(?:```|~~~)")


def _headings(body):
    """(offset, level) of every markdown heading. A `#` line inside a code
    fence is a comment in someone's script, not a heading."""
    heads, pos, fenced = [], 0, False
    for line in body.splitlines(True):
        if FENCE.match(line):
            fenced = not fenced
        elif not fenced:
            m = HEADING.match(line)
            if m:
                heads.append((pos, len(m.group(1))))
        pos += len(line)
    return heads


def _sections(body, heads=None):
    """(start, end) of every heading's section: from the heading line to the
    next heading of the same or a higher level."""
    heads = _headings(body) if heads is None else heads
    out = []
    for i, (start, level) in enumerate(heads):
        end = next((s for s, lv in heads[i + 1:] if lv <= level), len(body))
        out.append((start, end))
    return out


def _section_of(body, sections, offset):
    """The innermost section holding `offset`, or the text before the first
    heading when the offset sits there."""
    inside = [(s, e) for s, e in sections if s <= offset < e]
    if inside:
        return max(inside)
    first = min((s for s, _ in sections), default=len(body))
    return (0, first) if offset < first else (0, len(body))


def gate7(sk):
    text = sk["body"]
    flags = re.IGNORECASE | re.MULTILINE
    heads = _headings(text)
    real = {at for at, _ in heads}
    worked = sorted({m.start() for pat in WORKED_EXAMPLE_MARKERS
                     for m in re.finditer(pat, text, flags)
                     if not pat.startswith("^#") or m.start() in real})
    if worked:
        # The catch has to be in the example's own section. Counted anywhere
        # in the body, an "instead of" three sections away passed a skill
        # whose worked example had been deleted outright.
        sections = _sections(text, heads)
        for at in worked:
            lo, hi = _section_of(text, sections, at)
            nl = text.find("\n", lo)
            if text.startswith("#", lo) and 0 <= nl < hi:  # "(a catch, not a happy path)" in a heading is a claim
                lo = nl + 1
            if has(CATCH_MARKERS, _masked(text[lo:hi])):  # `silently-dropped` in code is a mention
                return "PASS", "A worked example is present and shows a catch, not just the happy path.", ""
        return "REVIEW", "An example is present but reads like a happy path.", \
            "Confirm at least one example shows the skill catching a case that would otherwise go wrong. (Gate 7)"
    if has(INLINE_EXAMPLE_MARKERS, text, flags=flags):
        return NOTCHECK, "Examples appear only inline (\"for example\", \"e.g.\", a mention), and none is set " \
            "out in a section the lint can read for a catch.", \
            "Confirm by eye that at least one example shows a catch, not the happy path -- or set one out under " \
            "its own heading, with the case that goes wrong. (Gate 7)"
    # The message already conceded the lint may simply have failed to read the
    # file; reporting that concession as REVIEW charged the skill for it.
    return NOTCHECK, "No example detected by the lint — it may present usage in a form the lint can't read (e.g. code recipes).", \
        "Confirm by eye that at least one example shows a catch, not the happy path — the obvious case succeeding is decoration. (Gate 7)"


# ------------------------------------------------------- preflight: refs ----
#
# The hard part of this check is not finding paths — it is telling a path that
# addresses THIS SKILL'S OWN BUNDLE from one that addresses the workspace the
# skill operates on. A SKILL.md is full of the second kind: `word/document.xml`
# inside a document being unpacked, `.claude/settings.json` in the user's repo,
# `../out.docx` as an output, a script the skill tells the model to write at
# run time. None of those can or should resolve here, and flagging them is the
# false positive that would make this check worthless.
#
# So a token counts as a bundle reference only when the skill's own layout
# vouches for it: its first segment is a directory the skill actually ships, or
# it is a bare script name and the skill ships scripts at its root. Anything
# else is a workspace path and is left alone — reported as skipped, never as
# a finding.

# Anything containing these is a placeholder, a glob, a URL, a shell
# construct, or a traversal — not a concrete path inside this skill.
REF_REJECT = re.compile(r"[<>{}*?|$\"'\\]|://|^[#~/]|^\.\.|^-")

# Trailing punctuation that belongs to the prose, not the path.
REF_TRAILING = ".,:;!?)]}\u2019\u201d"

INLINE_CODE = re.compile(r"`([^`\n]+)`")
FENCED_CODE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
# [text](target "title") and [text](<target>) as well as [text](target)
MD_LINK = re.compile(r"\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)")
# [label]: target -- the definition a reference-style link [text][label] points at
REF_DEF = re.compile(r"(?m)^ {0,3}\[[^\]]+\]:\s*<?([^\s>]+)>?")
# scripts/lint.py:3 is a line in a file, not a file named "lint.py:3"
LINE_REF = re.compile(r":\d+(?::\d+)?$")
# "write it to `scripts/x.py` in the user's repository": a file the model authors
AUTHORED_LINE = re.compile(r"\bthe user'?s (?:repo|repository|project|workspace|working directory)\b",
                           re.IGNORECASE)

# A path on a line that announces itself as illustrative is not a claim to
# ship that file. Skills about skills are full of these -- "**Examples**:
# `references/finance.md` for financial schemas" is naming a file the READER
# might write, in a skill that happens to ship a references/ directory of its
# own, which is exactly the coincidence the first-segment rule cannot tell
# apart. Scoped to the line: a heading two paragraphs up exempts nothing.
ILLUSTRATIVE = re.compile(
    r"\*\*examples?\*\*|(?:^|[\s(*_])examples?\s*:|\be\.g\.|\bfor example\b"
    r"|\bfor instance\b|\bsuch as\b",
    re.IGNORECASE)

TOKEN_RUN = re.compile(r"\S+")
PROSE_PATH = re.compile(r"(?<![\w`/.(\[-])([A-Za-z0-9_-]+/[\w./-]*\.[A-Za-z0-9]+)(?![\w/])")

# A pointer verb immediately before the path is the skill telling you the file
# is THERE -- "see `references/api.md`", "load `references/schema.md`". That,
# a markdown link, and an invocation are the three strong claims. A path that
# merely appears in a bullet is a weak one, and the difference decides FAIL
# from REVIEW below.
POINTER_VERB = re.compile(
    r"\b(?:see|read|reads?|load|loads?|open|run|runs?|consult|refer to|"
    r"defined in|documented in|described in|listed in|found in|per)\b[^.\n]{0,40}$",
    re.IGNORECASE)


INTERPRETERS = {"python", "python3", "python2", "py", "node", "deno", "bun",
                "bash", "sh", "zsh", "ruby", "perl", "pwsh", "powershell"}


def _line_containing(body, line_starts, offset):
    i = bisect.bisect_right(line_starts, offset) - 1
    end = body.find("\n", offset)
    return body[line_starts[i]:end if end != -1 else len(body)]


def _ref_tokens(body):
    """Path-shaped tokens from code spans, fenced blocks and link targets.

    Yields (token, invoked, illustrative, strong). `invoked` is True when the
    token is being executed (an interpreter immediately before it, or a ./
    prefix). `illustrative` is True when the line it sits on announces itself
    as an example. `strong` is True when the skill is pointing AT the file --
    a markdown link, an invocation, or a pointer verb ahead of it on the line.
    Bare prose is not collected: a filename in running text is a mention, not
    a reference.
    """
    line_starts = [0] + [i + 1 for i, ch in enumerate(body) if ch == "\n"]

    spans = [(m.start(1), m.group(1), False) for m in INLINE_CODE.finditer(body)]
    spans += [(m.start(1), m.group(1), False) for m in FENCED_CODE.finditer(body)]
    spans += [(m.start(1), m.group(1), True) for m in MD_LINK.finditer(body)]
    spans += [(m.start(1), m.group(1), True) for m in REF_DEF.finditer(body)]

    out = []
    for base, inner, linked in spans:
        after_interp = False
        for m in TOKEN_RUN.finditer(inner):
            raw = m.group(0)
            tok = LINE_REF.sub("", raw.strip().rstrip(REF_TRAILING).replace("\\", "/"))
            invoked = tok.startswith("./") or after_interp
            # "python3 -u scripts/x.py": flags between interpreter and script
            after_interp = raw.lower() in INTERPRETERS or (after_interp and raw.startswith("-"))
            tok = tok[2:] if tok.startswith("./") else tok
            if linked:  # a link target is a URL: drop its #fragment, decode %20
                tok = unquote(tok.split("#", 1)[0])
            if not tok or REF_REJECT.search(tok) or not os.path.splitext(tok)[1]:
                continue
            start = base + m.start()
            line = _line_containing(body, line_starts, start)
            before = body[line_starts[bisect.bisect_right(line_starts, start) - 1]:start]
            strong = linked or invoked or bool(POINTER_VERB.search(before))
            out.append((tok, invoked, bool(ILLUSTRATIVE.search(line)), strong))
    return out


def _bundle_refs(sk):
    """Split the token pool into (bundle claims, skipped paths, strong claims)."""
    try:
        entries = os.listdir(sk["dir"])
    except OSError:
        return [], [], set()
    dirs = {e for e in entries if os.path.isdir(os.path.join(sk["dir"], e))}

    # Fold duplicates first, ORing the invoked flag: a script named in prose
    # and run in a code block is invoked. Classifying on first sight instead
    # would let the earlier, weaker mention decide.
    order, invoked_any, illus_all, strong_any = [], {}, {}, set()
    for tok, invoked, illus, strong in _ref_tokens(sk["body"]):
        if tok not in invoked_any:
            order.append(tok)
            illus_all[tok] = True
        invoked_any[tok] = invoked_any.get(tok, False) or invoked
        # AND, where invoked ORs: one occurrence on a real line makes the token
        # a claim, however many illustrative mentions sit beside it.
        illus_all[tok] = illus_all[tok] and illus
        if strong:
            strong_any.add(tok)

    authored = {t for line in sk["body"].splitlines() if AUTHORED_LINE.search(line)
                for span in INLINE_CODE.findall(line) for t in span.split()}
    claims, skipped = [], []
    for tok in order:
        invoked = invoked_any[tok]
        if illus_all[tok] or tok in authored:
            skipped.append(tok)
        elif "/" in tok:
            # A path is this skill's business only if it starts in a directory
            # this skill actually ships. `scripts/build.py` in a skill with a
            # scripts/ dir is a claim; `word/document.xml` in one without a
            # word/ dir is a runtime path in someone else's document.
            (claims if tok.split("/", 1)[0] in dirs else skipped).append(tok)
        elif (invoked and sk["scripts"]
              and os.path.splitext(tok)[1].lower() in SCRIPT_EXT):
            # A bare script name is a claim only when the skill tells you to
            # RUN it AND the skill ships scripts of its own. Naming a file in
            # a tree diagram is not a claim to ship it, and a skill that ships
            # nothing is telling the model to write the script it then runs --
            # both are common, and neither is a broken reference.
            claims.append(tok)
        else:
            skipped.append(tok)
    # Plain prose too, but only a path under a folder this skill ships. Named
    # in passing it is a weak claim: missing, REVIEW. After a pointer verb
    # ("See references/style.md") it is pointed at, backticked or not, and
    # missing it is a FAIL -- README's [R] rule names the verb, not the quoting.
    prose = MD_LINK.sub(" ", INLINE_CODE.sub(" ", FENCED_CODE.sub(" ", sk["body"])))
    for line in prose.splitlines():
        if ILLUSTRATIVE.search(line):
            continue
        for m in PROSE_PATH.finditer(line):
            tok = m.group(1)
            if tok.split("/", 1)[0] in dirs and tok not in invoked_any and tok not in authored:
                if tok not in claims:
                    claims.append(tok)
                if POINTER_VERB.search(line[:m.start()]):
                    strong_any.add(tok)
    return claims, skipped, strong_any


# ------------------------------------------------ preflight: description ----

# The hard limit on a skill `description`. Past it the field is truncated when
# the platform ingests it: the tail is dropped, nothing warns, and a trigger
# sentence that lived in the tail simply stops firing.
MAX_DESCRIPTION = 1024

# claude.ai refuses the upload outright when the description holds anything
# shaped like an XML tag -- "SKILL.md description cannot contain XML tags".
# The cause is almost always a placeholder (`recheck <path>`) and not markup.
# Claude Code accepts the same file, so nothing local catches it. The exact
# server-side rule is unpublished, so this matches any <...> span, which is the
# rule the build tooling behind this skill enforces on the way into an archive.
DESCRIPTION_TAG_RE = re.compile(r"<[^<>]*>")


def check_description(sk):
    """Preflight: the platform must accept the description as written.

    An integrity check, not a quality gate. A description the platform refuses
    or silently truncates is not a design flaw to weigh -- the skill either
    never installs or installs with half its trigger missing, and every gate
    below would then be grading a file nobody can run.
    """
    desc = sk["description"]
    if not desc.strip():
        return (NOTCHECK, "SKILL.md declares no description.",
                "Nothing here to measure against the platform's limits. A skill needs "
                "a `description:` to be selected at all, and gates 1 and 2 grade what "
                "it says. (Preflight)")

    problems, fixes = [], []

    tags = DESCRIPTION_TAG_RE.findall(desc)
    if tags:
        shown = ", ".join(repr(t) for t in tags[:4]) + (" ..." if len(tags) > 4 else "")
        problems.append("holds %s, which claude.ai refuses at upload" % shown)
        fixes.append(
            "claude.ai answers the upload with \"SKILL.md description cannot contain "
            "XML tags\" and installs nothing. Write the placeholder without angle "
            "brackets -- `recheck PATH`, not `recheck <path>`. Claude Code accepts "
            "the same file, which is why this is found at upload and not before.")

    if len(desc) > MAX_DESCRIPTION:
        problems.append("is %d chars, %d over the %d-char limit"
                        % (len(desc), len(desc) - MAX_DESCRIPTION, MAX_DESCRIPTION))
        fixes.append(
            "Past %d characters the description is truncated on ingest and the tail is "
            "lost with no warning. Cut it to length yourself, so that you choose what "
            "goes rather than the platform choosing for you." % MAX_DESCRIPTION)

    if problems:
        return ("FAIL", "description " + " and ".join(problems) + ".",
                " ".join(fixes) + " (Preflight)")

    return ("PASS", "description is %d of %d chars and holds no XML-tag shape."
            % (len(desc), MAX_DESCRIPTION), "")


def check_refs(sk):
    """Preflight: every path the skill claims to ship must resolve.

    This is an integrity check, not a quality gate. It runs before the Floor
    because a skill pointing at a file that is not there is broken the way a
    build break is broken, and no gate below can see it.
    """
    claims, skipped, strong = _bundle_refs(sk)
    missing = [t for t in claims
               if not os.path.exists(os.path.normpath(os.path.join(sk["dir"], t)))]
    hard = [t for t in missing if t in strong]
    tail = (" (%d workspace path(s) skipped — not this skill's to resolve)" % len(skipped)) if skipped else ""

    if hard:
        shown = ", ".join(hard[:6]) + (" ..." if len(hard) > 6 else "")
        return ("FAIL",
                "%d of %d bundled path(s) the skill points at do not exist: %s%s"
                % (len(hard), len(claims), shown, tail),
                "A file the skill says it ships and does not is a skill that breaks on first run, "
                "and no gate below can see it. Fix the path or ship the file. (Preflight)",
                hard)
    if missing:
        # Missing, but only ever named in passing. A skill teaching skill
        # layout writes `references/patterns.md` as advice in exactly the form
        # it writes a file it really ships -- the two are byte-identical on the
        # page, so a lint cannot call this broken without inventing evidence.
        shown = ", ".join(missing[:6]) + (" ..." if len(missing) > 6 else "")
        return ("REVIEW",
                "%d of %d bundled path(s) are named but not present: %s%s"
                % (len(missing), len(claims), shown, tail),
                "Each is mentioned in passing, never linked, run, or pointed at — so this is either a "
                "stale reference or prose about a file the reader would write. Only you can tell which. "
                "(Preflight)",
                missing)
    if not claims:
        # Same class as gate 4's missing premise: there was nothing of this
        # kind to resolve, which is not the same as having resolved it.
        return (NOTCHECK, "No bundled-file references to verify.%s" % tail,
                "This checks only paths the skill claims to ship. Runtime and workspace paths "
                "are out of its reach — a cold run is what settles those.", [])
    return ("PASS", "All %d bundled path(s) resolve.%s" % (len(claims), tail), "", [])


CHECKS = {1: gate1, 2: gate2, 3: gate3, 4: gate4, 5: gate5, 6: gate6, 7: gate7}


# --------------------------------------------------------------- evaluate ----

def evaluate(sk, refs=True):
    findings = []
    status, msg, fix = check_description(sk)
    findings.append({"gate": "D", "title": "Upload-safe description",
                     "status": status, "message": msg, "fix": fix})
    if refs:
        status, msg, fix, broken = check_refs(sk)
        findings.append({"gate": "R", "title": "References resolve", "status": status,
                         "message": msg, "fix": fix, "broken": broken})
    for num, title in GATES:
        status, msg, fix = CHECKS[num](sk)
        findings.append({"gate": num, "title": title, "status": status,
                         "message": msg, "fix": fix})
    return findings


def verdict_of(findings):
    """Worst decided status wins. NOT CHECKABLE is not a status the verdict sees.

    A row the lint declined to decide is deliberately absent from both tests
    below, so a skill whose only open rows are undecidable ones reaches PASS.
    That is what makes exit 0 reachable at all: before the third state existed,
    gate 6 returned REVIEW on every input and no run could return 0.
    """
    statuses = {f["status"] for f in findings}
    if "FAIL" in statuses:
        return "FAIL", 1
    if "REVIEW" in statuses:
        return "REVIEW", 2
    return "PASS", 0


# ---------------------------------------------------------------- report -----

# The one question no gate answers. A lint reads files; whether a skill works
# in a fresh session takes a run. It is printed under every verdict, FAIL
# included, so that no verdict -- least of all a PASS -- is read as that run.
NOT_GRADED = ("Not graded: whether the skill works in a fresh session. "
              "The lint reads files; only a run shows what a model does with them.")


def cold_run_step(sk):
    """The run the lint cannot do, written for this skill.

    Names the skill's own trigger when the description or body declares a
    prefix, so the step is one a reader can take as written rather than a
    method to adapt.
    """
    prefix = _declared_prefix(sk["description"] + "\n" + sk["body"])
    task = ("a real task that starts with %s" % _as_code(prefix)) if prefix \
        else "a real request it should fire on"
    return ("Open a session where your own project instructions do not load, install the "
            "skill from its archive, give it %s, and check what it does against what the "
            "skill promises." % task)


def print_report(sk, findings, verdict, quiet=False):
    print("skill_audit — %s" % sk["name"])
    print("           %s" % sk["path"])
    if sk["scripts"]:
        print("           scripts: %s" % ", ".join(sk["scripts"]))
    print()
    counts = {s: 0 for s in STATUSES}
    for f in findings:
        counts[f["status"]] += 1
        badge = f["status"].ljust(BADGE_W)
        print("  [%s] %-26s %s %s" % (f["gate"], f["title"], badge, f["message"]))
        if not quiet and f["fix"] and f["status"] != "PASS":
            print("        -> %s" % f["fix"])
    print()
    print("FAIL %d   REVIEW %d   NOT CHECKABLE %d   PASS %d"
          % (counts["FAIL"], counts["REVIEW"], counts[NOTCHECK], counts["PASS"]))
    print("\nVERDICT: %s" % verdict)
    nc = counts[NOTCHECK]
    if verdict == "FAIL":
        print("At least one gate failed on a detectable anti-pattern. Fix the -> items and re-run.")
    elif verdict == "REVIEW":
        print("No detectable failures. The REVIEW gates need a human ruling or a deeper pass "
              "(a static lint can't settle them). This is the normal result for a decent skill.")
    elif nc:
        # The honest PASS. It says what it covers and, in the same breath, how
        # many rows it does not — because a verdict that hides its own blind
        # spots is the failure mode this whole state was added to prevent.
        print("Every gate the lint can decide came back clean. %s above — read %s."
              % ("One gate it cannot decide is marked NOT CHECKABLE" if nc == 1
                 else "%d gates it cannot decide are marked NOT CHECKABLE" % nc,
                 "its -> line" if nc == 1 else "their -> lines"))
    else:
        # Reachable since gate 6 gained a PASS branch: every row decided and
        # clean. The line below still says what no row covers.
        print("Every gate came back clean.")
    print(NOT_GRADED)
    if not quiet:
        print("        -> %s" % cold_run_step(sk))
    print()


class Parser(argparse.ArgumentParser):
    """argparse exits 2 on a usage error, and 2 is REVIEW here. A mistyped flag
    read as "a gate needs a ruling" is a verdict on nothing, so usage errors
    take a code of their own."""

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, "%s: usage error: %s (exit %d, no verdict)\n"
                  % (self.prog, message, EXIT_USAGE))


def print_refusal(r):
    print("skill_audit: REFUSED %s: %s." % (r["path"], r["reason"]), file=sys.stderr)
    print("        -> %s" % r["fix"], file=sys.stderr)


def main():
    # allow_abbrev off: "--jso" or "--no" is a usage error (exit 4), not a
    # silent --json or --no-refs.
    ap = Parser(add_help=True, allow_abbrev=False, description="Lint a Claude skill against the seven-gate Floor.")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--log-row", action="store_true")
    ap.add_argument("--no-refs", action="store_true",
                    help="skip the reference-resolution preflight")
    args = ap.parse_args()

    collected = collect_skills(args.paths)
    refused = [r for r in collected if r.get("refused")]
    skills = [sk for sk in collected if not sk.get("refused")]
    for r in refused:
        print_refusal(r)
    if not skills:
        sys.exit(EXIT_REFUSED)

    results = []
    for sk in skills:
        findings = evaluate(sk, refs=not args.no_refs)
        verdict, code = verdict_of(findings)
        results.append((sk, findings, verdict, code))

    if args.json:
        out = [{
            "name": sk["name"], "path": sk["path"], "verdict": verdict,
            "scripts": sk["scripts"],
            "broken_refs": [b for f in findings for b in f.get("broken", [])],
            "gates": [{"gate": f["gate"], "title": f["title"], "status": f["status"],
                       "message": f["message"], "fix": f["fix"]} for f in findings],
            "not_graded": {"what": NOT_GRADED, "how": cold_run_step(sk)},
        } for (sk, findings, verdict, code) in results]
        print(json.dumps(out if len(out) > 1 else out[0], indent=2))
    else:
        for i, (sk, findings, verdict, code) in enumerate(results):
            if i:
                print("=" * 60)
            print_report(sk, findings, verdict, quiet=args.quiet)

    if args.log_row:
        print("--- gate log row(s) ---")
        for (sk, findings, verdict, code) in results:
            # Counts first, gate numbers named as gate numbers. The earlier
            # format read "FAIL:4 REVIEW:1/2/3" — gate identifiers that a
            # reader takes for counts, three lines under a summary line that
            # really is counts. Two shapes for one fact is one too many.
            fails = [str(f["gate"]) for f in findings if f["status"] == "FAIL"]
            revs = [str(f["gate"]) for f in findings if f["status"] == "REVIEW"]
            ncs = [str(f["gate"]) for f in findings if f["status"] == NOTCHECK]
            npass = sum(1 for f in findings if f["status"] == "PASS")
            note = "%d FAIL / %d REVIEW / %d NOT CHECKABLE / %d PASS" \
                % (len(fails), len(revs), len(ncs), npass)
            if fails:
                note += "; FAIL at gate %s" % ", ".join(fails)
            if revs:
                note += "; REVIEW at gate %s" % ", ".join(revs)
            if ncs:
                note += "; NOT CHECKABLE at gate %s" % ", ".join(ncs)
            note += (". Static lint; each REVIEW gate needs a human ruling, each "
                     "NOT CHECKABLE gate is one the lint declined to decide, and "
                     "whether the skill works in a fresh session is not graded.")
            print("| %s | %s | %s | %s |"
                  % (date.today().isoformat(), sk["name"], verdict, note))

    # worst outcome across all inputs drives the exit code: any FAIL -> 1,
    # else any refusal -> 3, else any REVIEW -> 2, else 0. A refusal outranks
    # REVIEW and PASS because neither may stand for an input never graded;
    # FAIL outranks it because "script against 1" must still catch every FAIL.
    codes = [code for (_s, _f, _v, code) in results]
    sys.exit(EXIT_FAIL if EXIT_FAIL in codes else EXIT_REFUSED if refused else
             EXIT_REVIEW if EXIT_REVIEW in codes else EXIT_PASS)


if __name__ == "__main__":
    main()
