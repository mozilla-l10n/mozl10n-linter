# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re

from html import unescape
from html.parser import HTMLParser

from moz.l10n.formats import Format
from moz.l10n.message import serialize_message
from moz.l10n.model import (
    CatchallKey,
    Entry,
    Message,
    PatternMessage,
    SelectMessage,
)
from moz.l10n.resource import parse_resource


def getAllExceptions(data, result_set=None):
    if result_set is None:
        result_set = set()

    if isinstance(data, dict):
        for value in data.values():
            getAllExceptions(value, result_set)
    elif isinstance(data, list):
        # If it's all short strings, it's likely a list of locales
        cleaned_data = [i for i in data if len(i) > 6]
        if cleaned_data:
            result_set.update(cleaned_data)

    return result_set


# A candidate placeable is a percent sign, an optional argument index, width,
# precision and length modifier, at most one conversion character, plus any
# trailing `$` or `@`. Text following a complete placeable is not part of the
# candidate, since several locales attach suffixes directly to a placeable
# (e.g. `%@iin` in Finnish).
printf_candidate_pattern = re.compile(r"%[0-9$.]*(?:hh|h|ll|l|q|z|t|j)?[a-zA-Z@]?[$@]*")

# Characters that are part of placeable syntax, and shouldn't be left over
# after a complete placeable.
printf_stray_pattern = re.compile(r"[$@]+")

# A candidate is only reported when it includes one of these characters,
# otherwise it's indistinguishable from a literal percent sign (`50% off`, or
# `%50` in Turkish).
printf_marker_pattern = re.compile(r"[$@]")

# Python format: `%(name)s`. Trailing characters are never treated as strays,
# since a literal `$` can legitimately follow a placeable (`%(price)s$`).
python_candidate_pattern = re.compile(r"%\(?\w*\)?[a-zA-Z]?")
python_marker_pattern = re.compile(r"[(]")


def get_malformed_placeables(
    text: str,
    valid_pattern: re.Pattern,
    candidate_pattern: re.Pattern = printf_candidate_pattern,
    marker_pattern: re.Pattern = printf_marker_pattern,
    stray_pattern: re.Pattern | None = printf_stray_pattern,
    check_percent_escaping: bool = True,
) -> list[str]:
    """Return placeable-like chunks in text that aren't valid placeables.

    Three cases are reported:
    - A valid placeable with leftover placeable characters attached to it,
      e.g. `%2$@$` instead of `%2$@`.
    - A chunk matching candidate_pattern and marker_pattern, but not the
      valid pattern, e.g. `%$@` or `%(count)d`.
    - Any other unescaped percent sign, but only if the text includes at
      least one valid placeable: the text is then a format string, where a
      literal percent sign needs to be escaped as `%%`. In a text without
      placeables, `50% off` or `%50` (Turkish) are perfectly valid.

    The last case, and the special meaning of `%%`, only apply to printf-style
    formats: set check_percent_escaping to False for syntaxes that don't
    escape percent signs, e.g. Qt's `%1`.
    """
    malformed = []
    unescaped = []
    has_placeables = False

    def get_end(match: re.Match) -> int:
        """Return the end of a match, including strays attached to it."""
        stray_match = stray_pattern.match(text, match.end()) if stray_pattern else None
        if not stray_match:
            return match.end()

        # Report the whole malformed chunk, e.g. all of `%2$lld` and not just
        # the `%2$` part that the stray pattern covers.
        candidate = candidate_pattern.match(text, match.start())

        return max(stray_match.end(), candidate.end())

    position = 0
    while (index := text.find("%", position)) != -1:
        if check_percent_escaping and text.startswith("%%", index):
            # An escaped percent sign, unless it's followed by a placeable:
            # in `%%3$@` the escaping swallows the percent sign, and the
            # placeable is lost.
            escaped_match = valid_pattern.match(text, index + 1)
            if not escaped_match:
                position = index + 2
                continue
            position = get_end(escaped_match)
            malformed.append(text[index:position])
            continue

        valid_match = valid_pattern.match(text, index)
        if valid_match:
            has_placeables = True
            position = get_end(valid_match)
            if position != valid_match.end():
                malformed.append(text[index:position])
            continue

        candidate = candidate_pattern.match(text, index).group()
        if marker_pattern.search(candidate):
            malformed.append(candidate)
        else:
            unescaped.append(candidate)
        position = index + max(len(candidate), 1)

    if has_placeables and check_percent_escaping:
        malformed.extend(unescaped)

    return malformed


