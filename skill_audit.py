#!/usr/bin/env python3
"""
skill_audit.py — mechanical lint of a Claude skill against the seven-gate Floor.

This is the lint, not the verdict. It is decisive only where a machine can be
precise: it FAILs on an explicitly-declared hard-fail with no check behind it,
a countable constraint asserted without verification, a scope boundary that
says "try to stay in scope" instead of naming an exit, and context the file
does not contain. Everything softer — whether the trigger is a prefix or a
description, whether an example is present and genuinely *deciding*, whether
the one-sentence gap is *true*, whether the skill survives a cold run — comes
back REVIEW for a human, because presence is not quality and a regex cannot
settle it. This tool reports what it can see honestly and never pretends to
judge more than it can.

USAGE
    python skill_audit.py <path> [<path> ...] [options]

    <path>          a skill directory (containing SKILL.md), a SKILL.md file,
                    or a folder of skills (each in its own subdirectory).

    --json          machine-readable output
    --no-refs       skip the reference-resolution preflight
    --quiet         suppress per-gate evidence, print the gate line + verdict
    --log-row       emit a markdown row for a build-notes gate log

EXIT CODES
    0   PASS    every gate passed. Note: Gate 6 (cold handoff) cannot be
                settled by a static lint, so a clean run tops out at REVIEW
                unless every other gate passes AND Gate 6 is waived. In
                practice a lint result is a REVIEW at best — that is honest,
                not a defect. Only a cold-run ablation can raise it to PASS.
    2   REVIEW  no failures, but at least one gate needs a human ruling or a
                deeper pass. This is the normal result for a decent skill.
    1   FAIL    at least one gate failed on a high-precision anti-pattern: an
                explicitly-declared hard-fail with no backing check, a countable
                constraint with no verification, a soft-only scope exit, or
                context the file does not contain -- or the preflight found a
                file the skill says it ships and does not. Fix and re-run.
    3   ERROR   nothing gradable was found at the given path(s).

THE [R] PREFLIGHT
    Before the Floor, one integrity check: every path the skill claims to ship
    must exist. It runs first because a skill pointing at a file that is not
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

WHAT THIS IS NOT
    It does not rewrite your skill. It diagnoses and points; fixing is your
    pass, or the skill-creator's. It grades Claude Agent Skills (a SKILL.md,
    optionally with sibling scripts), not loose prompts or code repositories.
"""

import argparse
import json
import os
import re
import sys
from datetime import date

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
    (6, "Survives cold handoff"),
    (7, "Deciding example"),
]

STATUSES = ("FAIL", "REVIEW", "PASS")  # worst-first, for verdict ordering

SCRIPT_EXT = {".py", ".sh", ".js", ".ts", ".rb", ".pl", ".ps1", ".bat"}


# -------------------------------------------------------------- load skill ---

def find_skill_md(directory):
    for name in os.listdir(directory):
        if name.lower() == "skill.md":
            return os.path.join(directory, name)
    return None


def parse_frontmatter(text):
    """Return (frontmatter_dict, body). Naive YAML: enough for name/description."""
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    raw, body = m.group(1), m.group(2)
    fm, key, buf = {}, None, []
    for line in raw.splitlines():
        top = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if top and not line.startswith((" ", "\t")):
            if key is not None:
                fm[key] = " ".join(b.strip() for b in buf).strip()
            key = top.group(1).lower()
            buf = [top.group(2)]
        else:
            buf.append(line)
    if key is not None:
        fm[key] = " ".join(b.strip() for b in buf).strip()
    # strip YAML folding markers left in values
    for k, v in fm.items():
        fm[k] = re.sub(r"^[>|][-+]?\s*", "", v).strip().strip('"').strip("'")
    return fm, body


