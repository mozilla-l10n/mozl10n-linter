#! /usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# This script is largely based on the Fluent Linter used in mozilla-central
# https://firefox-source-docs.mozilla.org/code-quality/lint/linters/fluent-lint.html

import argparse
import os
import bisect
from fluent.syntax import parse, visitor
import re
import sys
import yaml

from html.parser import HTMLParser


class TextElementHTMLParser(HTMLParser):
    """HTML Parser for TextElement.

    TextElements may contain embedded html tags, which can include
    quotes in attributes. We only want to check the actual text.
    """

    def __init__(self):
        super().__init__()
        self.extracted_text = []

    def handle_data(self, data):
        self.extracted_text.append(data)


class Linter(visitor.Visitor):
    """Fluent linter implementation.

    This subclasses the Fluent AST visitor. Methods are called corresponding
    to each type of node in the Fluent AST. It is possible to control
    whether a node is recursed into by calling the generic_visit method on
    the superclass.

    See the documentation here:
    https://www.projectfluent.org/python-fluent/fluent.syntax/stable/usage.html
    """

    def __init__(self, path, root_folder, config, contents, offsets_and_lines):
        super().__init__()
        self.path = path
        self.root_folder = root_folder
        self.config = config
        self.contents = contents
        self.offsets_and_lines = offsets_and_lines

        self.results = []
        self.identifier_re = re.compile(r"[a-z0-9-]+")
        self.apostrophe_re = re.compile(r"\w'")
        self.incorrect_apostrophe_re = re.compile(r"\w\u2018\w")
        self.single_quote_re = re.compile(r"'(.+)'")
        self.double_quote_re = re.compile(r"\".+\"")
        self.ellipsis_re = re.compile(r"\.\.\.")
        self.ids = []
        self.state = {
            # The resource comment should be at the top of the page after the license.
            "node_can_be_resource_comment": True,
            # Group comments must be followed by a message. Two group comments are not
            # allowed in a row.
            "can_have_group_comment": True,
        }

        # Set this to true to debug print the root node's json. This is useful for
        # writing new lint rules, or debugging existing ones.
        self.debug_print_json = False

    def generic_visit(self, node):
        node_name = type(node).__name__
        self.state["node_can_be_resource_comment"] = self.state[
            "node_can_be_resource_comment"
        ] and (
            # This is the root node.
            node_name == "Resource"
            # Empty space is allowed.
            or node_name == "Span"
            # Comments are allowed
            or node_name == "Comment"
        )

        if self.debug_print_json:
            import json

            print(json.dumps(node.to_json(), indent=2))
            # Only debug print the root node.
            self.debug_print_json = False

        super(Linter, self).generic_visit(node)

    def visit_Attribute(self, node):
        # Log errors if attributes are not supported
        if "SY05" in self.config and self.config["SY05"]["disabled"]:
            self.add_error(node, "SY05", "Attributes are not supported.")
            pass
        else:
            # Only visit values for Attribute nodes, the identifier comes from dom.
            super().generic_visit(node.value)

    def visit_FunctionReference(self, node):
        # We don't recurse into function references, the identifiers there are
        # allowed to be free form.
        pass

    def visit_Term(self, node):
        # There must be at least one message or term between group comments.
        self.state["can_have_group_comment"] = True

        # Log errors if terms are not supported
        if "SY01" in self.config and self.config["SY01"]["disabled"]:
            self.add_error(node, "SY01", "Terms are not supported.")

        super().generic_visit(node)

    def visit_Message(self, node):
        # There must be at least one message or term between group comments.
        self.state["can_have_group_comment"] = True

        # Check for duplicates
        if node.id.name in self.ids:
            self.add_error(
                node,
                "MI01",
                f"Identifier {node.id.name} is present more than once in the file.",
            )
        else:
            self.ids.append(node.id.name)

        super().generic_visit(node)

    def visit_MessageReference(self, node):
        # Log errors if message references are not supported
        if "SY02" in self.config and self.config["SY02"]["disabled"]:
            self.add_error(node, "SY02", "Message references are not supported.")

        # We don't recurse into message references, the identifiers are either
        # checked elsewhere or are attributes and come from DOM.

        pass

    def visit_TermReference(self, node):
        # Log errors if term references are not supported
        if "SY03" in self.config and self.config["SY03"]["disabled"]:
            self.add_error(node, "SY03", "Terms are not supported.")
        pass

    def visit_Identifier(self, node):
        if (
            "ID01" in self.config
            and self.config["ID01"]["enabled"]
            and self.path not in self.config["ID01"]["exclusions"]["files"]
            and node.name not in self.config["ID01"]["exclusions"]["messages"]
            and not self.identifier_re.fullmatch(node.name)
        ):
            self.add_error(
                node, "ID01", "Identifiers may only contain lowercase characters and -"
            )

        if (
            "ID02" in self.config
            and self.config["ID02"]["enabled"]
            and len(node.name) < self.config["ID02"]["min_length"]
            and self.path not in self.config["ID02"]["exclusions"]["files"]
            and node.name not in self.config["ID02"]["exclusions"]["messages"]
        ):
            self.add_error(
                node,
                "ID02",
                f"Identifiers must be at least {self.config['ID02']['min_length']} characters long",
            )

    def visit_TextElement(self, node):
        parser = TextElementHTMLParser()
        parser.feed(node.value)
        for text in parser.extracted_text:
            # To check for apostrophes, first remove pairs of straigh quotes
            # used as delimiters.
            cleaned_str = re.sub(self.single_quote_re, "\1", node.value)
            if self.apostrophe_re.search(cleaned_str):
                self.add_error(
                    node,
                    "TE01",
                    "Strings with apostrophes should use foo\u2019s instead of foo's.",
                )
            if self.incorrect_apostrophe_re.search(text):
                self.add_error(
                    node,
                    "TE02",
                    "Strings with apostrophes should use foo\u2019s instead of foo\u2018s.",
                )
            if self.single_quote_re.search(text):
                self.add_error(
                    node,
                    "TE03",
                    "Single-quoted strings should use Unicode \u2018foo\u2019 instead of 'foo'.",
                )
            if self.double_quote_re.search(text):
                self.add_error(
                    node,
                    "TE04",
                    'Double-quoted strings should use Unicode \u201cfoo\u201d instead of "foo".',
                )
            if self.ellipsis_re.search(text):
                self.add_error(
                    node,
                    "TE05",
                    "Strings with an ellipsis should use the Unicode \u2026 character"
                    " instead of three periods",
                )

    def visit_ResourceComment(self, node):
        # This node is a comment with: "###"
        if not self.state["node_can_be_resource_comment"]:
            self.add_error(
                node,
                "RC01",
                "Resource comments (###) should be placed at the top of the file, just "
                "after the license header. There should only be one resource comment "
                "per file.",
            )
            return

        lines_after = get_newlines_count_after(node.span, self.contents)
        lines_before = get_newlines_count_before(node.span, self.contents)

        if node.span.end == len(self.contents) - 1:
            # This file only contains a resource comment.
            return

        if lines_after != 2:
            self.add_error(
                node,
                "RC02",
                "Resource comments (###) should be followed by one empty line.",
            )
            return

        if lines_before != 2:
            self.add_error(
                node,
                "RC03",
                "Resource comments (###) should have one empty line above them.",
            )
            return

    def visit_SelectExpression(self, node):
        # Log errors if variants are not supported
        if node.variants and "SY04" in self.config and self.config["SY04"]["disabled"]:
            self.add_error(node, "SY04", "Variants are not supported.")
            pass
        else:
            # We only want to visit the variant values, the identifiers in selectors
            # and keys are allowed to be free form.
            for variant in node.variants:
                super().generic_visit(variant.value)

    def visit_GroupComment(self, node):
        # This node is a comment with: "##"

        if not self.state["can_have_group_comment"]:
            self.add_error(
                node,
                "GC04",
                "Group comments (##) must be followed by at least one message. Make sure "
                "that a single group comment with multiple pararaphs is not separated by "
                "whitespace, as it will be interpreted as two different comments.",
            )
            return

        self.state["can_have_group_comment"] = False

        lines_after = get_newlines_count_after(node.span, self.contents)
        lines_before = get_newlines_count_before(node.span, self.contents)

        if node.span.end == len(self.contents) - 1:
            # The group comment is the last thing in the file.

            if node.content == "":
                # Empty comments are allowed at the end of the file.
                return

            self.add_error(
                node,
                "GC01",
                "Group comments (##) should not be at the end of the file, they should "
                "always be above a message. Only an empty group comment is allowed at "
                "the end of a file.",
            )
            return

        if lines_after != 2:
            self.add_error(
                node,
                "GC02",
                "Group comments (##) should be followed by one empty line.",
            )
            return

        if lines_before != 2:
            self.add_error(
                node,
                "GC03",
                "Group comments (##) should have an empty line before them.",
            )
            return

    def visit_VariableReference(self, node):
        # We don't recurse into variable references, the identifiers there are
        # allowed to be free form.
        pass

    def add_error(self, node, rule, msg):
        (col, line) = self.span_to_line_and_col(node.span)

        file_path = os.path.relpath(self.path, self.root_folder)
        error_msg = f"""
            File path: {file_path}
            Position: line {line} column {col}
            Error ({rule}): {msg}"""

        self.results.append(error_msg)

    def span_to_line_and_col(self, span):
        i = bisect.bisect_left(self.offsets_and_lines, (span.start, 0))
        if i > 0:
            col = span.start - self.offsets_and_lines[i - 1][0]
        else:
            col = 1 + span.start
        return (col, self.offsets_and_lines[i][1])


