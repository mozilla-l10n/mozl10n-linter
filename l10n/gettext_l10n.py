#! /usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import hashlib
import json
import os
import re
import sys

from collections import defaultdict
from pathlib import Path

import polib

from custom_html_parser import MyHTMLParser


def ignoreString(exceptions, locale, errorcode, string_id):
    """Check if a string should be ignored"""

    if not exceptions:
        return False

    if errorcode == "ellipsis":
        if locale in exceptions[errorcode][
            "excluded_locales"
        ] or string_id in exceptions[errorcode]["locales"].get(locale, {}):
            return True
    else:
        if (
            locale in exceptions[errorcode]["locales"]
            and string_id in exceptions[errorcode]["locales"][locale]
        ):
            return True

    return False


def main():
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
    base_path = os.path.realpath(args.locales_path)

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
    placeable_pattern = re.compile(r"%\([a-zA-Z]+\)s")

    # Get a list of locales (subfolders in <locales_path>, exclude hidden folders)
    locales = [
        f
        for f in next(os.walk(base_path))[1]
        if not f.startswith(".") and f not in ["templates", "en", "en_US"]
    ]
    locales.sort()

    html_parser = MyHTMLParser()

    for locale in locales:
        l10n_path = os.path.join(base_path, locale)
        search_path = Path(l10n_path)
        files = search_path.glob("**/*.po")

        # Normalize locale code, e.g. zh_TW => zh-TW
        normalized_locale = locale.replace("_", "-")

        locale_messages = {}
        for f in files:
            pofile = polib.pofile(f)
            for entry in pofile.translated_entries():
                msgid = hashlib.sha256(entry.msgid.encode("utf-8")).hexdigest()

                locale_messages[msgid] = {
                    "reference": entry.msgid,
                    "translation": entry.msgstr,
                }

        # Check for missing placeables
        for message_id, message_data in locale_messages.items():
            reference = message_data["reference"]
            translation = message_data["translation"]

            # Skip if message isn't translated
            if translation == "":
                continue

            # Skip if it's a known exception
            if ignoreString(exceptions, normalized_locale, "placeables", message_id):
                continue

            ref_placeholders = placeable_pattern.findall(reference)
            l10n_placeholders = placeable_pattern.findall(translation)

            if sorted(ref_placeholders) != sorted(l10n_placeholders):
                errors[normalized_locale].append(
                    f"Placeholder mismatch in {message_id}\n"
                    f"  Translation: {translation}\n"
                    f"  Reference: {reference}"
                )

        # Check for HTML tags
        for message_id, message_data in locale_messages.items():
            reference = message_data["reference"]
            translation = message_data["translation"]

            # Skip if message isn't translated
            if translation == "":
                continue

            # Skip if it's a known exception
            if ignoreString(exceptions, normalized_locale, "HTML", message_id):
                continue

            html_parser.clear()
            html_parser.feed(reference)
            ref_tags = html_parser.get_tags()

            html_parser.clear()
            html_parser.feed(translation)
            l10n_tags = html_parser.get_tags()

            if l10n_tags != ref_tags:
                # Ignore if only the order was changed
                if sorted(l10n_tags) == sorted(ref_tags):
                    continue
                errors[normalized_locale].append(
                    f"Mismatched HTML elements in string ({message_id})\n"
                    f"  Translation tags ({len(l10n_tags)}): {', '.join(l10n_tags)}\n"
                    f"  Reference tags ({len(ref_tags)}): {', '.join(ref_tags)}\n"
                    f"  Translation: {translation}\n"
                    f"  Reference: {reference}"
                )

        # General checks
        ignore_ellipsis = normalized_locale in exceptions["ellipsis"].get(
            "excluded_locales", []
        )
        for message_id, translation in locale_messages.items():
            # Skip if message isn't translated
            if translation == "":
                continue

            # Check for pilcrows
            if "¶" in translation:
                errors[normalized_locale].append(
                    f"'¶' in {message_id}\n"
                    f"  Translation: {translation}\n"
                    f"  Reference: {reference}"
                )

            # Check for empty translation
            if translation == "":
                error_msg = (
                    f"{message_id} is empty\n"
                    f"  Translation: {translation}\n"
                    f"  Reference: {reference}"
                )
                errors[normalized_locale].append(error_msg)

            # Check for ellipsis
            if not ignore_ellipsis and "..." in translation:
                if ignoreString(exceptions, normalized_locale, "ellipsis", message_id):
                    continue
                errors[normalized_locale].append(
                    f"'...' in {message_id}\n"
                    f"  Translation: {translation}\n"
                    f"  Reference: {reference}"
                )

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
