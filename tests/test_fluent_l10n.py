# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""End-to-end tests for the Fluent linter (mozorg, FxA, Monitor, Relay…)."""

import pytest


def lint(run_linter, fluent_project, reference, translation, exceptions=None):
    return run_linter(
        "fluent_l10n.py",
        ["--l10n", fluent_project(reference, translation), "--ref", "en"],
        exceptions=exceptions,
    )


def test_clean_project_reports_nothing(run_linter, fluent_project):
    reference = """
        greeting = Hello { $name }
        save-button =
            .label = Save
            .accesskey = S
    """
    translation = """
        greeting = Ciao { $name }
        save-button =
            .label = Salva
            .accesskey = S
    """
    assert lint(run_linter, fluent_project, reference, translation) == ""


def test_placeable_mismatch(run_linter, fluent_project):
    reference = "greeting = Hello { $name }"
    translation = "greeting = Ciao { $surname }"
    assert "Placeable mismatch in string (test.ftl:greeting)" in lint(
        run_linter, fluent_project, reference, translation
    )


def test_missing_placeable(run_linter, fluent_project):
    reference = "greeting = Hello { $name }"
    translation = "greeting = Ciao"
    assert "Placeable missing in string (test.ftl:greeting)" in lint(
        run_linter, fluent_project, reference, translation
    )


def test_term_and_message_references_are_checked(run_linter, fluent_project):
    reference = "greeting = Welcome to { -brand-name }"
    translation = "greeting = Benvenuto in { -other-brand }"
    assert "Placeable mismatch in string (test.ftl:greeting)" in lint(
        run_linter, fluent_project, reference, translation
    )


def test_reordered_placeables_are_allowed(run_linter, fluent_project):
    reference = "greeting = { $first } and { $second }"
    translation = "greeting = { $second } e { $first }"
    assert lint(run_linter, fluent_project, reference, translation) == ""


@pytest.mark.xfail(
    strict=True,
    reason=(
        "The attribute checks are dead code: StringExtraction initializes "
        "`msg_ids` and `msg_attributes`, returns them, and never fills them, "
        "so `ref_msg_attributes` is always empty. Lost when compare-locales "
        "was dropped in #79. Remove this marker once they are populated."
    ),
)
def test_missing_and_extra_attributes(run_linter, fluent_project):
    reference = """
        save-button =
            .label = Save
            .accesskey = S
    """
    translation = """
        save-button =
            .label = Salva
            .title = Salva il file
    """
    errors = lint(run_linter, fluent_project, reference, translation)
    assert "Missing attributes in string (test.ftl:save-button): accesskey" in errors
    assert "Extra attributes in string (test.ftl:save-button): title" in errors


def test_data_l10n_name_mismatch(run_linter, fluent_project):
    reference = 'policy = Read the <a data-l10n-name="policy">policy</a>'
    translation = 'policy = Leggi la <a data-l10n-name="privacy">policy</a>'
    assert "data-l10n-name mismatch in string (test.ftl:policy)" in lint(
        run_linter, fluent_project, reference, translation
    )


def test_mismatched_html_elements(run_linter, fluent_project):
    reference = "markup = Read <b>this</b>"
    translation = "markup = Leggi <i>questo</i>"
    assert "Mismatched HTML elements in string (test.ftl:markup)" in lint(
        run_linter, fluent_project, reference, translation
    )


def test_fluent_literal(run_linter, fluent_project):
    reference = "greeting = Hello { $name }"
    translation = 'greeting = Ciao { "" }{ $name }'
    assert "Fluent literal in string (test.ftl:greeting)" in lint(
        run_linter, fluent_project, reference, translation
    )


def test_message_id_repeated_in_the_translation(run_linter, fluent_project):
    reference = "greeting = Hello"
    translation = "greeting = greeting = Ciao"
    assert "Message ID is repeated in string (test.ftl:greeting)" in lint(
        run_linter, fluent_project, reference, translation
    )


def test_ellipsis_and_pilcrow(run_linter, fluent_project):
    reference = """
        loading = Loading…
        search = Search
    """
    translation = """
        loading = Caricamento...
        search = Cerca¶
    """
    errors = lint(run_linter, fluent_project, reference, translation)
    assert "'...' in test.ftl:loading" in errors
    assert "Pilcrow character in string (test.ftl:search)" in errors


def test_exceptions_suppress_placeable_errors(run_linter, fluent_project):
    reference = "greeting = Hello { $name }"
    translation = "greeting = Ciao { $surname }"
    exceptions = {"placeables": {"locales": {}, "strings": ["test.ftl:greeting"]}}
    assert lint(run_linter, fluent_project, reference, translation, exceptions) == ""
