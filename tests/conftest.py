# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Helpers to build throwaway l10n trees and run a linter against them.

Most of the linters' logic lives inside `main()`, so the tests drive them as
the workflow does: build a minimal project, run the script, read the errors
file. Each builder returns the path to pass to `--l10n` (or `--toml`).
"""

import json
import os
import re
import subprocess
import sys

from pathlib import Path
from textwrap import dedent
from xml.sax.saxutils import escape

import polib
import pytest


L10N_DIR = Path(__file__).resolve().parent.parent / "l10n"

XLIFF_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<xliff xmlns="urn:oasis:names:tc:xliff:document:1.2" version="1.2">
  <file original="test" source-language="en" target-language="{locale}" datatype="plaintext">
    <body>
{units}
    </body>
  </file>
</xliff>
"""

ANDROID_TOML = """basepath = "."
locales = ["{locale}"]
[[paths]]
  reference = "res/values/strings.xml"
  l10n = "res/values-{{android_locale}}/strings.xml"
"""


@pytest.fixture
def run_linter(tmp_path):
    """Run a linter script and return the content of its errors file."""

    def run(script, args, exceptions=None):
        dest = tmp_path / "errors.txt"
        dest.unlink(missing_ok=True)
        command = [sys.executable, str(L10N_DIR / script), *args, "--dest", str(dest)]
        if exceptions is not None:
            exceptions_file = tmp_path / "exceptions.json"
            exceptions_file.write_text(json.dumps(exceptions), encoding="utf-8")
            command += ["--exceptions", str(exceptions_file)]

        process = subprocess.run(command, capture_output=True, text=True)
        # An uncaught exception also exits with 1, so the traceback is what
        # tells a crash apart from a lint failure.
        if "Traceback (most recent call last)" in process.stderr:
            raise RuntimeError(f"{script} crashed:\n{process.stdout}\n{process.stderr}")

        # Without `--no-failure`, a linter exits with 1 when it reports
        # errors, and with 0 when it doesn't.
        expected_returncode = 1 if dest.exists() else 0
        if process.returncode != expected_returncode:
            raise RuntimeError(
                f"{script} exited with {process.returncode}, expected "
                f"{expected_returncode}:\n{process.stdout}\n{process.stderr}"
            )
        if not dest.exists():
            return ""

        return dest.read_text(encoding="utf-8")

    return run


@pytest.fixture
def xliff_project(tmp_path):
    """Build `<locale>/test.xliff` from {string_id: (source, target)}."""

    def build(units, locale="it"):
        lines = []
        for string_id, (source, target) in units.items():
            lines.append(f'      <trans-unit id="{escape(string_id)}">')
            lines.append(f"        <source>{escape(source)}</source>")
            if target is not None:
                lines.append(f"        <target>{escape(target)}</target>")
            lines.append("      </trans-unit>")

        locale_dir = tmp_path / locale
        locale_dir.mkdir(parents=True, exist_ok=True)
        (locale_dir / "test.xliff").write_text(
            XLIFF_TEMPLATE.format(locale=locale, units="\n".join(lines)),
            encoding="utf-8",
        )

        return str(tmp_path)

    return build


@pytest.fixture
def android_project(tmp_path):
    """Build an Android project from {string_id: (reference, translation)}.

    A value is either a string, or a {quantity: text} mapping for a plural.
    """

    def build(units, locale="it"):
        def serialize(name, value):
            if isinstance(value, dict):
                items = "\n".join(
                    f'    <item quantity="{quantity}">{escape(text)}</item>'
                    for quantity, text in value.items()
                )
                return f'  <plurals name="{name}">\n{items}\n  </plurals>'

            return f'  <string name="{name}">{escape(value)}</string>'

        def write(directory, index):
            strings = "\n".join(
                serialize(name, values[index])
                for name, values in units.items()
                if values[index] is not None
            )
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "strings.xml").write_text(
                f'<?xml version="1.0" encoding="utf-8"?>\n<resources>\n{strings}\n</resources>\n',
                encoding="utf-8",
            )

        write(tmp_path / "res" / "values", 0)
        write(tmp_path / "res" / f"values-{locale}", 1)
        toml = tmp_path / "l10n.toml"
        toml.write_text(ANDROID_TOML.format(locale=locale), encoding="utf-8")

        return str(toml)

    return build


@pytest.fixture
def gettext_project(tmp_path):
    """Build `<locale>/LC_MESSAGES/messages.po` from a list of entries.

    An entry is (msgid, msgstr), or (msgid, msgid_plural, [msgstr, ...]).
    """

    def build(entries, locale="it"):
        pofile = polib.POFile()
        pofile.metadata = {
            "Content-Type": "text/plain; charset=UTF-8",
            "Plural-Forms": "nplurals=2; plural=(n != 1);",
        }
        for entry in entries:
            if len(entry) == 2:
                msgid, msgstr = entry
                pofile.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
            else:
                msgid, msgid_plural, translations = entry
                pofile.append(
                    polib.POEntry(
                        msgid=msgid,
                        msgid_plural=msgid_plural,
                        msgstr_plural=dict(enumerate(translations)),
                    )
                )

        messages_dir = tmp_path / locale / "LC_MESSAGES"
        messages_dir.mkdir(parents=True, exist_ok=True)
        pofile.save(str(messages_dir / "messages.po"))

        return str(tmp_path)

    return build


@pytest.fixture
def fluent_project(tmp_path):
    """Build `<locale>/test.ftl` from two FTL bodies.

    Fluent entries span several lines (attributes, selectors), so this builder
    takes the file content directly instead of a mapping.
    """

    def build(reference, translation, locale="it", reference_locale="en"):
        for name, content in ((reference_locale, reference), (locale, translation)):
            locale_dir = tmp_path / name
            locale_dir.mkdir(parents=True, exist_ok=True)
            (locale_dir / "test.ftl").write_text(
                f"{dedent(content).strip()}\n", encoding="utf-8"
            )

        # `--l10n` points inside the locales folder: the linter reads the root
        # from `os.path.dirname()`, so the trailing separator matters.
        return f"{tmp_path}{os.sep}"

    return build


@pytest.fixture
def webext_project(tmp_path):
    """Build `<locale>/messages.json` from {string_id: (reference, translation)}."""

    def build(units, locale="it", reference_locale="en"):
        def write(directory, index):
            messages = {}
            for name, values in units.items():
                if values[index] is None:
                    continue
                message = {"message": values[index]}
                # The linter reads the expected placeholders from the
                # reference file, and looks for `$NAME$` in the translation.
                placeholders = re.findall(r"\$([a-zA-Z0-9_@]+)\$", values[index])
                if placeholders:
                    message["placeholders"] = {
                        placeholder.lower(): {"content": "$1"}
                        for placeholder in placeholders
                    }
                messages[name] = message
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "messages.json").write_text(
                json.dumps(messages, indent=2), encoding="utf-8"
            )

        write(tmp_path / reference_locale, 0)
        write(tmp_path / locale, 1)

        return str(tmp_path)

    return build
