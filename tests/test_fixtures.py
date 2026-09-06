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

CASES = [
    ("examples/before/release-notes", 1, "FAIL"),
    ("examples/after/release-notes", 2, "REVIEW"),
]


def main():
    if not os.path.isfile(CHECKER):
        print("test_fixtures: checker not found at %s" % CHECKER, file=sys.stderr)
        return 2

    failures = 0
    for rel, expected, label in CASES:
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
        if got == expected:
            print("  ok    %-32s exit %d (%s)" % (rel, got, label))
        else:
            failures += 1
            print("  FAIL  %-32s exit %d, expected %d (%s)"
                  % (rel, got, expected, label))
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
