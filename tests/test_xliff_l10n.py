# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""End-to-end tests for the XLIFF linter (Firefox for iOS, Focus, VPN)."""


def lint(run_linter, xliff_project, units, exceptions=None):
    return run_linter(
        "xliff_l10n.py", ["--l10n", xliff_project(units)], exceptions=exceptions
    )


def test_clean_project_reports_nothing(run_linter, xliff_project):
    units = {
        "greeting": ("Hello %1$@", "Ciao %1$@"),
        "plain": ("Settings", "Impostazioni"),
    }
    assert lint(run_linter, xliff_project, units) == ""


def test_trailing_dollar_after_placeable(run_linter, xliff_project):
    units = {"notifications": ("Go to %1$@ > %2$@", "Vai a %1$@ > %2$@$")}
    errors = lint(run_linter, xliff_project, units)
    assert "Malformed placeables in test.xliff:notifications" in errors
    assert "Malformed placeables: %2$@$" in errors


def test_escaped_percent_swallowing_a_placeable(run_linter, xliff_project):
    units = {"body": ("Updated %1$@ in %2$@", "Aktualizěrowali %1$@ w %%2$@")}
    assert "Malformed placeables: %%2$@" in lint(run_linter, xliff_project, units)


def test_unsupported_conversion_and_length_modifier(run_linter, xliff_project):
    units = {
        "modifier": ("Hello", "Ciao %lld"),
        "conversion": ("Hello", "Ciao %03g"),
    }
    errors = lint(run_linter, xliff_project, units)
    assert "Malformed placeables: %lld" in errors
    assert "Malformed placeables: %03g" in errors


def test_unescaped_percent_in_a_format_string(run_linter, xliff_project):
    units = {"progress": ("%1$@ is 50%% done", "%1$@ è completo al 50%")}
    assert "Malformed placeables: %" in lint(run_linter, xliff_project, units)


def test_literal_percent_without_placeables_is_allowed(run_linter, xliff_project):
    units = {
        "discount": ("Save 50% today", "Risparmia il 50% oggi"),
        "turkish": ("Save 50% today", "%50 tasarruf edin"),
    }
    assert lint(run_linter, xliff_project, units) == ""


def test_suffix_attached_to_a_placeable_is_allowed(run_linter, xliff_project):
    units = {"sync": ("Sync with %@", "Synkronoi %@iin")}
    assert lint(run_linter, xliff_project, units) == ""


def test_reordering_with_positional_placeables_is_allowed(run_linter, xliff_project):
    units = {"pair": ("%@ on %@", "%2$@ su %1$@")}
    assert lint(run_linter, xliff_project, units) == ""


def test_reordering_without_positional_placeables_is_reported(
    run_linter, xliff_project
):
    units = {"pair": ("%@ has %d tabs", "%d schede in %@")}
    assert "Variable mismatch in test.xliff:pair" in lint(
        run_linter, xliff_project, units
    )


def test_missing_and_extra_placeables(run_linter, xliff_project):
    units = {
        "missing": ("Tabs closed: %d", "Schede chiuse"),
        "extra": ("Settings", "Impostazioni %@"),
    }
    errors = lint(run_linter, xliff_project, units)
    assert "Variable mismatch in test.xliff:missing" in errors
    assert "Extra placeables in test.xliff:extra" in errors


def test_qt_placeable_added_to_a_plain_string_is_ignored(run_linter, xliff_project):
    # A bare `%1` is indistinguishable from a percentage written before the
    # number, so it isn't reported when the reference has no placeables.
    units = {"plain": ("Save 50% today", "%1 tasarruf edin")}
    assert lint(run_linter, xliff_project, units) == ""


def test_qt_string_does_not_require_escaped_percent(run_linter, xliff_project):
    units = {"checking": ("Checking (%1%)…", "Kontrol ediliyor (%%1)…")}
    assert lint(run_linter, xliff_project, units) == ""


def test_ellipsis_pilcrow_and_empty_translation(run_linter, xliff_project):
    units = {
        "ellipsis": ("Loading…", "Caricamento..."),
        "pilcrow": ("Search", "Cerca¶"),
        "empty": ("Search", "\n"),
    }
    errors = lint(run_linter, xliff_project, units)
    assert "'...' in test.xliff:ellipsis" in errors
    assert "'¶' in test.xliff:pilcrow" in errors
    assert "test.xliff:empty is empty" in errors


def test_mismatched_html_elements(run_linter, xliff_project):
    units = {"markup": ("Read <b>this</b>", "Leggi <i>questo</i>")}
    assert "Mismatched HTML elements in string (test.xliff:markup)" in lint(
        run_linter, xliff_project, units
    )


def test_exceptions_suppress_placeable_errors(run_linter, xliff_project):
    units = {"notifications": ("Go to %1$@", "Vai a %1$@$")}
    exceptions = {"placeables": {"strings": ["test.xliff:notifications"]}}
    assert lint(run_linter, xliff_project, units, exceptions) == ""


def test_locale_is_read_from_the_folder_name(run_linter, xliff_project):
    units = {"greeting": ("Hello %@", "Ciao %@$")}
    errors = run_linter("xliff_l10n.py", ["--l10n", xliff_project(units, "zh_TW")])
    assert "Locale: zh-TW" in errors
