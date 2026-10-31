#!/usr/bin/env python3
"""Compare two Observatory raw snapshots and print aggregate differences as JSON.

The builder does this itself when given --previous-raw and stores the result in
the manifest; this CLI is for ad-hoc comparisons. No titles are printed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_muhas_observatory as obs  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("previous", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("--no-api", action="store_true", help="skip re-querying removed works")
    args = parser.parse_args()
    current = list(obs.load_raw(args.current).values())
    print(json.dumps(obs.compare_works(obs.load_raw(args.previous), current, query_api=not args.no_api)))


if __name__ == "__main__":
    main()
