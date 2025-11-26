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
from pathlib import Path

from fluent.syntax import ast, parse, visitor
from fluent.syntax.serializer import FluentSerializer
from functions import get_html_tags, getAllExceptions, parse_file
from moz.l10n.paths import L10nConfigPaths


class StringExtraction:
    def __init__(self, l10n_path, search_type, reference_locale):
        """Initialize object."""

        self.translations = defaultdict(dict)
        self.msg_ids = defaultdict(list)
        self.msg_attributes = defaultdict(dict)

        self.l10n_path = l10n_path
        self.search_type = search_type
        self.reference_locale = reference_locale

    def storeFluentStrings(self, locale, filename, relative_filename):
        try:
            parse_file(filename, self.translations[locale], relative_filename)
        except Exception as e:
            print(f"Error parsing file: {filename}")
            print(e)

    def removeObsoleteStrings(self, locale):
        # Remove obsolete strings from locale
        if locale != self.reference_locale:
            for string_id in list(self.translations[locale].keys()):
                if string_id not in self.translations[self.reference_locale]:
                    del self.translations[locale][string_id]

    def extractStringsToml(self):
        """Extract strings using TOML configuration."""

        if not os.path.exists(self.l10n_path):
            sys.exit("Specified TOML file does not exist.")
        project_config_paths = L10nConfigPaths(self.l10n_path)
        basedir = project_config_paths.base

        locales = list(project_config_paths.all_locales)
        locales.sort()

        if not locales:
            print("No locales defined in the project configuration.")

        read_references = []

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

                # Extract reference strings if not already available
                if ref_file not in read_references:
                    self.storeFluentStrings(
                        self.reference_locale,
                        ref_file,
                        key_path,
                    )

                # Extract localized strings
                self.storeFluentStrings(locale, l10n_file, key_path)

        # Use a second loop to remove obsolete strings, since reference files
        # are not available beforehand.
        for locale in locales:
            self.removeObsoleteStrings(locale)

    def extractLocale(self, locale, base_dir):
        """Extract strings for a locale"""

        # Normalize locale code
        normalized_locale = locale.replace("_", "-")
        for relative_file in self.file_list:
            file_name = os.path.join(base_dir, locale, relative_file)
            if not os.path.exists(file_name):
                continue
            self.storeFluentStrings(normalized_locale, file_name, relative_file)

        # Remove obsolete strings from locale
        self.removeObsoleteStrings(normalized_locale)

    def extractStringsFolder(self):
        """Extract strings searching for FTL files in folders."""

        base_dir = os.path.dirname(self.l10n_path)
        ref_dir = os.path.join(base_dir, self.reference_locale)

        if not os.path.isdir(ref_dir):
            sys.exit(f"Reference folder {ref_dir} does not exist.")

        # Store the list of FTL files, with paths relative to the source folder
        ref_path = Path(ref_dir)
        files = ref_path.glob("**/*.ftl")
        self.file_list = [os.path.relpath(fp, ref_dir) for fp in files]

        # Get a list of subfolders, assume they're locales
        locales = [
            loc
            for loc in os.listdir(base_dir)
            if os.path.isdir(os.path.join(base_dir, loc))
        ]
        locales.remove(self.reference_locale)
        locales.sort()

        # Extract strings for reference locale
        print(f"Extracting strings for reference locale ({self.reference_locale}).")
        self.extractLocale(self.reference_locale, base_dir)
        print(f"  {len(self.translations[self.reference_locale])} strings extracted")

        # Extract strings for other locales
        for locale in locales:
            print(f"Extracting strings for locale: {locale}")
            self.extractLocale(locale, base_dir)
            # Normalize locale code
            normalized_locale = locale.replace("_", "-")
            print(f"  {len(self.translations[normalized_locale])} strings extracted")

    def extractStrings(self):
        """Extract strings from all locales."""

        if self.search_type == "folder":
            self.extractStringsFolder()
        else:
            self.extractStringsToml()

    def getTranslations(self):
        """Return dictionary with translations"""

        return {
            "translations": self.translations,
            "attributes": self.msg_attributes,
            "ids": self.msg_ids,
        }


class flattenSelectExpression(visitor.Transformer):
    def visit_SelectExpression(self, node):
        for variant in node.variants:
            if variant.default:
                default_variant = variant
                break

        node.variants = [default_variant]

        return node


