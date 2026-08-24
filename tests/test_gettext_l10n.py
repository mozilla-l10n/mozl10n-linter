# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""End-to-end tests for the gettext linter (FxA, addons)."""


def lint(run_linter, gettext_project, entries):
    return run_linter("gettext_l10n.py", ["--l10n", gettext_project(entries)])


def test_clean_project_reports_nothing(run_linter, gettext_project):
    entries = [
        ("Hello %(name)s", "Ciao %(name)s"),
        ("Settings", "Impostazioni"),
    ]
    assert lint(run_linter, gettext_project, entries) == ""


def test_placeholder_mismatch(run_linter, gettext_project):
    entries = [("Hello %(name)s", "Ciao %(name)d")]
    assert "Placeholder mismatch" in lint(run_linter, gettext_project, entries)


def test_unescaped_percent_after_a_placeholder(run_linter, gettext_project):
    entries = [
        (
            "Account notifications will now also be sent to %(email)s.",
            "Le notifiche saranno inviate a %(email)s% .",
        )
    ]
    errors = lint(run_linter, gettext_project, entries)
    assert "Malformed placeholder(s)" in errors
    assert "Malformed placeholders: %" in errors


def test_literal_percent_without_placeholders_is_allowed(run_linter, gettext_project):
    entries = [("Save 50% today", "Risparmia il 50% oggi")]
    assert lint(run_linter, gettext_project, entries) == ""


def test_brace_placeholders_do_not_require_escaping(run_linter, gettext_project):
    entries = [("{count} items, 50% off", "{count} elementi, 50% di sconto")]
    assert lint(run_linter, gettext_project, entries) == ""


def test_plural_allowance_uses_the_highest_count(run_linter, gettext_project):
    # Both English forms contain `%(total)` once. Summing them would let a
    # translation using it twice through.
    entries = [
        (
            "One of %(total) files",
            "%(count)s of %(total) files",
            ["Uno di %(total) file su %(total)", "%(count)s di %(total) file"],
        )
    ]
    assert "Malformed placeholders: %(total)" in lint(
        run_linter, gettext_project, entries
    )


def test_plural_form_dropping_a_placeholder_is_allowed(run_linter, gettext_project):
    entries = [
        (
            "One file",
            "%(count)s files",
            ["Un file", "%(count)s file"],
        )
    ]
    assert lint(run_linter, gettext_project, entries) == ""


def test_unknown_placeholder_in_a_plural_form(run_linter, gettext_project):
    entries = [
        (
            "One file",
            "%(count)s files",
            ["Un file", "%(count)s file su %(total)s"],
        )
    ]
    assert "Unknown placeholder(s)" in lint(run_linter, gettext_project, entries)


def test_mismatched_html_elements(run_linter, gettext_project):
    entries = [("Read <b>this</b>", "Leggi <i>questo</i>")]
    assert "Mismatched HTML elements" in lint(run_linter, gettext_project, entries)