def load_skill(path):
    """Return a skill dict, or None if nothing gradable is here."""
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

    with open(md, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    fm, body = parse_frontmatter(text)

    scripts = []
    try:
        for name in os.listdir(skill_dir):
            full = os.path.join(skill_dir, name)
            if os.path.isfile(full) and os.path.splitext(name)[1].lower() in SCRIPT_EXT:
                scripts.append(name)
    except OSError:
        pass

    name = fm.get("name") or os.path.basename(skill_dir) or os.path.basename(md)
    return {
        "path": md,
        "dir": skill_dir,
        "name": name,
        "description": fm.get("description", ""),
        "body": body,
        "full": text,
        "scripts": scripts,
    }


def collect_skills(paths):
    """Expand paths into a list of skill dicts (supports a folder of skills)."""
    found, seen = [], set()

    def add(sk):
        if sk and sk["path"] not in seen:
            seen.add(sk["path"])
            found.append(sk)

    for p in paths:
        sk = load_skill(p)
        if sk:
            add(sk)
            continue
        if os.path.isdir(p):
            for child in sorted(os.listdir(p)):
                cd = os.path.join(p, child)
                if os.path.isdir(cd):
                    add(load_skill(cd))
    return found


# ------------------------------------------------------------ detectors ------

def has(patterns, text, flags=re.IGNORECASE):
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            return m
    return None


GAP_MARKERS = [
    r"does\s?n'?t?\s+survive", r"\bwithout this\b", r"\bwithout the skill\b",
    r"\bthe base model\b", r"\bleft alone\b", r"\bfrom memory\b",
    r"\bthe gap\b", r"\bthe failure mode\b", r"\botherwise\b[^.\n]{0,60}\b(wrong|fails?|breaks?|drift|miss)",
    r"\b(forget|forgets|skip|skips|fudge|fudges|confabulate|confabulates|drift|drifts)\b",
    r"\bgets? (?:this )?wrong\b", r"\binconsistent(?:ly)?\b",
]

# a deterministic entry: a prefix/condition, not a keyword pile
PREFIX_TOKEN = r"`[A-Za-z][\w-]*[:/]`"
ENTRY_MARKERS = [
    PREFIX_TOKEN,
    r"\bprimary trigger is\b", r"\bhard trigger\b", r"\bdeterministic (?:entry|trigger)\b",
    r"\bany message beginning with\b", r"\bmessages? (?:that )?(?:begin|start)(?:s|ning)? with\b",
    r"\bstarts? with\b[^.\n]{0,30}`", r"\bwhen the user types\b",
    r"\btreat (?:any message|the prefix)\b",
]
KEYWORD_TRIGGER_MARKERS = [
    r"\buse when\b", r"\buse this (?:skill )?when\b", r"\btrigger(?:s)? (?:on|include)\b",
    r"\bkeywords?\b", r"\btriggers include\b",
]

# hard-fail claims. An explicit token is decisive on its own; imperative rule
# phrasing ("you must", "never <verb>", "always <verb>") is counted, and two or
# more with no backing check is the prose-hard-fail anti-pattern.
HARDFAIL_EXPLICIT = [r"hard[\s-]?fail", r"\bhard[\s-]?stop\b", r"\brefuse and\b", r"\b→\s*refuse\b"]
IMPERATIVE_RULE = [
    r"\byou must\b", r"\bmust not\b", r"\bmust never\b", r"\bmust always\b",
    r"\bmust\s+\w+", r"\bshall not\b", r"\bnever\s+\w+", r"\balways\s+\w+",
    r"\bdo not\s+\w+", r"\bdon'?t\s+\w+", r"\brefuse\b", r"\breject\b", r"\babort\b",
]
ENFORCEMENT_MARKERS = [
    r"\bexit code\b", r"\bnon-?zero\b", r"\breturns? \d", r"\.py\b", r"\.sh\b",
    r"\brun (?:the )?(?:check|script|audit|linter?)\b", r"```(?:bash|sh|python|console)",
    r"\bthe check (?:returns|fails|passes)\b", r"\bverif(?:y|ies|ied) (?:with|by running)\b",
]

# verify-before-voice
CONSTRAINT_MARKERS = [
    r"\bcharacter count\b", r"\bchar(?:acter)? limit\b", r"\bword count\b",
    r"\bexactly \d", r"\bno more than \d",
    # a length spec, not a stray "(1-2 words)" aside: require a limiting word
    r"\b(?:under|over|at most|at least|up to|within|max|min|no fewer than|limit(?:ed)? to)\s+\d+\s*(?:characters?|chars?|words?)\b",
    r"\bspec(?:ification)?\b", r"\bmust match\b", r"\bcountable\b",
]
VERIFY_MARKERS = [
    r"\bverif(?:y|ies|ied|ication)\b", r"\bcount (?:and|then) (?:confirm|check|verify)\b",
    r"\bbefore (?:emitting|responding|the response|you (?:respond|write))\b",
    r"\bconfirm(?:s|ed)? (?:the|each|every)\b", r"\bre-?run\b", r"\bcheck (?:the )?(?:count|output|result)\b",
    r"\bmeasure(?:d|s)? (?:the|it)\b",
]

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
]
SOFT_SCOPE_MARKERS = [
    r"\btry to stay\b", r"\bshould (?:not|avoid)\b", r"\bavoid\b", r"\btry (?:not )?to\b",
    r"\bbe careful\b", r"\bwhere possible\b",
]

