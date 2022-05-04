#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from collections import defaultdict
from configparser import ConfigParser
from fluent.syntax import parse, visitor, serialize
from fluent.syntax.serializer import FluentSerializer
from html.parser import HTMLParser
from pathlib import Path
import argparse
import json
import os
import re
import sys

try:
    from compare_locales import paths
    from compare_locales import parser
except ImportError as e:
    print("FATAL: make sure that dependencies are installed")
    print(e)
    sys.exit(1)


class StringExtraction:
    def __init__(self, l10n_path, search_type, reference_locale):
        """Initialize object."""

        self.translations = defaultdict(dict)

        self.l10n_path = l10n_path
        self.search_type = search_type
        self.reference_locale = reference_locale

    def extractStringsToml(self):
        """Extract strings using TOML configuration."""

        basedir = os.path.dirname(self.l10n_path)
        project_config = paths.TOMLParser().parse(self.l10n_path, env={"l10n_base": ""})
        basedir = os.path.join(basedir, project_config.root)

        reference_cache = {}

        if not project_config.all_locales:
            print("No locales defined in the project configuration.")

        for locale in project_config.all_locales:
            print(f"Extracting strings for locale: {locale}.")
            files = paths.ProjectFiles(locale, [project_config])
            for l10n_file, reference_file, _, _ in files:
                if not os.path.exists(l10n_file):
                    # File not available in localization
                    continue

                if not os.path.exists(reference_file):
                    # File not available in reference
                    continue

                key_path = os.path.relpath(reference_file, basedir)
                try:
                    p = parser.getParser(reference_file)
                except UserWarning:
                    continue
                if key_path not in reference_cache:
                    p.readFile(reference_file)
                    reference_cache[key_path] = set(p.parse().keys())
                    self.translations[self.reference_locale].update(
                        (
                            f"{key_path}:{entity.key}",
                            entity.raw_val,
                        )
                        for entity in p.parse()
                    )

                p.readFile(l10n_file)
                self.translations[locale].update(
                    (
                        f"{key_path}:{entity.key}",
                        entity.raw_val,
                    )
                    for entity in p.parse()
                )
            print(f"  {len(self.translations[locale])} strings extracted")

    def extractLocale(self, locale, base_dir):
        """Extract strings for a locale"""

        # Normalize locale code
        normalized_locale = locale.replace("_", "-")
        for relative_file in self.file_list:
            file_name = os.path.join(base_dir, locale, relative_file)
            if not os.path.exists(file_name):
                continue
            file_extension = os.path.splitext(file_name)[1]

            file_parser = parser.getParser(file_extension)
            file_parser.readFile(file_name)
            try:
                entities = file_parser.parse()
                for entity in entities:
                    # Ignore Junk
                    if isinstance(entity, parser.Junk):
                        continue
                    string_id = f"{relative_file}:{entity}"
                    if file_extension == ".ftl":
                        if entity.raw_val is not None:
                            self.translations[normalized_locale][
                                string_id
                            ] = entity.raw_val
                        # Store attributes
                        for attribute in entity.attributes:
                            attr_string_id = f"{relative_file}:{entity}.{attribute}"
                            self.translations[normalized_locale][
                                attr_string_id
                            ] = attribute.raw_val
                    else:
                        self.translations[normalized_locale][string_id] = entity.raw_val
            except Exception as e:
                print(f"Error parsing file: {file_name}")
                print(e)

        # Remove extra strings from locale
        if self.reference_locale != locale:
            for string_id in list(self.translations[normalized_locale].keys()):
                if string_id not in self.translations[self.reference_locale]:
                    del self.translations[normalized_locale][string_id]

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
            l for l in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, l))
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

        return self.translations


class MyHTMLParser(HTMLParser):
    def __init__(self):
        self.clear()
        super().__init__(convert_charrefs=True)

    def clear(self):
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)

    def handle_endtag(self, tag):
        self.tags.append(tag)

    def get_tags(self):
        self.tags.sort()

        # Remove line breaks
        self.tags = [t for t in self.tags if t != "br"]

        return self.tags


