# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""End-to-end tests for the WebExtension linter (Relay, VPN extension, MAC)."""


def lint(run_linter, webext_project, units):
    return run_linter(
        "webext_l10n.py", ["--l10n", webext_project(units), "--ref", "en"]
    )


def test_clean_project_reports_nothing(run_linter, webext_project):
    units = {
        "greeting": ("Hello $NAME$", "Ciao $NAME$"),
        "plain": ("Settings", "Impostazioni"),
    }
    assert lint(run_linter, webext_project, units) == ""


def test_missing_placeholder(run_linter, webext_project):
    units = {"greeting": ("Hello $NAME$", "Ciao")}
    assert "Placeholder mismatch in messages.json:greeting" in lint(
        run_linter, webext_project, units
    )


def test_placeholders_are_case_insensitive(run_linter, webext_project):
    units = {"greeting": ("Hello $NAME$", "Ciao $name$")}
    assert lint(run_linter, webext_project, units) == ""


def test_ellipsis_and_pilcrow(run_linter, webext_project):
    units = {
        "ellipsis": ("Loading…", "Caricamento..."),
        "pilcrow": ("Search", "Cerca¶"),
    }
    errors = lint(run_linter, webext_project, units)
    assert "'...' in messages.json:ellipsis" in errors
    assert "'¶' in messages.json:pilcrow" in errors