# cold-handoff killers: references to context the file does not contain
CONTEXT_LEAK_MARKERS = [
    r"\bas (?:we )?discussed\b", r"\bper our\b", r"\bas (?:above|before) in (?:this|the) (?:chat|thread|conversation)\b",
    r"\byou already know\b", r"\blike (?:last time|before)\b", r"\bearlier in (?:this|the) (?:chat|thread)\b",
    r"\bas established (?:above|earlier)\b",
]

# worked example
EXAMPLE_MARKERS = [
    r"^#+\s+.*\bexamples?\b", r"\bworked example\b", r"\bwalkthrough\b",
    r"^\s*(?:Input|User|Prompt|Output)\s*:", r"\bfor (?:example|instance)\b",
    r"\*\*example\b", r"^\s*(?:Example|Ex\.)\s*\d", r"\be\.g\.\b",
    r"\bhere'?s (?:an|a) example\b", r"\bsample (?:input|output|run|skill|call)\b",
]
CATCH_MARKERS = [
    r"\bcatch(?:es|ing)?\b", r"\bcaught\b", r"\bwould otherwise\b", r"\bgets? (?:it )?wrong\b",
    r"\binstead of\b", r"\bmistake\b", r"\btrap\b", r"\bgotcha\b", r"\bbefore\b.*\bafter\b",
    r"\bfails?\b", r"\bthe bad case\b", r"\bnaive\b", r"\bna(?:ï|i)ve\b",
]


# ------------------------------------------------------------ gate checks ----

def gate1(sk):
    text = sk["description"] + "\n" + sk["body"]
    if has(GAP_MARKERS, text):
        return "PASS", "A gap/failure-mode statement is present.", \
            "Confirm it names one specific thing the base model gets wrong — not a vague benefit."
    return "REVIEW", "No gap statement detected.", \
        "State in one sentence what the base model gets wrong or does inconsistently without this skill."


def gate2(sk):
    text = sk["description"] + "\n" + sk["body"]
    if has(ENTRY_MARKERS, text):
        return "PASS", "A deterministic entry (prefix or unambiguous condition) is present.", ""
    if has(KEYWORD_TRIGGER_MARKERS, text):
        return "REVIEW", "Entry is description/keyword-based — the ecosystem norm, but not a deterministic trigger.", \
            "This fires semantically and can mis-trigger on adjacent requests. A hard trigger (a prefix like `foo:` " \
            "or an unambiguous condition) makes entry predictable; keyword lists can supplement it. Optional, not required. (Gate 2)"
    return "REVIEW", "No trigger mechanism detected at all.", \
        "Declare how the skill fires — a deterministic entry (a prefix or unambiguous condition) is the most predictable."


def _count(patterns, text):
    return sum(1 for pat in patterns if re.search(pat, text, re.IGNORECASE))


def gate3(sk):
    text = sk["body"]
    explicit = bool(has(HARDFAIL_EXPLICIT, text))
    imperatives = _count(IMPERATIVE_RULE, text)
    enforced = bool(sk["scripts"]) or has(ENFORCEMENT_MARKERS, text)
    if not explicit and imperatives == 0:
        return "REVIEW", "No hard-fails declared.", \
            "If this skill has a constraint that must always hold, name it as a hard-fail and back it with a check."
    if enforced:
        detail = ("ships a script (%s)" % ", ".join(sk["scripts"])) if sk["scripts"] \
            else "references a mechanical check"
        return "PASS", "Hard-fails are present and the skill %s." % detail, \
            "Confirm every claimed hard-fail is actually covered by a check — a lint can't map claim to check."
    if explicit:
        return "FAIL", "A hard-fail is explicitly declared but asserted in prose with no backing check.", \
            "A hard-fail that lives in a sentence is a suggestion. Back each with a check that returns a real " \
            "signal (exit code, count, diff) before the skill emits. (Gate 3)"
    return "REVIEW", "Rule-like imperatives are present but no explicit hard-fail is declared or enforced.", \
        "If any of these must always hold, name it as a hard-fail and back it with a check rather than leaving it as prose."


