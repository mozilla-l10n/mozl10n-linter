# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from html import unescape
from html.parser import HTMLParser
from typing import Union

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
            key: Union[str, CatchallKey] = key_tuple[0] if key_tuple else "other"
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