class flattenSelectExpression(visitor.Transformer):
    def visit_SelectExpression(self, node):
        for variant in node.variants:
            if variant.default:
                default_variant = variant
                break

        node.variants = [default_variant]

        return node


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

        datal10n_pattern = re.compile(
            'data-l10n-name\s*=\s*"([a-zA-Z\-]*)"', re.UNICODE
        )

        placeable_pattern = re.compile(
            '(?<!\{)\{\s*([\$|-]?[A-Za-z0-9._-]+)(?:[\[(]?[A-Za-z0-9_\-, :"]+[\])])*\s*\}'
        )

        # Load exceptions
        if not self.exceptions_path:
            exceptions = {}
        else:
            exceptions_filename = os.path.basename(self.exceptions_path)
            try:
                with open(self.exceptions_path) as f:
                    exceptions = json.load(f)
            except Exception as e:
                sys.exit(e)

        """
        Store specific reference strings for addictional FTL checks:
        - Strings with data-l10n-names
        - Strings with message, terms, or variable references
        """
        reference_data = self.translations[self.reference_locale]
        data_l10n_ids = {}
        placeable_ids = {}
        for string_id, text in reference_data.items():
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
        html_parser = MyHTMLParser()
        html_strings = {}
        for string_id, text in reference_data.items():
            if not isinstance(text, str):
                continue

            if "*[" in text:
                resource = parse(f"temp_id = {text}")
                flattener = flattenSelectExpression()
                serializer = FluentSerializer()
                text = serializer.serialize(flattener.visit(resource))

            html_parser.clear()
            html_parser.feed(text)

            tags = html_parser.get_tags()
            if tags:
                html_strings[string_id] = tags

        for locale, locale_translations in self.translations.items():
            # Ignore reference locale
            if locale == self.reference_locale:
                continue

            # General checks on localized strings
            for string_id, translation in locale_translations.items():
                # Ignore excluded strings
                if ignoreString(exceptions, locale, "general", string_id):
                    continue

                translation = locale_translations[string_id]
                if not isinstance(translation, str):
                    continue

                # Check for pilcrow character
                if "¶" in translation:
                    error_msg = f"Pilcrow character in string ({string_id})"
                    self.error_messages[locale].append(error_msg)

                # Check for stray spaces
                if '{ "' in translation:
                    error_msg = (
                        f"Fluent literal in string ({string_id})\n"
                        f"  Translation: {translation}"
                    )
                    self.error_messages[locale].append(error_msg)

                # Check for the message ID repeated in the translation
                message_id = string_id.split(":")[1]
                pattern = re.compile(re.escape(message_id) + "\s*=", re.UNICODE)
                if pattern.search(translation):
                    error_msg = f"Message ID is repeated in string ({string_id})"
                    self.error_messages[locale].append(error_msg)

                # Check for 3 dots instead of ellipsis
                if "..." in translation and not ignoreString(
                    exceptions, locale, "ellipsis", string_id
                ):
                    error_msg = (
                        f"'...' in {string_id}\n" f"  Translation: {translation}"
                    )
                    self.error_messages[locale].append(error_msg)

            # Check for HTML elements mismatch
            html_parser = MyHTMLParser()
            for string_id, ref_tags in html_strings.items():
                # Ignore untranslated strings
                if string_id not in locale_translations:
                    continue

                # Ignore excluded strings
                if ignoreString(exceptions, locale, "HTML", string_id):
                    continue

                translation = locale_translations[string_id]
                if not isinstance(translation, str):
                    continue
                if "*[" in translation:
                    resource = parse(f"temp_id = {translation}")
                    flattener = flattenSelectExpression()
                    serializer = FluentSerializer()
                    translation = serializer.serialize(flattener.visit(resource))

                html_parser.clear()
                html_parser.feed(translation)
                tags = html_parser.get_tags()

                if tags != ref_tags:
                    error_msg = (
                        f"Mismatched HTML elements in string ({string_id})\n"
                        f"  Translation: {translation}\n"
                        f"  Reference: {self.translations[self.reference_locale][string_id]}"
                    )
                    self.error_messages[locale].append(error_msg)

            # Check data-l10n-names
            for string_id, groups in data_l10n_ids.items():
                if string_id not in locale_translations:
                    continue

                # Ignore excluded strings
                if ignoreString(exceptions, locale, "data-l10n-names", string_id):
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
                            f"  Reference: {self.translations[self.reference_locale][string_id]}"
                        )
                        self.error_messages[locale].append(error_msg)
                else:
                    # There are no data-l10n-name
                    error_msg = (
                        f"data-l10n-name missing in string ({string_id})\n"
                        f"  Translation: {translation}\n"
                        f"  Reference: {self.translations[self.reference_locale][string_id]}"
                    )
                    self.error_messages[locale].append(error_msg)

            # Check placeables
            for string_id, groups in placeable_ids.items():
                if string_id not in locale_translations:
                    continue

                # Ignore excluded strings
                if ignoreString(exceptions, locale, "placeables", string_id):
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
                        # Groups are not matching
                        error_msg = (
                            f"Placeable mismatch in string ({string_id})\n"
                            f"  Translation: {translation}\n"
                            f"  Reference: {self.translations[self.reference_locale][string_id]}"
                        )
                        self.error_messages[locale].append(error_msg)
                else:
                    # There are no data-l10n-name
                    error_msg = (
                        f"Placeable missing in string ({string_id})\n"
                        f"  Translation: {translation}\n"
                        f"  Reference: {self.translations[self.reference_locale][string_id]}"
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
        "--toml", nargs="?", dest="toml_path", help="Path to l10n.toml file"
    )
    parser.add_argument(
        "--l10n", nargs="?", dest="l10n_path", help="Path to l10n.toml file"
    )
    parser.add_argument("--ref", dest="reference_code", help="Reference language code")
    parser.add_argument("--dest", dest="dest_file", help="Save output to file")
    parser.add_argument(
        "--exceptions",
        nargs="?",
        dest="exceptions_file",
        help="Path to JSON exceptions file",
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
        sys.exit(1)
    else:
        print("No issues found.")


if __name__ == "__main__":
    main()