class checkSelectExpression(visitor.Visitor):
    def __init__(self):
        super().__init__()
        self.select_vars = []
        self.msg_vars = []
        self.is_message = True

    def visit_Message(self, node):
        self.is_message = True
        super().generic_visit(node)

    def visit_Term(self, node):
        # No need to check selectExpression in terms
        self.is_message = False

    def visit_SelectExpression(self, node):
        # Store the variable used in the selectExpression
        if (
            isinstance(node.selector, ast.VariableReference)
            and node.selector.id.name not in self.select_vars
            and self.is_message
        ):
            self.select_vars.append(node.selector.id.name)

        for variant in node.variants:
            super().generic_visit(variant.value)

    def visit_VariableReference(self, node):
        # Store the variables used in the message
        if node.id.name not in self.msg_vars and self.is_message:
            self.msg_vars.append(node.id.name)


class QualityCheck:
    def __init__(self, translations, reference_locale, exceptions_path):
        self.translations = translations["translations"]
        self.msg_attributes = translations["attributes"]
        self.msg_ids = translations["ids"]
        self.reference_locale = reference_locale
        self.error_messages = defaultdict(list)

        # Load exceptions
        if not exceptions_path:
            self.exceptions = {}
        else:
            try:
                with open(exceptions_path) as f:
                    self.exceptions = json.load(f)
            except Exception as e:
                sys.exit(e)

        self.runChecks()

    def runChecks(self):
        """Check translations for issues"""

        def ignoreString(locale, errorcode, string_id):
            """Check if a string should be ignored"""

            if not self.exceptions:
                return False

            if errorcode not in self.exceptions:
                return False

            if errorcode == "ellipsis":
                if string_id in self.exceptions[errorcode].get("strings", []):
                    return True
                if locale in self.exceptions[errorcode][
                    "excluded_locales"
                ] or string_id in self.exceptions[errorcode]["locales"].get(locale, {}):
                    return True
            else:
                # Ignore excluded strings
                if string_id in self.exceptions[errorcode]["strings"]:
                    return True
                if (
                    locale in self.exceptions[errorcode]["locales"]
                    and string_id in self.exceptions[errorcode]["locales"][locale]
                ):
                    return True

            return False

        datal10n_pattern = re.compile(
            r'data-l10n-name\s*=\s*"([a-zA-Z\-]*)"', re.UNICODE
        )

        placeable_pattern = re.compile(
            r'(?<!\{)\{\s*([\$|-]?[\w.-]+)(?:[\[(]?[\w.\-, :"]+[\])])*\s*\}', re.UNICODE
        )

        """
        Store specific reference strings for additional FTL checks:
        - Strings with data-l10n-names
        - Strings with message, terms, or variable references
        """
        reference_data = self.translations[self.reference_locale]

        # Check if there are obsolete exceptions
        exception_ids = getAllExceptions(self.exceptions)
        for id in exception_ids:
            if id not in reference_data:
                print(f"Obsolete exception: {id}")

        data_l10n_ids = {}
        placeable_ids = {}
        for string_id, string_data in reference_data.items():
            text = string_data["value"]
            file_id, message_id = string_id.split(":")

            if not isinstance(text, str):
                continue

            matches_iterator = datal10n_pattern.finditer(text)
            matches = []
            for m in matches_iterator:
                matches.append(m.group(1))
            if matches:
                # Remove duplicates
                matches = list(set(matches))
                data_l10n_ids[string_id] = sorted(matches)

            matches_iterator = placeable_pattern.finditer(text)
            matches = []
            for m in matches_iterator:
                matches.append(m.group(1))
            if matches:
                # Remove duplicates
                matches = list(set(matches))
                placeable_ids[string_id] = sorted(matches)

        # Store strings with HTML elements
        html_strings = {}
        for string_id, string_data in reference_data.items():
            text = string_data["value"]
            if not isinstance(text, str):
                continue

            if "*[" in text:
                resource = parse(f"temp_id = {text}")
                flattener = flattenSelectExpression()
                serializer = FluentSerializer()
                text = serializer.serialize(flattener.visit(resource))

            # Remove Fluent placeables before parsing HTML, because the parser
            # will consider curly parentheses and other elements as starting
            # tags.
            cleaned_text = placeable_pattern.sub("", text)
            tags = get_html_tags(cleaned_text)
            if tags:
                html_strings[string_id] = tags

        # Check missing or additional attributes in messages
        ref_msg_attributes = self.msg_attributes[self.reference_locale]
        ref_msg_attributes_ids = list(ref_msg_attributes.keys())
        for locale, l10n_msg_attributes in self.msg_attributes.items():
            # Ignore reference locale
            if locale == self.reference_locale:
                continue

            for string_id, ref_string_msg_attributes in ref_msg_attributes.items():
                # Ignore untranslated strings. We compare against translations,
                # not msg_attributes, in case the translated string doesn't have
                # any attribute.
                if string_id not in self.msg_ids[locale]:
                    continue

                l10n_string_msg_attributes = l10n_msg_attributes.get(string_id, [])
                missing_attributes = list(
                    set(ref_string_msg_attributes) - set(l10n_string_msg_attributes)
                )
                if missing_attributes:
                    missing_list = ", ".join(missing_attributes)
                    error_msg = (
                        f"Missing attributes in string ({string_id}): {missing_list}"
                    )
                    self.error_messages[locale].append(error_msg)

                extra_attributes = list(
                    set(l10n_string_msg_attributes) - set(ref_string_msg_attributes)
                )
                if extra_attributes:
                    extra_list = ", ".join(extra_attributes)
                    error_msg = (
                        f"Extra attributes in string ({string_id}): {extra_list}"
                    )
                    self.error_messages[locale].append(error_msg)

            # Check if there are strings in locale with attributes that have
            # none in the reference locale.
            l10n_msg_attributes_ids = list(l10n_msg_attributes.keys())
            extra_attributes = list(
                set(l10n_msg_attributes_ids) - set(ref_msg_attributes_ids)
            )
            for string_id in extra_attributes:
                attributes_list = ", ".join(l10n_msg_attributes[string_id])
                error_msg = (
                    f"Extra attributes in string ({string_id}): {attributes_list}"
                )
                self.error_messages[locale].append(error_msg)

        for locale, locale_translations in self.translations.items():
            # Ignore reference locale
            if locale == self.reference_locale:
                continue

            # Ignore excluded locales
            if (
                "excluded_locales" in self.exceptions
                and locale in self.exceptions["excluded_locales"]
            ):
                continue

            # General checks on localized strings
            for string_id, string_data in locale_translations.items():
                translation = string_data["value"]
                # Ignore excluded strings
                if ignoreString(locale, "general", string_id):
                    continue

                translation = locale_translations[string_id]
                if not isinstance(translation, str):
                    continue

                # Check for pilcrow character
                if "¶" in translation:
                    error_msg = f"Pilcrow character in string ({string_id})"
                    self.error_messages[locale].append(error_msg)

                # Check for empty translation, or translations with just line
                # breaks
                if "".join(translation.splitlines()) == "":
                    reference_string = reference_data.get(string_id, "")
                    error_msg = (
                        f"{string_id} is empty\n"
                        f"  Translation: {translation}\n"
                        f"  Reference: {reference_string}"
                    )
                    self.error_messages[locale].append(error_msg)

                # Check for stray spaces
                if '{ "' in translation and not ignoreString(
                    locale, "fluent-literal", string_id
                ):
                    error_msg = (
                        f"Fluent literal in string ({string_id})\n"
                        f"  Translation: {translation}"
                    )
                    self.error_messages[locale].append(error_msg)

                # Check for the message ID repeated in the translation
                message_id = string_id.split(":")[1]
                pattern = re.compile(re.escape(message_id) + r"\s*=", re.UNICODE)
                if pattern.search(translation):
                    error_msg = f"Message ID is repeated in string ({string_id})"
                    self.error_messages[locale].append(error_msg)

                # Check for 3 dots instead of ellipsis
                if "..." in translation and not ignoreString(
                    locale, "ellipsis", string_id
                ):
                    error_msg = f"'...' in {string_id}\n  Translation: {translation}"
                    self.error_messages[locale].append(error_msg)

                # If it's a selectExpression, check if the variable used in
                # selector matches one of the placeables.
                if "*[" in translation and not ignoreString(
                    locale, "select", string_id
                ):
                    l10n_select = checkSelectExpression()
                    ref_select = checkSelectExpression()
                    serializer = FluentSerializer()
                    message_id = string_id.split(":")[1]
                    l10n_select.visit(parse(f"{message_id} = {translation}"))
                    reference_string = reference_data.get(string_id, "")
                    ref_select.visit(parse(f"{message_id} = {reference_string}"))

                    for select_var in l10n_select.select_vars:
                        # The select var should be used in the source string,
                        # either in the selector or in one of the variants
                        acceptable_vars = ref_select.msg_vars + ref_select.select_vars
                        if select_var not in acceptable_vars:
                            error_msg = (
                                f"'${select_var}' is used in a selectExpression for {string_id} but it's not available in the source string\n"
                                f"  Translation: {translation}\n"
                                f"  Reference: {reference_string}\n"
                            )
                            self.error_messages[locale].append(error_msg)

            # Check all localized strings for HTML elements mismatch or extra tags
            for string_id, string_data in locale_translations.items():
                translation = string_data["value"]
                # Ignore excluded strings
                if ignoreString(locale, "HTML", string_id):
                    continue

                if not isinstance(translation, str):
                    continue
                if "*[" in translation:
                    resource = parse(f"temp_id = {translation}")
                    flattener = flattenSelectExpression()
                    serializer = FluentSerializer()
                    translation = serializer.serialize(flattener.visit(resource))

                cleaned_translation = placeable_pattern.sub("", translation)
                tags = get_html_tags(cleaned_translation)

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
                        f"  Reference: {reference_data[string_id]}"
                    )
                    self.error_messages[locale].append(error_msg)

            # Check data-l10n-names
            for string_id, groups in data_l10n_ids.items():
                if string_id not in locale_translations:
                    continue

                # Ignore excluded strings
                if ignoreString(locale, "data-l10n-names", string_id):
                    continue

                translation = locale_translations[string_id]
                if not isinstance(translation, str):
                    continue
                matches_iterator = datal10n_pattern.finditer(translation)
                matches = []
                for m in matches_iterator:
                    matches.append(m.group(1))
                # Remove duplicates
                matches = list(set(matches))
                if matches:
                    translated_groups = sorted(matches)
                    if translated_groups != groups:
                        # Groups are not matching
                        error_msg = (
                            f"data-l10n-name mismatch in string ({string_id})\n"
                            f"  Translation: {translation}\n"
                            f"  Reference: {reference_data[string_id]}"
                        )
                        self.error_messages[locale].append(error_msg)
                else:
                    # There are no data-l10n-name
                    error_msg = (
                        f"data-l10n-name missing in string ({string_id})\n"
                        f"  Translation: {translation}\n"
                        f"  Reference: {reference_data[string_id]}"
                    )
                    self.error_messages[locale].append(error_msg)

            # Check placeables
            for string_id, groups in placeable_ids.items():
                if string_id not in locale_translations:
                    continue

                # Ignore excluded strings
                if ignoreString(locale, "placeables", string_id):
                    continue

                translation = locale_translations[string_id]
                if not isinstance(translation, str):
                    continue
                matches_iterator = placeable_pattern.finditer(translation)
                matches = []
                for m in matches_iterator:
                    matches.append(m.group(1))
                # Remove duplicates
                matches = list(set(matches))
                if matches:
                    translated_groups = sorted(matches)
                    if translated_groups != groups:
                        missing_placeables = ", ".join(list(set(groups) - set(matches)))
                        additional_placeables = ", ".join(
                            list(set(matches) - set(groups))
                        )
                        extra_msg = ""
                        extra_msg += (
                            f"  Missing: {missing_placeables}\n"
                            if missing_placeables != ""
                            else ""
                        )
                        extra_msg += (
                            f"  Additional: {additional_placeables}\n"
                            if additional_placeables != ""
                            else ""
                        )
                        # Groups are not matching
                        error_msg = (
                            f"Placeable mismatch in string ({string_id})\n"
                            f"{extra_msg}"
                            f"  Translation: {translation}\n"
                            f"  Reference: {reference_data[string_id]}"
                        )
                        self.error_messages[locale].append(error_msg)
                else:
                    # There are no data-l10n-name
                    error_msg = (
                        f"Placeable missing in string ({string_id})\n"
                        "  Missing: " + ", ".join(groups) + "\n"
                        f"  Translation: {translation}\n"
                        f"  Reference: {reference_data[string_id]}"
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
            excluded_locales = self.exceptions.get("excluded_locales", [])
            excluded_locales.sort()
            if excluded_locales:
                excluded_locales = ", ".join(excluded_locales)
                output.append(f"Excluded locales: {excluded_locales}")

        return output


def main():
    # Read command line input parameters
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--toml", nargs="?", dest="toml_path", help="Path to l10n.toml file"
    )
    parser.add_argument(
        "--l10n",
        nargs="?",
        dest="l10n_path",
        help="Path to folder including folders for each locale",
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

    if not args.toml_path and not args.l10n_path:
        sys.exit("It's necessary to specify one between --toml and --l10n parameters")

    search_type = "toml" if args.toml_path else "folder"
    l10n_path = args.toml_path if args.toml_path else args.l10n_path

    extracted_strings = StringExtraction(
        l10n_path=l10n_path,
        search_type=search_type,
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
