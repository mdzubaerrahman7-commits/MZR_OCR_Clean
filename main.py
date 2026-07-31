#!/usr/bin/env python3
"""Entry point: run `python3 main.py` to process everything in INPUT/."""
import sys

from bond_audit.cli import main

if __name__ == "__main__":
    sys.exit(main())