def get_offsets_and_lines(contents):
    """Return a list consisting of tuples of (offset, line).

    The Fluent AST contains spans of start and end offsets in the file.
    This function returns a list of offsets and line numbers so that errors
    can be reported using line and column.
    """
    line = 1
    result = []
    for m in re.finditer(r"\n", contents):
        result.append((m.start(), line))
        line += 1
    return result


def get_newlines_count_after(span, contents):
    # Determine the number of newlines.
    count = 0
    for i in range(span.end, len(contents)):
        assert contents[i] != "\r", "This linter does not handle \\r characters."
        if contents[i] != "\n":
            break
        count += 1

    return count


def get_newlines_count_before(span, contents):
    # Determine the range of newline characters.
    count = 0
    for i in range(span.start - 1, 0, -1):
        assert contents[i] != "\r", "This linter does not handle \\r characters."
        if contents[i] != "\n":
            break
        count += 1

    return count


def lint(root_folder, config_path):

    # Get list of FTL files
    root_folder = os.path.abspath(root_folder)
    files = get_file_list(root_folder)

    # Get config, including exclusions
    if config_path:
        config_file = config_path
    else:
        config_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "config.yml"
        )

    # Warn if a config file is provided but missing
    if config_path and not os.path.exists(config_file):
        print(f"Configuration file not found: {config_file}")

    if os.path.exists(config_file):
        with open(config_file) as f:
            config = list(yaml.safe_load_all(f))[0]
    else:
        config = {}

    results = []
    for path in files:
        path = os.path.join(root_folder, path)
        contents = open(path, "r", encoding="utf-8").read()
        linter = Linter(
            path, root_folder, config, contents, get_offsets_and_lines(contents)
        )
        linter.visit(parse(contents))
        results.extend(linter.results)

    return results


def get_file_list(path):
    """Get the list of supported files."""

    file_list = []
    for root, dirs, files in os.walk(path, followlinks=True):
        for file in files:
            if file.endswith(".ftl"):
                file_list.append(os.path.join(root, file))
    file_list.sort()

    return file_list


def main():
    # Read command line input parameters
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "files_path", help="Path to root folder with FTL files for reference locale"
    )
    parser.add_argument(
        "--config",
        help="Path to config file. If not provided, it will be searched in the same path of the script",
    )
    args = parser.parse_args()

    results = lint(args.files_path, args.config)
    if results:
        for r in results:
            print(r)
        sys.exit(1)
    else:
        print("No errors found.")


if __name__ == "__main__":
    main()