def gate4(sk):
    text = sk["body"]
    constraints = has(CONSTRAINT_MARKERS, text)
    verify = has(VERIFY_MARKERS, text)
    if not constraints:
        return "PASS", "No countable/spec'd constraint detected; gate not applicable.", \
            "If the skill does have a hard constraint (a count, a spec), make sure it's verified, not asserted."
    if verify:
        return "PASS", "A hard constraint is present and a verification step is described.", ""
    return "FAIL", "A countable/spec'd constraint is present but no verification step was detected.", \
        "Write the output around a verified result — run the check first, then speak. (Gate 4)"


def gate5(sk):
    text = sk["body"]
    scope = has(SCOPE_MARKERS, text)
    named = has(NAMED_EXIT_MARKERS, text, flags=re.IGNORECASE | re.MULTILINE)
    if scope and named:
        return "PASS", "Scope boundaries name an explicit exit (if X, refuse and do Y).", ""
    if scope and not named:
        return "FAIL", "Scope language is present but the exit is soft.", \
            "Replace 'try to stay in scope' with 'if X, refuse and do Y' — a named action, not an intention. (Gate 5)"
    return "REVIEW", "No scope boundary detected.", \
        "Confirm the skill can't be pulled out of scope, or add a boundary with a named exit."


def gate6(sk):
    leak = has(CONTEXT_LEAK_MARKERS, sk["body"])
    if leak:
        return "FAIL", "The skill refers to context it does not contain (%r)." % leak.group(0), \
            "A cold reader won't have that. Move the procedure into the skill so it survives a fresh thread. (Gate 6)"
    return "REVIEW", "Cold-handoff survival can't be settled by a static lint.", \
        "Prove it by running the skill in a clean context on a fixture (an ablation) and comparing the result."


def gate7(sk):
    text = sk["body"]
    example = has(EXAMPLE_MARKERS, text, flags=re.IGNORECASE | re.MULTILINE)
    catch = has(CATCH_MARKERS, text)
    if example and catch:
        return "PASS", "A worked example is present and shows a catch, not just the happy path.", ""
    if example and not catch:
        return "REVIEW", "An example is present but reads like a happy path.", \
            "Confirm at least one example shows the skill catching a case that would otherwise go wrong. (Gate 7)"
    return "REVIEW", "No example detected by the lint — it may present usage in a form the lint can't read (e.g. code recipes).", \
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
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


INTERPRETERS = {"python", "python3", "python2", "py", "node", "deno", "bun",
                "bash", "sh", "zsh", "ruby", "perl", "pwsh", "powershell"}


def _ref_tokens(body):
    """Path-shaped tokens from code spans, fenced blocks and link targets.

    Yields (token, invoked) — invoked is True when the token is being executed
    (an interpreter immediately before it, or a ./ prefix). Bare prose is not
    collected: a filename in running text is a mention, not a reference.
    """
    spans = [m.group(1).split() for m in INLINE_CODE.finditer(body)]
    spans += [m.group(1).split() for m in FENCED_CODE.finditer(body)]
    spans += [[m.group(1)] for m in MD_LINK.finditer(body)]

    out = []
    for span in spans:
        for i, raw in enumerate(span):
            tok = raw.strip().rstrip(REF_TRAILING).replace("\\", "/")
            invoked = tok.startswith("./") or (i and span[i - 1].lower() in INTERPRETERS)
            tok = tok[2:] if tok.startswith("./") else tok
            if not tok or REF_REJECT.search(tok) or not os.path.splitext(tok)[1]:
                continue
            out.append((tok, invoked))
    return out


def _bundle_refs(sk):
    """Split the token pool into (bundle claims, skipped workspace paths)."""
    try:
        entries = os.listdir(sk["dir"])
    except OSError:
        return [], []
    dirs = {e for e in entries if os.path.isdir(os.path.join(sk["dir"], e))}

    # Fold duplicates first, ORing the invoked flag: a script named in prose
    # and run in a code block is invoked. Classifying on first sight instead
    # would let the earlier, weaker mention decide.
    order, invoked_any = [], {}
    for tok, invoked in _ref_tokens(sk["body"]):
        if tok not in invoked_any:
            order.append(tok)
        invoked_any[tok] = invoked_any.get(tok, False) or invoked

    claims, skipped = [], []
    for tok in order:
        invoked = invoked_any[tok]
        if "/" in tok:
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
    return claims, skipped


