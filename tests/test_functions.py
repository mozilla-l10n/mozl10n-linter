# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Unit tests for the helpers shared by the linters.

The patterns are imported from the linters themselves, so these tests fail if
a grammar changes without the expectations being updated.
"""

import pytest

from android_l10n import (
    android_candidate_pattern,
    android_marker_pattern,
    placeable_pattern as android_pattern,
)
from functions import (
    get_html_tags,
    get_malformed_placeables,
    python_candidate_pattern,
    python_marker_pattern,
)
from gettext_l10n import placeable_pattern as gettext_pattern
from xliff_l10n import placeables_pattern as xliff_pattern


def xliff_malformed(text, check_percent_escaping=True):
    return get_malformed_placeables(
        text, xliff_pattern, check_percent_escaping=check_percent_escaping
    )


def android_malformed(text):
    return get_malformed_placeables(
        text,
        android_pattern,
        candidate_pattern=android_candidate_pattern,
        marker_pattern=android_marker_pattern,
    )


def gettext_malformed(text):
    return get_malformed_placeables(
        text,
        gettext_pattern,
        candidate_pattern=python_candidate_pattern,
        marker_pattern=python_marker_pattern,
        stray_pattern=None,
    )


@pytest.mark.parametrize(
    "text, expected",
    [
        # Leftover placeable characters
        ("%2$@$", ["%2$@$"]),
        ("%1$@@", ["%1$@@"]),
        ("%1$", ["%1$"]),
        ("%$@", ["%$@"]),
        # An escaped percent sign swallowing a placeable
        ("%%3$@$s", ["%%3$@$"]),
        ("%1$@ and %%3$@", ["%%3$@"]),
        # Unsupported conversions and length modifiers
        ("%2$lld", ["%2$lld"]),
        ("Hello %lld", ["%lld"]),
        ("Hello %03g", ["%03g"]),
        ("%1$.2x", ["%1$.2x"]),
        # A literal percent sign in a format string must be escaped
        ("%@ 100% sure", ["%"]),
        ("%@ 100%% sure", []),
        # Valid placeables
        ("%@", []),
        ("%d min", []),
        ("%@ (%d)", []),
        ("%1$.2f", []),
        ("%03d", []),
        ("%-5s", []),
        # A placeable followed by text, common in agglutinative locales
        ("%@iin", []),
        ("%2$@s", []),
        # A literal percent sign outside a format string
        ("Save 50% now", []),
        ("50%off", []),
        ("100%", []),
        ("%50", []),
    ],
)
def test_xliff_malformed_placeables(text, expected):
    assert xliff_malformed(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        # Qt has no escaping for literal percent signs
        ("Kontrol ediliyor (%%1)…", []),
        ("%1 is %50", []),
        ("%1měsíční", []),
        ("Checking (%1%)…", []),
    ],
)
def test_xliff_malformed_placeables_qt(text, expected):
    assert xliff_malformed(text, check_percent_escaping=False) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("%1$s$", ["%1$s$"]),
        ("%@", ["%@"]),
        ("%lld", ["%lld"]),
        # The `-` and `0` flags require a width in Java
        ("%0d", ["%0d"]),
        ("%00d", ["%00d"]),
        ("%-d", ["%-d"]),
        ("%-s", ["%-s"]),
        ("%1$s off 50%", ["%"]),
        # Valid Java formats
        ("%s", []),
        ("%1$s", []),
        ("%,d", []),
        ("%.2f", []),
        ("%03d", []),
        ("%1$03d", []),
        ("%-10s", []),
        ("%+d", []),
        ("%03.2f", []),
        # Literal and percent-encoded text
        ("50% off", []),
        ("100% done", []),
        ("50%off", []),
        ("%%", []),
        ("Hello%20World", []),
    ],
)
def test_android_malformed_placeables(text, expected):
    assert android_malformed(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("%(count)d", ["%(count)d"]),
        ("%(count)", ["%(count)"]),
        ("%(n)s 50%", ["%"]),
        ("%(count)s", []),
        ("{count} items", []),
        # Braces aren't percent formatting, so the percent sign is literal
        ("{n} off 50%", []),
        # A trailing `$` is a currency symbol, not a stray placeable character
        ("%(price)s$", []),
        ("50% off", []),
    ],
)
def test_gettext_malformed_placeholders(text, expected):
    assert gettext_malformed(text) == expected


def test_malformed_placeables_reports_every_occurrence():
    assert xliff_malformed("%1$@$ and %2$@$") == ["%1$@$", "%2$@$"]


@pytest.mark.parametrize(
    "html, expected",
    [
        ("<b>bold</b>", ["<b>", "</b>"]),
        ("plain text", []),
        # `br` is ignored on purpose
        ("one<br>two", []),
        (
            '<a href="https://example.com">link</a>',
            ['<a href="https://example.com">', "</a>"],
        ),
        # Localizable attributes are normalized
        ('<img alt="translated">', ['<img alt="-">']),
    ],
)
def test_get_html_tags(html, expected):
    assert get_html_tags(html) == expected
