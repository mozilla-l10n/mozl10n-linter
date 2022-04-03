#! /usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from pathlib import Path
import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "json_path",
        help="Path to search for JSON files (including subfolders)",
    )
    args = parser.parse_args()

    search_path = Path(args.json_path)
    file_paths = search_path.glob(f"**/*.json")

    issues = {}
    for fn in file_paths:
        try:
            with open(fn) as f:
                exceptions = json.load(f)
        except Exception as e:
            issues[fn] = e

    if issues:
        for fn, issue in issues.items():
            print(f"Error in {fn}: {issue}")
    else:
        print(f"No issues found.")


if __name__ == "__main__":
    main()
