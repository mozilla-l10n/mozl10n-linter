#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import json
import os
import re
import sys

from collections import Counter, defaultdict

from functions import get_html_tags, getAllExceptions, parse_file
from moz.l10n.paths import L10nConfigPaths, get_android_locale


class StringExtraction:
    def __init__(self, l10n_path, reference_locale):
        """Initialize object."""

        self.translations = defaultdict(dict)

        self.l10n_path = l10n_path
        self.reference_locale = reference_locale

    def extractStringsToml(self):
        """Extract strings using TOML configuration."""

        if not os.path.exists(self.l10n_path):
            sys.exit("Specified TOML file does not exist.")
        project_config_paths = L10nConfigPaths(
            self.l10n_path, locale_map={"android_locale": get_android_locale}
        )
        basedir = project_config_paths.base
        reference_cache = {}

        locales = list(project_config_paths.all_locales)
        locales.sort()

        if not locales:
            print("No locales defined in the project configuration.")

        all_files = [
            (ref_path, tgt_path)
            for (ref_path, tgt_path), _ in project_config_paths.all().items()
        ]
        for locale in locales:
            print(f"Extracting strings for locale: {locale}.")
            locale_files = [
                (os.path.abspath(ref_path), os.path.abspath(tgt_path))
                for (ref_path, raw_tgt_path) in all_files
                if os.path.exists(
                    tgt_path := project_config_paths.format_target_path(
                        raw_tgt_path, locale
                    )
                )
            ]

            for ref_file, l10n_file in locale_files:
                # Ignore missing files in locale
                if not os.path.exists(l10n_file):
                    # print(f"Ignored missing file for {locale}: {l10n_file}")
                    continue
                # Ignore missing files in reference
                if not os.path.exists(ref_file):
                    print(f"Ignored missing reference file: {ref_file}")
                    continue

                key_path = os.path.relpath(ref_file, basedir)

                # Store content of reference file if it wasn't read yet.
                if key_path not in reference_cache:
                    try:
                        parse_file(
                            ref_file,
                            self.translations[self.reference_locale],
                            f"{key_path}",
                        )
                    except Exception as e:
                        print(f"Error parsing resource: {ref_file}")
                        print(e)

                try:
                    parse_file(
                        l10n_file,
                        self.translations[locale],
                        f"{key_path}",
                    )
                except Exception as e:
                    print(f"Error parsing resource: {l10n_file}")
                    print(e)
            print(f"  {len(self.translations[locale])} strings extracted")

    def extractStrings(self):
        """Extract strings from all locales."""

        self.extractStringsToml()

    def getTranslations(self):
        """Return dictionary with translations"""

        return self.translations


