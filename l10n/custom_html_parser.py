#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from html.parser import HTMLParser


class MyHTMLParser(HTMLParser):
    def __init__(self):
        self.clear()
        super().__init__(convert_charrefs=True)

    def clear(self):
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
                    attributes_str += (
                        f' {name}="{value}"' if value != None else f" {name}"
                    )
                tag_str = f"<{tag}{attributes_str}>"
            else:
                tag_str = f"<{tag}>"
            self.tags.append(tag_str)

    def handle_endtag(self, tag):
        if tag not in ["br"]:
            self.tags.append(f"</{tag}>")

    def get_tags(self):

        return self.tags
