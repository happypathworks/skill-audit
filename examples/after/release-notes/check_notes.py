#!/usr/bin/env python3
"""EXAMPLE FIXTURE — the check that makes the 'after' skill's hard-fails real.

Deliberately small. The point of the worked example is not that this script is
sophisticated; it is that the three claims the SKILL.md makes are backed by
something that exits non-zero, instead of being three sentences of prose.

exit 0  every check passed
exit 1  a hard-fail tripped
exit 3  the input is not a changelog (the scope boundary)
"""
import argparse
import re
import sys

BUDGET = 200


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("changelog")
    ap.add_argument("--summary-file")
    ap.add_argument("--version")
    args = ap.parse_args()

    try:
        with open(args.changelog, encoding="utf-8") as fh:
            src = fh.read()
    except OSError as exc:
        print(f"release-notes: cannot read {args.changelog}: {exc}")
        return 3

    if not re.search(r"^##\s+", src, re.M):
        print(f"release-notes: not a changelog at {args.changelog} "
              f"— no '## ' sections. (exit 3)")
        return 3

    failed = False

    if args.version:
        if args.version not in src:
            print(f"  version {args.version!r} not found in {args.changelog}")
            failed = True
        else:
            print(f"  version {args.version!r} found — ok")

    unreleased = re.search(r"^##\s+Unreleased\s*$(.*?)(?=^##\s|\Z)",
                           src, re.M | re.S)
    unreleased_items = []
    if unreleased:
        unreleased_items = [ln.strip("- ").strip()
                            for ln in unreleased.group(1).splitlines()
                            if ln.strip().startswith("-")]

    if args.summary_file:
        try:
            with open(args.summary_file, encoding="utf-8") as fh:
                summary = fh.read().strip()
        except OSError as exc:
            print(f"release-notes: cannot read {args.summary_file}: {exc}")
            return 3

        for item in unreleased_items:
            if item and item.rstrip(".") in summary:
                print(f"  entry {item!r} is under Unreleased")
                failed = True

        count = len(summary)
        status = "ok" if count <= BUDGET else "OVER BUDGET"
        print(f"  summary: {count} / {BUDGET} characters — {status}")
        if count > BUDGET:
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
