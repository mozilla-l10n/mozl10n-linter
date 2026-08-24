#! /usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import json
import os
import re
import sys

from collections import Counter, defaultdict
from glob import glob

from functions import get_html_tags, get_malformed_placeables
from lxml import etree


# Printf-style placeables, e.g. `%@`, `%d`, `%1$@`, `%1$.2f`, `%03d`. The
# conversion characters are limited to the ones actually used in these
# projects: anything else, including length modifiers (`%1$lld`), is reported
# as malformed, and can be added here if it turns out to be legitimate.
# The space flag (`% d`) is left out on purpose: it would turn any text with a
# percent sign followed by a word (`100% sure`) into a placeable.
printf_pattern = re.compile(
    r"%(?:([1-9][0-9]*)\$)?([-+#0]*[0-9]*(?:\.[0-9]+)?)([@dsfu])"
)
# Qt-style placeables, e.g. `%1`. Unlike printf, Qt has no escaping for
# literal percent signs.
qt_pattern = re.compile(r"%([1-9][0-9]*)")
placeables_pattern = re.compile(
    f"(?:{printf_pattern.pattern})|(?:{qt_pattern.pattern})"
)


def get_placeable_groups(text):
    """Return canonical argument/specification pairs, with their syntax."""
    groups = []
    next_implicit_index = 1
    for match in placeables_pattern.finditer(text):
        raw = match.group()
        printf_match = printf_pattern.fullmatch(raw)
        if printf_match:
            explicit_index, formatting, conversion = printf_match.groups()
            if explicit_index:
                argument_index = int(explicit_index)
            else:
                argument_index = next_implicit_index
                next_implicit_index += 1
            specification = f"%{formatting}{conversion}"
            kind = "printf"
        else:
            argument_index = int(qt_pattern.fullmatch(raw).group(1))
            specification = "qt"
            kind = "qt"
        groups.append(
            {
                "canonical": (argument_index, specification),
                "kind": kind,
            }
        )

    return groups


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

    errors = defaultdict(list)

    for file_path in file_paths:
        # Extract and normalize locale code, relative file path. The paths
        # come from `locales_path`, so the relative path has to be computed
        # against it, and not against the raw argument: they differ as soon
        # as there's a symlink in the middle.
        rel_file_path = os.path.relpath(file_path, locales_path)
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
                string_exceptions = exceptions.get("placeables", {}).get("strings", [])
                locale_exceptions = (
                    exceptions.get("placeables", {}).get("locales", {}).get(locale, [])
                )
                ignore_placeables = string_id in locale_exceptions + string_exceptions

                mismatch = False
                ref_groups = get_placeable_groups(ref_string)
                l10n_groups = get_placeable_groups(l10n_string)
                if not ignore_placeables:
                    if ref_groups:
                        ref_canonical = Counter(
                            group["canonical"] for group in ref_groups
                        )
                        l10n_canonical = Counter(
                            group["canonical"] for group in l10n_groups
                        )
                        if ref_canonical != l10n_canonical:
                            mismatch = True
                            errors[locale].append(
                                f"Variable mismatch in {string_id}\n"
                                f"  Translation: {l10n_string}\n"
                                f"  Reference: {ref_string}"
                            )
                    elif any(group["kind"] == "printf" for group in l10n_groups):
                        # The reference has no placeables, so the translation
                        # shouldn't have any either. Only printf-style ones
                        # are reported: a bare `%1` is indistinguishable from
                        # a percentage written before the number (`%50` in
                        # Turkish), which is legitimate in a plain string.
                        mismatch = True
                        errors[locale].append(
                            f"Extra placeables in {string_id}\n"
                            f"  Translation: {l10n_string}\n"
                            f"  Reference: {ref_string}"
                        )

                # Check for malformed placeables, e.g. `%2$@$` instead of
                # `%2$@`. Ignore the ones already present in the reference.
                if not ignore_placeables and not mismatch:
                    # Percent signs are only escaped in printf-style strings,
                    # not in Qt strings. Rely on the syntax used in the
                    # reference to tell them apart.
                    is_printf = any(group["kind"] == "printf" for group in ref_groups)
                    l10n_malformed = get_malformed_placeables(
                        l10n_string,
                        placeables_pattern,
                        check_percent_escaping=is_printf,
                    )
                    ref_malformed = get_malformed_placeables(
                        ref_string,
                        placeables_pattern,
                        check_percent_escaping=is_printf,
                    )
                    malformed = Counter(l10n_malformed) - Counter(ref_malformed)
                    if malformed:
                        errors[locale].append(
                            f"Malformed placeables in {string_id}\n"
                            f"  Malformed placeables: {', '.join(sorted(malformed.elements()))}\n"
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
