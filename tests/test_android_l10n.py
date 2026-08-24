# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""End-to-end tests for the Android linter (Firefox for Android, Focus)."""


def lint(run_linter, android_project, units, exceptions=None):
    return run_linter(
        "android_l10n.py", ["--toml", android_project(units)], exceptions=exceptions
    )


def test_clean_project_reports_nothing(run_linter, android_project):
    units = {
        "greeting": ("Hello %1$s", "Ciao %1$s"),
        "plain": ("Settings", "Impostazioni"),
    }
    assert lint(run_linter, android_project, units) == ""


def test_trailing_dollar_after_placeable(run_linter, android_project):
    units = {"greeting": ("Hello %1$s", "Ciao %1$s$")}
    errors = lint(run_linter, android_project, units)
    assert "Malformed placeables" in errors
    assert "Malformed placeables: %1$s$" in errors


def test_ios_placeable_in_an_android_string(run_linter, android_project):
    units = {"tracker": ("Got 'em! We stopped this site", "잡았다! %@가 사용자를")}
    assert "Malformed placeables: %@" in lint(run_linter, android_project, units)


def test_flags_requiring_a_width(run_linter, android_project):
    # Java throws MissingFormatWidthException for `%0d` and `%-d`.
    units = {"padded": ("Chapter %d", "Capitolo %0d")}
    assert "Malformed placeables: %0d" in lint(run_linter, android_project, units)


def test_valid_java_formats_are_accepted(run_linter, android_project):
    units = {
        "width": ("Chapter %03d", "Capitolo %03d"),
        "grouped": ("%,d files", "%,d file"),
        "precision": ("%.2f MB", "%.2f MB"),
        "justified": ("%-10s", "%-10s"),
        "indexed_width": ("%1$03d of %2$03d", "%1$03d di %2$03d"),
    }
    assert lint(run_linter, android_project, units) == ""


def test_date_like_pattern_keeps_its_placeables(run_linter, android_project):
    # `d` and `f` are hex digits, so a loose URL heuristic masks these as
    # percent escapes. The reference would then look placeable-free, and the
    # placeable dropped by the translation would go unnoticed.
    units = {"date": ("%02d/%02d", "%02d")}
    assert "Placeable mismatch in string" in lint(run_linter, android_project, units)


def test_percent_escape_inside_a_url_is_not_a_placeable(run_linter, android_project):
    # `%2f` in a URL is an encoded slash, not a width-2 float.
    units = {"url": ("Visit https://example.com/a%2fb", "Visita il sito")}
    assert lint(run_linter, android_project, units) == ""


def test_escaped_percent_inside_a_url_is_not_reported(run_linter, android_project):
    # `%%20` is the correct way to write a literal `%20` in a format string.
    units = {"url": ("Open %1$s", "Apri %1$s (https://example.com/a%%20b)")}
    assert lint(run_linter, android_project, units) == ""


def test_reordering_with_positional_placeables_is_allowed(run_linter, android_project):
    units = {"pair": ("%s: %d", "%2$d: %1$s")}
    assert lint(run_linter, android_project, units) == ""


def test_reordering_without_positional_placeables_is_reported(
    run_linter, android_project
):
    units = {"pair": ("%s: %d", "%d: %s")}
    assert "Placeable mismatch in string" in lint(run_linter, android_project, units)


def test_dropped_argument_is_reported(run_linter, android_project):
    # `%1$d out of %2$d` translated using argument 1 twice.
    units = {"progress": ("%1$d out of %2$d", "%1$d ནང་ནས་ %1$d")}
    assert "Placeable mismatch in string" in lint(run_linter, android_project, units)


def test_plural_with_more_forms_than_the_reference(run_linter, android_project):
    # The locale has more plural forms than English, which is not an error:
    # each variant is its own format string.
    units = {
        "trackers": (
            {"one": "%d tracker blocked", "other": "%d trackers blocked"},
            {"one": "%d трэкер", "few": "%d трэкеры", "other": "%d трэкераў"},
        )
    }
    assert lint(run_linter, android_project, units) == ""


def test_plural_form_without_the_placeable(run_linter, android_project):
    units = {
        "downloads": (
            {"one": "Delete file?", "other": "Delete %d files?"},
            {
                "one": "Smazat soubor?",
                "few": "Smazat %d soubory?",
                "other": "Smazat %d souborů?",
            },
        )
    }
    assert lint(run_linter, android_project, units) == ""


def test_plural_with_the_wrong_conversion(run_linter, android_project):
    units = {
        "trackers": (
            {"one": "%d tracker blocked", "other": "%d trackers blocked"},
            {"one": "%s tracker", "other": "%s tracker"},
        )
    }
    assert "Placeable mismatch in string" in lint(run_linter, android_project, units)


def test_extra_placeable_is_reported_once(run_linter, android_project):
    units = {"plain": ("Settings", "Impostazioni %1$s$")}
    errors = lint(run_linter, android_project, units)
    assert "Extra placeables" in errors
    assert "Malformed placeables" not in errors


def test_missing_placeable(run_linter, android_project):
    units = {"greeting": ("Hello %1$s", "Ciao")}
    assert "Placeable missing in string" in lint(run_linter, android_project, units)


def test_ellipsis_and_pilcrow(run_linter, android_project):
    units = {
        "ellipsis": ("Loading…", "Caricamento..."),
        "pilcrow": ("Search", "Cerca¶"),
    }
    errors = lint(run_linter, android_project, units)
    assert "'...' in" in errors
    assert "'¶' in" in errors


def build_exceptions(*string_ids):
    # `ignoreString()` indexes every category directly, so an Android
    # exceptions file has to define all of them, as the template does.
    return {
        "HTML": {"locales": {}, "strings": []},
        "ellipsis": {"excluded_locales": [], "locales": {}},
        "general": {"locales": {}, "strings": []},
        "placeables": {"locales": {}, "strings": list(string_ids)},
    }


def test_exceptions_suppress_malformed_placeables(run_linter, android_project):
    units = {"greeting": ("Hello %1$s", "Ciao %1$s$")}
    exceptions = build_exceptions("res/values/strings.xml:greeting")
    assert lint(run_linter, android_project, units, exceptions) == ""


def test_exceptions_suppress_extra_placeables(run_linter, android_project):
    # The extra-placeables check reads the exceptions separately from the
    # malformed one, so it needs its own coverage.
    units = {"plain": ("Hello", "Ciao %s")}
    assert "Extra placeables" in lint(run_linter, android_project, units)

    exceptions = build_exceptions("res/values/strings.xml:plain")
    assert lint(run_linter, android_project, units, exceptions) == ""


def test_malformed_placeable_is_not_also_reported_as_missing(
    run_linter, android_project
):
    # `%lld` isn't a valid Java placeable, so the translation looks empty of
    # placeables to the mismatch loop: only the malformed error is wanted.
    units = {"count": ("Found %d files", "Trovati %lld file")}
    errors = lint(run_linter, android_project, units)
    assert errors.count("Malformed placeables in") == 1
    assert "Placeable missing in string" not in errors


def test_formatter_inside_a_url_is_still_a_placeable(run_linter, android_project):
    # `%02` decodes to a control character, so it's a formatter that happens
    # to sit in a URL, not a percent escape: dropping it is an error.
    units = {"link": ("https://example.test?n=%02d", "https://example.test")}
    assert "Placeable missing in string" in lint(run_linter, android_project, units)
