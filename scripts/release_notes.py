"""Draft release notes from merged PRs since the last release tag (#138).

The squash-merge history IS the source: one PR = one line, the PR title
is the headline. Prints a draft to stdout; the human edits before
publishing (automation proposes, a person disposes).

    python3 scripts/release_notes.py            # since last tag
    python3 scripts/release_notes.py v0.7.0     # since a specific tag
"""

import os
import subprocess
import sys


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def main():
    since = sys.argv[1] if len(sys.argv) > 1 else None
    if not since:
        # the newest tag reachable from HEAD
        since = sh("git", "describe", "--tags", "--abbrev=0")
        if not since:
            raise SystemExit("no tags found — pass a base tag")
    print(f"# Draft notes — changes since {since}\n")

    ver = sh("git", "describe", "--tags", "--abbrev=0", "HEAD") or "next"
    sh("git", "fetch", "--tags", "-q")
    log = sh("git", "log", f"{since}..HEAD", "--oneline", "--no-merges")
    prs = []
    for line in log.splitlines():
        # squash merges embed the PR number: "title (#123)"
        if "(#" in line:
            title, num = line.rsplit("(#", 1)
            prs.append((title.strip(), num.rstrip(")")))
    if not prs:
        print(f"No merged PRs since {since}.")
        return
    for title, num in prs:
        cat = "Changed"
        t = title.lower()
        if t.startswith(("add", "feat")):
            cat = "Added"
        elif t.startswith(("fix", "correct", "repair")):
            cat = "Fixed"
        elif t.startswith(("remove", "drop", "deprecate")):
            cat = "Removed"
        elif t.startswith(("docs", "doc:")):
            cat = "Docs"
        print(f"- {title} — #{num}   _[{cat}]_")
    print(f"\nCompare: https://github.com/CloudCompile/tonearm/compare/"
          f"{since}...{ver or 'HEAD'}")
    print("# After editing: gh release create <tag> --notes-file <this> "
          "--draft (verify, then publish)")


if __name__ == "__main__":
    main()
