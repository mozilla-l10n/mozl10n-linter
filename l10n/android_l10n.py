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

from functions import (
    get_html_tags,
    get_malformed_placeables,
    getAllExceptions,
    parse_file,
)
from moz.l10n.paths import L10nConfigPaths, get_android_locale


# Java formatter syntax: %[index$][flags][width][.precision]conversion, e.g.
# `%s`, `%1$s`, `%,d`, `%.2f`, `%03d`. The `-` and `0` flags require a width
# (`%0d` and `%-d` throw MissingFormatWidthException), so they only appear in
# the first alternative. The space flag is left out on purpose: it would turn
# any text with a percent sign followed by a word (`100% done`) into a
# placeable.
placeable_pattern = re.compile(
    r"((%)(\d+\$)?(?:[-#+0,(]*[1-9][0-9]*|[#+,(]*)(?:\.[0-9]+)?([dfs]))"
)
# Keep malformed-candidate detection specific to Android. The generic printf
# marker also treats width-plus-letter sequences as format-like, which can
# mistake percent-encoded text such as `%20World` for a malformed placeable.
# Here, an otherwise ambiguous candidate is only considered malformed when it
# ends in one of Android's supported conversions. `$` and `@` remain
# unambiguous syntax markers.
android_candidate_pattern = re.compile(
    r"%(?:\d+\$)?[-#+0,(]*[0-9]*(?:\.[0-9]+)?(?:hh|h|ll|l|q|z|t|j)?[a-zA-Z@]?[$@]*"
)
android_marker_pattern = re.compile(r"[$@]|[dfs]$")


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

        def mask_url_percent_escapes(text):
            """Hide percent-encoded bytes in URL-like, whitespace-delimited text."""
            masked = list(text)
            for escape in re.finditer(r"%[0-9A-Fa-f]{2}", text):
                # `%%20` is how a literal percent sign is written in a format
                # string, so the escape is already correct: masking it would
                # hide the `%%` from the malformed check.
                if escape.start() > 0 and text[escape.start() - 1] == "%":
                    continue

                # A percent escape encodes a character that can't be written
                # as is, never a control character. `%02d` in a URL is a
                # formatter with a width, not an encoded STX.
                if int(escape.group()[1:], 16) < 0x20:
                    continue

                token_start = (
                    max(
                        text.rfind(separator, 0, escape.start())
                        for separator in " \t\r\n\"'"
                    )
                    + 1
                )
                token_end_match = re.search(r"[\s\"']", text[escape.end() :])
                token_end = (
                    escape.end() + token_end_match.start()
                    if token_end_match
                    else len(text)
                )
                token = text[token_start:token_end]
                # A bare slash isn't enough to assume a URL: `d` and `f` are
                # hex digits, so `%02d/%02d` would be masked, and the string
                # would silently lose all of its placeables.
                if "://" in token or token.startswith("www."):
                    masked[escape.start()] = "％"

            return "".join(masked)

        def get_malformed_android_placeables(text):
            return get_malformed_placeables(
                mask_url_percent_escapes(text),
                placeable_pattern,
                candidate_pattern=android_candidate_pattern,
                marker_pattern=android_marker_pattern,
            )

        def get_placeable_matches(text):
            """Return matches, excluding percent escapes inside URL-like tokens."""
            return list(placeable_pattern.finditer(mask_url_percent_escapes(text)))

        def get_placeable_groups(text, is_plural=False):
            """Return raw placeables and canonical argument/specification pairs."""
            original = []
            canonical = []
            # Each variant of a plural is a separate format string, stored on
            # its own line. The implicit argument index restarts on each of
            # them, otherwise it ends up encoding the number of plural forms
            # of the locale, which legitimately differs from the reference.
            segments = text.split("\n") if is_plural else [text]
            for segment in segments:
                next_implicit_index = 1
                for match in get_placeable_matches(segment):
                    raw = match.group(1)
                    explicit_index = match.group(3)
                    if explicit_index:
                        argument_index = int(explicit_index[:-1])
                        specification = f"%{raw[1 + len(explicit_index) :]}"
                    else:
                        argument_index = next_implicit_index
                        next_implicit_index += 1
                        specification = raw
                    original.append(raw)
                    canonical.append((argument_index, specification))

            return {"original": sorted(original), "canonical": canonical}

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

            matches = get_placeable_groups(
                text, string_data.get("android_plural", False)
            )
            if matches["original"]:
                placeable_ids[string_id] = matches

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

            reported_placeable_ids = set()

            # General checks on localized strings
            for string_id, string_data in locale_translations.items():
                translation = string_data["value"]
                # Ignore excluded strings
                if ignoreString(exceptions, locale, "general", string_id):
                    continue

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
                ignore_placeables = ignoreString(
                    exceptions, locale, "placeables", string_id
                )
                extra_placeables = (
                    get_placeable_matches(translation)
                    and string_id not in placeable_ids
                    and not ignore_placeables
                )
                if extra_placeables:
                    error_msg = (
                        f"Extra placeables in {string_id}\n"
                        f"  Translation: {translation}\n"
                        f"  Reference: {reference}"
                    )
                    self.error_messages[locale].append(error_msg)
                    reported_placeable_ids.add(string_id)

                # Check for malformed placeables, e.g. `%1$s$` instead of
                # `%1$s`.
                if not extra_placeables and not ignore_placeables:
                    malformed = Counter(
                        get_malformed_android_placeables(translation)
                    ) - Counter(get_malformed_android_placeables(reference))
                    if malformed:
                        error_msg = (
                            f"Malformed placeables in {string_id}\n"
                            f"  Malformed placeables: {', '.join(sorted(malformed.elements()))}\n"
                            f"  Translation: {translation}\n"
                            f"  Reference: {reference}"
                        )
                        self.error_messages[locale].append(error_msg)
                        reported_placeable_ids.add(string_id)

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
                if string_id in reported_placeable_ids:
                    continue

                translation = locale_translations[string_id]["value"]
                reference = (
                    self.translations[self.reference_locale]
                    .get(string_id, {})
                    .get("value", None)
                )
                if not isinstance(translation, str):
                    continue
                is_plural = locale_translations[string_id].get("android_plural", False)
                matches = get_placeable_groups(translation, is_plural)

                if matches["original"]:
                    # Compare argument identities independently from display
                    # order, so `%s: %d` and `%2$d: %1$s` match, while the
                    # unindexed and unsafe `%d: %s` does not.
                    if Counter(matches["canonical"]) == Counter(groups["canonical"]):
                        continue

                    # If it's plural, treats them as sets (remove duplicates)
                    if is_plural:
                        if set(matches["canonical"]) == set(groups["canonical"]):
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
