#! /usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import html
import json
import os
import re
import sys

from collections import defaultdict
from glob import glob

from custom_html_parser import get_html_tags
from lxml import etree


def main():
    NS = {"x": "urn:oasis:names:tc:xliff:document:1.2"}

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--l10n",
        required=True,
        dest="locales_path",
        help="Path to folder including subfolders for all locales",
    )
    parser.add_argument(
        "--dest",
        dest="dest_file",
        help="Save output to file",
    )
    parser.add_argument(
        "--exceptions",
        nargs="?",
        dest="exceptions_file",
        help="Path to JSON exceptions file",
    )
    parser.add_argument(
        "--no-failure",
        action=argparse.BooleanOptionalAction,
        default=True,
        dest="exit_error",
        help="If set, the script will exit with 1 in case of errors",
    )
    args = parser.parse_args()

    # Get a list of files to check (absolute paths)
    locales_path = os.path.realpath(args.locales_path)

    file_paths = []
    for xliff_path in glob(locales_path + "/**/*.xliff", recursive=True):
        file_paths.append(xliff_path)

    if not file_paths:
        sys.exit("File not found.")
    else:
        file_paths.sort()

    # Load exceptions
    if not args.exceptions_file:
        exceptions = defaultdict(dict)
    else:
        try:
            with open(args.exceptions_file) as f:
                exceptions = json.load(f)
        except Exception as e:
            sys.exit(e)

    placeables_pattern = re.compile(r"(%[1-9ds]?\$?@|%[1-9])")
    errors = defaultdict(list)

    for file_path in file_paths:
        # Extract and normalize locale code, relative file path
        rel_file_path = os.path.relpath(file_path, args.locales_path)
        locale_folder = rel_file_path.split(os.sep)[0]
        locale = locale_folder.replace("_", "-")
        rel_file_path = rel_file_path.split(locale_folder)[1:][0].lstrip(os.path.sep)

        # Read localized XML file
        try:
            tree = etree.parse(file_path)
            root = tree.getroot()
        except Exception as e:
            print(f"ERROR: Can't parse {file_path}")
            print(e)
            continue

        ignore_ellipsis = locale in exceptions.get("ellipsis", {}).get(
            "excluded_locales", []
        )

        for trans_node in root.xpath("//x:trans-unit", namespaces=NS):
            for child in trans_node.xpath("./x:target", namespaces=NS):
                string_id = f"{rel_file_path}:{trans_node.get('id')}"

                ref_string = trans_node.xpath("./x:source", namespaces=NS)[0].text
                l10n_string = child.text

                # There is a target but it's empty
                if l10n_string is None:
                    continue

                # Check ellipsis
                if not ignore_ellipsis and "..." in l10n_string:
                    if string_id in exceptions.get("ellipsis", {}).get(
                        "locales", {}
                    ).get(locale, []):
                        continue
                    errors[locale].append(
                        f"'...' in {string_id}\n  Translation: {l10n_string}"
                    )

                # Check placeables
                ref_matches = placeables_pattern.findall(ref_string)
                if ref_matches:
                    string_exceptions = exceptions.get("placeables", {}).get(
                        "strings", []
                    )
                    locale_exceptions = (
                        exceptions.get("placeables", {})
                        .get("locales", {})
                        .get(locale, [])
                    )
                    if string_id in locale_exceptions + string_exceptions:
                        continue
                    ref_matches.sort()
                    l10n_matches = placeables_pattern.findall(l10n_string)
                    l10n_matches.sort()

                    if ref_matches != l10n_matches:
                        errors[locale].append(
                            f"Variable mismatch in {string_id}\n"
                            f"  Translation: {l10n_string}\n"
                            f"  Reference: {ref_string}"
                        )

                # Check HTML tags
                ref_tags = get_html_tags(ref_string)
                if ref_tags:
                    if string_id in exceptions.get("HTML", {}).get("locales", {}).get(
                        locale, []
                    ):
                        continue

                    l10n_tags = get_html_tags(l10n_string)

                    if l10n_tags != ref_tags:
                        # Ignore if only the order was changed
                        if sorted(l10n_tags) == sorted(ref_tags):
                            continue
                        errors[locale].append(
                            f"Mismatched HTML elements in string ({string_id})\n"
                            f"  Translation tags ({len(l10n_tags)}): {', '.join(l10n_tags)}\n"
                            f"  Reference tags ({len(ref_tags)}): {', '.join(ref_tags)}\n"
                            f"  Translation: {l10n_string}\n"
                            f"  Reference: {ref_string}"
                        )

                # Check pilcrow
                if "¶" in l10n_string:
                    errors[locale].append(
                        f"'¶' in {string_id}\n  Translation: {l10n_string}"
                    )

                # Check for empty translation, or translations with just line
                # breaks
                if "".join(l10n_string.splitlines()) == "":
                    error_msg = (
                        f"{string_id} is empty\n"
                        f"  Translation: {l10n_string}\n"
                        f"  Reference: {ref_string}"
                    )
                    errors[locale].append(error_msg)

    if errors:
        locales = list(errors.keys())
        locales.sort()

        output = []
        total_errors = 0
        for locale in locales:
            output.append(f"\nLocale: {locale} ({len(errors[locale])})")
            total_errors += len(errors[locale])
            for e in errors[locale]:
                output.append(f"\n  {e}")
        output.append(f"\nTotal errors: {total_errors}")

        out_file = args.dest_file
        if out_file:
            print(f"Saving output to {out_file}")
            with open(out_file, "w") as f:
                f.write("\n".join(output))
        # Print errors anyway on screen
        print("\n".join(output))
        if args.exit_error:
            sys.exit(1)
    else:
        print("No issues found.")


if __name__ == "__main__":
    main()