def check_refs(sk):
    """Preflight: every path the skill claims to ship must resolve.

    This is an integrity check, not a quality gate. It runs before the Floor
    because a skill pointing at a file that is not there is broken the way a
    build break is broken, and no gate below can see it.
    """
    claims, skipped = _bundle_refs(sk)
    missing = [t for t in claims
               if not os.path.exists(os.path.normpath(os.path.join(sk["dir"], t)))]
    tail = (" (%d workspace path(s) skipped — not this skill's to resolve)" % len(skipped)) if skipped else ""

    if missing:
        shown = ", ".join(missing[:6]) + (" ..." if len(missing) > 6 else "")
        return ("FAIL",
                "%d of %d bundled path(s) do not exist: %s%s" % (len(missing), len(claims), shown, tail),
                "A file the skill says it ships and does not is a skill that breaks on first run, "
                "and no gate below can see it. Fix the path or ship the file. (Preflight)",
                missing)
    if not claims:
        return ("PASS", "No bundled-file references to verify.%s" % tail,
                "This checks only paths the skill claims to ship. Runtime and workspace paths "
                "are out of its reach — a cold run is what settles those.", [])
    return ("PASS", "All %d bundled path(s) resolve.%s" % (len(claims), tail), "", [])


CHECKS = {1: gate1, 2: gate2, 3: gate3, 4: gate4, 5: gate5, 6: gate6, 7: gate7}


# --------------------------------------------------------------- evaluate ----

def evaluate(sk, refs=True):
    findings = []
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
    statuses = {f["status"] for f in findings}
    if "FAIL" in statuses:
        return "FAIL", 1
    if "REVIEW" in statuses:
        return "REVIEW", 2
    return "PASS", 0


# ---------------------------------------------------------------- report -----

def print_report(sk, findings, verdict, quiet=False):
    print("skill_audit — %s" % sk["name"])
    print("           %s" % sk["path"])
    if sk["scripts"]:
        print("           scripts: %s" % ", ".join(sk["scripts"]))
    print()
    counts = {s: 0 for s in STATUSES}
    for f in findings:
        counts[f["status"]] += 1
        badge = f["status"].ljust(6)
        print("  [%s] %-26s %s %s" % (f["gate"], f["title"], badge, f["message"]))
        if not quiet and f["fix"] and f["status"] != "PASS":
            print("        -> %s" % f["fix"])
    print()
    print("FAIL %d   REVIEW %d   PASS %d" % (counts["FAIL"], counts["REVIEW"], counts["PASS"]))
    print("\nVERDICT: %s" % verdict)
    if verdict == "FAIL":
        print("At least one gate failed on a detectable anti-pattern. Fix the -> items and re-run.")
    elif verdict == "REVIEW":
        print("No detectable failures. The REVIEW gates need a human ruling or a deeper pass "
              "(a static lint can't settle them). This is the normal result for a decent skill.")
    else:
        print("All gates passed the lint. Still worth a cold-run ablation to confirm Gate 6.")
    print()


def main():
    ap = argparse.ArgumentParser(add_help=True, description="Lint a Claude skill against the seven-gate Floor.")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--log-row", action="store_true")
    ap.add_argument("--no-refs", action="store_true",
                    help="skip the reference-resolution preflight")
    args = ap.parse_args()

    skills = collect_skills(args.paths)
    if not skills:
        print("skill_audit: nothing gradable found. Point me at a skill directory "
              "(with a SKILL.md), a SKILL.md file, or a folder of skills.", file=sys.stderr)
        sys.exit(3)

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
            fails = "/".join(str(f["gate"]) for f in findings if f["status"] == "FAIL") or "-"
            revs = "/".join(str(f["gate"]) for f in findings if f["status"] == "REVIEW") or "-"
            print("| %s | %s | %s | FAIL:%s REVIEW:%s | human sign-off required |"
                  % (date.today().isoformat(), sk["name"], verdict, fails, revs))

    # worst verdict across all skills drives the exit code: any FAIL -> 1,
    # else any REVIEW -> 2, else 0.
    codes = [code for (_s, _f, _v, code) in results]
    sys.exit(1 if 1 in codes else (2 if 2 in codes else 0))


if __name__ == "__main__":
    main()
