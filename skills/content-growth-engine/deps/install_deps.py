#!/usr/bin/env python3
"""
Dependency resolver for content-growth-engine (no shell-out — scanner-clean).

`trending_topics.py` needs the `last30days` skill. We do NOT shell out to git
here (that would trip Hermes's scanner). Instead:

  1. If last30days is already installed in ~/.hermes/skills/last30days, done.
  2. Otherwise print the exact Hermes commands to install it from its
     canonical public repo (the proper "install from original repo" path):

         hermes skills tap add mvanhorn/last30days-skill
         hermes skills install last30days

This keeps the skill scanner-clean while still vendoring the dependency from
its original source.
"""
import sys
import shutil
from pathlib import Path

HERMES_SKILLS = Path.home() / ".hermes" / "skills"
LAST30 = HERMES_SKILLS / "last30days"
REPO = "https://github.com/mvanhorn/last30days-skill"


def main():
    if LAST30.exists():
        print(f"✓ last30days already installed at {LAST30}")
        return
    print("⚠ last30days not found. Install it from its original repo:")
    print(f"    hermes skills tap add mvanhorn/last30days-skill")
    print(f"    hermes skills install last30days")
    print(f"  (source: {REPO})")
    print("Then re-run your trending scan. Everything else works without it.")
    sys.exit(2)


if __name__ == "__main__":
    main()
