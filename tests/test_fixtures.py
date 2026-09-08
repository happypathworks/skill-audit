#!/usr/bin/env python3
"""
test_fixtures.py — the shipped regression test for skill_audit.py.

Runs the checker against the two bundled worked-example fixtures and asserts
the exit code each one is supposed to produce. It needs no external corpus and
no arguments: clone the repo, run this, get a verdict.

    examples/before/release-notes   must exit 1 (FAIL)   — Gate 4 is a real
                                    anti-pattern and must stay detected.
    examples/after/release-notes    must exit 2 (REVIEW) — the repaired skill
                                    must NOT trip a false-positive FAIL.
    examples/refs/broken            must exit 1 (FAIL)   — the reference
                                    preflight must still catch a bundled path
                                    that is not there, while leaving the
                                    workspace paths beside it alone.
    examples/refs/intact            must exit 2 (REVIEW) — the same skill with
                                    the path repaired must come back clean.

The second assertion is the one that matters. A lint that fails good input
loses a stranger's trust on first contact, and there is no second contact.

    exit 0   both fixtures returned their expected code
    exit 1   at least one did not — the checker regressed
    exit 2   setup error (checker or fixture missing)

Note: this is not the same gate as _tools/skill_audit_acceptance.py, which
tests for false positives against a large external known-good corpus supplied
by path. That one stays out of the shipped product by design. This one is
small, bundled, and runnable by anyone who downloaded the repo.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CHECKER = os.path.join(ROOT, "skill_audit.py")

# (path, expected exit code, label, expected preflight status or None)
# The fourth field asserts the [R] preflight line directly. Exit code alone is
# not enough: a gate FAIL elsewhere would mask a preflight that stopped firing,
# and a check that silently never fires is worse than no check.
CASES = [
    ("examples/before/release-notes", 1, "FAIL", None),
    ("examples/after/release-notes", 2, "REVIEW", None),
    ("examples/refs/broken", 1, "FAIL", "FAIL"),
    ("examples/refs/intact", 2, "REVIEW", "PASS"),
]


def main():
    if not os.path.isfile(CHECKER):
        print("test_fixtures: checker not found at %s" % CHECKER, file=sys.stderr)
        return 2

    failures = 0
    for rel, expected, label, ref_status in CASES:
        path = os.path.join(ROOT, rel)
        if not os.path.isdir(path):
            print("test_fixtures: fixture missing at %s" % path, file=sys.stderr)
            return 2

        # text=True would decode the child's output with the parent's locale
        # encoding, which is not necessarily the encoding the child wrote in
        # (a Windows console under a legacy code page is the case that bites).
        # This test grades exit codes; it must never die decoding the output it
        # only echoes on failure. So: decode explicitly, and never strictly.
        proc = subprocess.run(
            [sys.executable, CHECKER, path],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        got = proc.returncode
        ref_line = next((l for l in proc.stdout.splitlines() if "[R]" in l), "")
        ref_got = next((s for s in ("FAIL", "REVIEW", "PASS") if s in ref_line), None)
        bad = got != expected or (ref_status is not None and ref_got != ref_status)

        if not bad:
            extra = "" if ref_status is None else ", preflight %s" % ref_got
            print("  ok    %-32s exit %d (%s%s)" % (rel, got, label, extra))
        else:
            failures += 1
            if got != expected:
                print("  FAIL  %-32s exit %d, expected %d (%s)"
                      % (rel, got, expected, label))
            else:
                print("  FAIL  %-32s preflight %s, expected %s"
                      % (rel, ref_got, ref_status))
            for line in proc.stdout.splitlines():
                print("        | %s" % line)

    print("")
    if failures:
        print("test_fixtures: %d of %d fixtures returned the wrong exit code."
              % (failures, len(CASES)))
        return 1
    print("test_fixtures: %d/%d ok." % (len(CASES), len(CASES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