def parse_file(
    filename: str,
    storage: dict[str, str],
    id_format: str,
) -> None:
    def get_entry_value(value: Message) -> str:
        entry_value = serialize_message(resource.format, value)
        if resource.format == Format.android:
            # In Android resources, unescape quotes
            entry_value = entry_value.replace('\\"', '"').replace("\\'", "'")

        return entry_value

    def serialize_select_variants(entry: Entry) -> str:
        msg: SelectMessage = entry.value
        lines: list[str] = []
        for key_tuple, pattern in msg.variants.items():
            key: str | CatchallKey = key_tuple[0] if key_tuple else "other"
            default = "*" if isinstance(key, CatchallKey) else ""
            label: str | None = key.value if isinstance(key, CatchallKey) else str(key)
            lines.append(
                f"{default}[{label}] {serialize_message(resource.format, PatternMessage(pattern))}"
            )
        return "\n".join(lines)

    try:
        resource = parse_resource(filename, android_literal_quotes=True)

        for section in resource.sections:
            for entry in section.entries:
                if isinstance(entry, Entry):
                    if resource.format == Format.ini:
                        entry_id = ".".join(entry.id)
                    else:
                        entry_id = ".".join(section.id + entry.id)
                    string_id = f"{id_format}:{entry_id}"
                    if entry.properties:
                        # Store the value of an entry with attributes only
                        # if the value is not empty.
                        if not entry.value.is_empty():
                            storage[string_id] = {"value": get_entry_value(entry.value)}
                        for attribute, attr_value in entry.properties.items():
                            attr_id = f"{string_id}.{attribute}"
                            storage[attr_id] = {"value": get_entry_value(attr_value)}
                    else:
                        if resource.format == Format.android:
                            # If it's a plural string in Android, each variant
                            # is stored within the message, following a format
                            # similar to Fluent.
                            if hasattr(entry.value, "variants"):
                                storage[string_id] = {
                                    "value": serialize_select_variants(entry),
                                    "android_plural": True,
                                }
                            else:
                                storage[string_id] = {
                                    "value": get_entry_value(entry.value)
                                }
                        else:
                            storage[string_id] = {"value": get_entry_value(entry.value)}
    except Exception as e:
        print(f"Error parsing file: {filename}")
        print(e)


class MyHTMLParser(HTMLParser):
    def __init__(self):
        self.clear()
        super().__init__(convert_charrefs=True)

    def clear(self):
        self.reset()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        # Ignore specific tags
        if tag not in ["br"]:
            # Order attributes by name
            attributes = sorted(attrs, key=lambda tup: tup[0])

            if attributes:
                attributes_str = ""
                for name, value in attributes:
                    # In Fluent strings like <a { $test }>, curly
                    # parentheses are treated as tags by the parser.
                    if name in ["{", "}"]:
                        continue

                    # Ignore value for localizable attributes
                    if name in ["alt"]:
                        value = "-"
                    attributes_str += (
                        f' {name}="{value}"' if value is not None else f" {name}"
                    )
                tag_str = f"<{tag}{attributes_str}>"
            else:
                tag_str = f"<{tag}>"
            self.tags.append(tag_str)

    def handle_endtag(self, tag):
        if tag not in ["br"]:
            self.tags.append(f"</{tag}>")

    def get_tags(self) -> list[str]:
        return self.tags


def get_html_tags(html: str) -> list[str]:
    html = unescape(html)

    stripper = MyHTMLParser()
    stripper.feed(html)
    return stripper.get_tags()
