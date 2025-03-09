#! /usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import json
import os
import sys

from collections import defaultdict
from pathlib import Path

from jsonschema import Draft7Validator


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "json_path",
        help="Path to search for JSON files (including subfolders)",
    )
    args = parser.parse_args()

    search_path = Path(args.json_path)
    file_paths = search_path.glob("**/*.json")

    schemas_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "schemas"))
    schemas = {
        "firefox_android.json": "android",
        "firefox_ios.json": "xliff",
        "focus_android.json": "android",
        "focus_ios.json": "xliff",
        "fxa_gettext.json": "gettext",
        "fxa.json": "fluent",
        "mac.json": "webextension",
        "monitor.json": "fluent",
        "mozorg.json": "fluent",
        "profiler.json": "fluent",
        "relay_addon.json": "webextension",
        "relay.json": "fluent",
        "translations.json": "webextension",
        "vpn_extension.json": "webextension",
        "vpn.json": "xliff",
    }

    issues = defaultdict(list)
    for fn in file_paths:
        try:
            with open(fn) as f:
                exceptions = json.load(f)
            json_name = os.path.basename(fn)
            if json_name in schemas:
                with open(
                    os.path.join(schemas_path, f"{schemas[json_name]}.json")
                ) as s:
                    schema = json.load(s)
                    v = Draft7Validator(schema)
                    for error in sorted(v.iter_errors(exceptions), key=str):
                        issues[fn].append(error)
        except Exception as e:
            issues[fn].append(e)

    if issues:
        for fn, fn_issues in issues.items():
            for i in fn_issues:
                print(f"Error in {fn}: {i}")
                sys.exit(1)
    else:
        print("No issues found.")


if __name__ == "__main__":
    main()