class QualityCheck:
    def __init__(self, translations, reference_locale, exceptions_path):
        self.translations = translations
        self.reference_locale = reference_locale
        self.exceptions_path = exceptions_path
        self.error_messages = defaultdict(list)

        self.runChecks()

    def runChecks(self):
        """Check translations for issues"""

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
                # Ignore excluded strings
                if string_id in exceptions[errorcode]["strings"]:
                    return True
                if (
                    locale in exceptions[errorcode]["locales"]
                    and string_id in exceptions[errorcode]["locales"][locale]
                ):
                    return True

            return False

        placeable_pattern = re.compile(r"((%)(?:\d+\$){0,1}(?:\.\d+)?([dfs]))")

        # Load exceptions
        if not self.exceptions_path:
            exceptions = {}
        else:
            try:
                with open(self.exceptions_path) as f:
                    exceptions = json.load(f)
            except Exception as e:
                sys.exit(e)

        reference_data = self.translations[self.reference_locale]

        # Check if there are obsolete exceptions
        exception_ids = getAllExceptions(exceptions)
        for id in exception_ids:
            if id not in reference_data:
                print(f"Obsolete exception: {id}")

        placeable_ids = {}
        for string_id, string_data in reference_data.items():
            text = string_data["value"]
            if not isinstance(text, str):
                continue

            matches_iterator = placeable_pattern.finditer(text)
            matches = defaultdict(list)
            for m in matches_iterator:
                matches["original"].append(m.group(1))
                if len(m.group()) > 3:
                    # String is using ordered placeables
                    matches["unordered"].append(m.group(2) + m.group(3))
                else:
                    # String is already using unordered placeables
                    matches["unordered"].append(m.group(1))
            if matches:
                placeable_ids[string_id] = {
                    "original": sorted(matches["original"]),
                    "unordered": matches["unordered"],
                }

        # Store strings with HTML elements
        html_strings = {}
        for string_id, string_data in reference_data.items():
            text = string_data["value"]
            if not isinstance(text, str):
                continue

            tags = get_html_tags(text)
            if tags:
                html_strings[string_id] = tags

        for locale, locale_translations in self.translations.items():
            # Ignore reference locale
            if locale == self.reference_locale:
                continue

            # General checks on localized strings
            for string_id, string_data in locale_translations.items():
                translation = string_data["value"]
                # Ignore excluded strings
                if ignoreString(exceptions, locale, "general", string_id):
                    continue

                translation = locale_translations[string_id]
                if not isinstance(translation, str):
                    continue

                # Ignore if it's an obsolete translation not available in the
                # reference file.
                reference = (
                    self.translations[self.reference_locale]
                    .get(string_id, {})
                    .get("value", None)
                )
                if not reference:
                    continue

                # Check for pilcrow character
                if "¶" in translation:
                    error_msg = (
                        f"'¶' in {string_id}\n"
                        f"  Translation: {translation}\n"
                        f"  Reference: {reference}"
                    )
                    self.error_messages[locale].append(error_msg)

                # Check for empty translation, or translations with just line
                # breaks
                if "".join(translation.splitlines()) == "":
                    error_msg = (
                        f"{string_id} is empty\n"
                        f"  Translation: {translation}\n"
                        f"  Reference: {reference}"
                    )
                    self.error_messages[locale].append(error_msg)

                # Check for 3 dots instead of ellipsis
                if "..." in translation and not ignoreString(
                    exceptions, locale, "ellipsis", string_id
                ):
                    error_msg = (
                        f"'...' in {string_id}\n"
                        f"  Translation: {translation}\n"
                        f"  Reference: {reference}"
                    )
                    self.error_messages[locale].append(error_msg)

                # Check if the string has extra placeables
                if (
                    list(placeable_pattern.finditer(translation))
                    and string_id not in placeable_ids
                ):
                    error_msg = (
                        f"Extra placeables in {string_id}\n"
                        f"  Translation: {translation}\n"
                        f"  Reference: {reference}"
                    )
                    self.error_messages[locale].append(error_msg)

            # Check all localized strings for HTML elements mismatch or extra tags
            for string_id, string_data in locale_translations.items():
                # Ignore excluded strings
                if ignoreString(exceptions, locale, "HTML", string_id):
                    continue

                # Ignore if it's an obsolete translation not available in the
                # reference file.
                reference = (
                    self.translations[self.reference_locale]
                    .get(string_id, {})
                    .get("value", None)
                )
                if not reference:
                    continue

                translation = string_data["value"]
                if not isinstance(translation, str):
                    continue

                tags = get_html_tags(translation)

                ref_tags = html_strings.get(string_id, [])
                if tags != ref_tags:
                    # Ignore if only the order was changed
                    if sorted(tags) == sorted(ref_tags):
                        continue

                    # Check extra or missing tags and ignore the error if it's
                    # only <i> and <em>, and the number of extra tags is even.
                    tags_diff = list(Counter(tags) - Counter(ref_tags)) + list(
                        Counter(ref_tags) - Counter(tags)
                    )
                    diff_list = [
                        t
                        for t in tags_diff
                        if t not in ["<em>", "</em>", "<i>", "</i>"]
                    ]
                    if not diff_list and (len(tags_diff) % 2) == 0:
                        continue

                    error_msg = (
                        f"Mismatched HTML elements in string ({string_id})\n"
                        f"  Translation tags ({len(tags)}): {', '.join(tags)}\n"
                        f"  Reference tags ({len(ref_tags)}): {', '.join(ref_tags)}\n"
                        f"  Translation: {translation}\n"
                        f"  Reference: {reference}"
                    )
                    self.error_messages[locale].append(error_msg)

            # Check placeables
            for string_id, groups in placeable_ids.items():
                if string_id not in locale_translations:
                    continue

                # Ignore excluded strings
                if ignoreString(exceptions, locale, "placeables", string_id):
                    continue

                translation = locale_translations[string_id]["value"]
                reference = (
                    self.translations[self.reference_locale]
                    .get(string_id, {})
                    .get("value", None)
                )
                if not isinstance(translation, str):
                    continue
                matches_iterator = placeable_pattern.finditer(translation)
                matches = defaultdict(list)
                for m in matches_iterator:
                    matches["original"].append(m.group(1))
                    if len(m.group()) > 3:
                        # String is using ordered placeables
                        matches["unordered"].append(m.group(2) + m.group(3))
                    else:
                        # String is already using unordered placeables
                        matches["unordered"].append(m.group(1))

                if matches:
                    translated_groups = sorted(matches["original"])
                    if translated_groups != groups["original"]:
                        # Groups are not matching, but the translation might be
                        # using ordered placeables instead of unordered, or
                        # the other way around.
                        # "%1$s" would be stored as "%s" in the "unordered"
                        # array.
                        if matches["unordered"] == groups["unordered"]:
                            continue

                        # If it's plural, treats them as sets (remove duplicates)
                        if locale_translations[string_id].get("android_plural"):
                            if set(matches["unordered"]) == set(groups["unordered"]):
                                continue

                        error_msg = (
                            f"Placeable mismatch in string ({string_id})\n"
                            f"  Translation: {translation}\n"
                            f"  Reference: {reference}"
                        )
                        self.error_messages[locale].append(error_msg)
                else:
                    # There are no placeables
                    error_msg = (
                        f"Placeable missing in string ({string_id})\n"
                        f"  Translation: {translation}\n"
                        f"  Reference: {reference}"
                    )
                    self.error_messages[locale].append(error_msg)

    def printErrors(self):
        """Print error messages"""

        output = []
        total = 0
        if self.error_messages:
            locales = list(self.error_messages.keys())
            locales.sort()

            for locale in locales:
                output.append(
                    f"\nLocale: {locale} ({len(self.error_messages[locale])})"
                )
                total += len(self.error_messages[locale])
                for e in self.error_messages[locale]:
                    output.append(f"\n  {e}")

            output.append(f"\nTotal errors: {total}")

        return output


def main():
    # Read command line input parameters
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--toml", required=True, dest="toml_path", help="Path to l10n.toml file"
    )
    parser.add_argument(
        "--ref", dest="reference_code", help="Reference locale code", default="en-US"
    )
    parser.add_argument("--dest", dest="dest_file", help="Save output to file")
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

    extracted_strings = StringExtraction(
        l10n_path=args.toml_path,
        reference_locale=args.reference_code,
    )
    extracted_strings.extractStrings()
    translations = extracted_strings.getTranslations()

    checks = QualityCheck(translations, args.reference_code, args.exceptions_file)
    output = checks.printErrors()
    if output:
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
