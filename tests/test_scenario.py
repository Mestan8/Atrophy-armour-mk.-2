"""Control availability per study, scenario results and page data."""

import json
import sqlite3

import pytest

from api import (
    build_library_view,
    build_measurements_view,
    build_scenario_controls_view,
    build_scenario_view,
)
from evidence_catalog import CATEGORIES
from scenario_inputs import resolve_controls
from study_library import initialize_database


@pytest.fixture
def connection() -> sqlite3.Connection:
    database = initialize_database(":memory:")
    yield database
    database.close()


def options(controls, control_id):
    control = next(item for item in controls if item.id == control_id)
    return {option.value: option for option in control.options}


def test_there_are_exactly_five_scientific_controls_plus_the_study_filter():
    _, controls = resolve_controls({})
    assert [control.id for control in controls] == [
        "study", "category", "region", "countermeasure", "subgroup", "recovery",
    ]


def test_categories_without_data_are_disabled_with_a_reason():
    _, controls = resolve_controls({"study": "greene-2021"})
    categories = options(controls, "category")
    assert not categories["muscle_size"].disabled
    assert categories["strength"].disabled
    assert categories["strength"].reason == "Not measured by Greene et al. (2021)"


def test_abstract_only_study_says_so_in_the_reason():
    _, controls = resolve_controls({"study": "gopalakrishnan-2010"})
    reason = options(controls, "category")["fibre"].reason
    assert "abstract" in reason


def test_men_and_women_are_offered_only_where_reported():
    _, controls = resolve_controls({"study": "english-2015", "category": "strength"})
    subgroups = options(controls, "subgroup")
    assert not subgroups["men"].disabled and not subgroups["women"].disabled
    _, controls = resolve_controls({"study": "trappe-2009", "category": "strength"})
    subgroups = options(controls, "subgroup")
    assert subgroups["women"].disabled
    assert "Not reported separately by Trappe et al. (2009)" in subgroups["women"].reason


def test_an_unsupported_request_falls_back_instead_of_inventing_a_value():
    selection, _ = resolve_controls({"study": "greene-2021", "category": "fibre"})
    assert selection.category == "muscle_size"


def test_recovery_day_snaps_to_reported_timepoints_only():
    _, controls = resolve_controls({"study": "greene-2021"})
    days = options(controls, "recovery")
    assert {"first", "7", "365", "1095"} <= set(days)
    assert not {"10", "100"} & set(days)


def test_regimen_choices_follow_the_paper(connection):
    _, controls = resolve_controls({"study": "sprint-2020", "category": "strength", "region": "thigh_knee"})
    regimens = options(controls, "countermeasure")
    assert {"any", "iss_standard_care", "sprint"} <= set(regimens)
    view = build_scenario_view(connection, {"study": "sprint-2020", "category": "strength", "region": "thigh_knee", "countermeasure": "sprint"})
    assert all("SPRINT" in row["title"] for row in view["rows"])


def test_duration_slider_changes_the_displayed_output(connection):
    base = {"study": "trappe-2009", "category": "muscle_size", "region": "calf_ankle"}
    short = build_scenario_view(connection, {**base, "duration": 165})
    long = build_scenario_view(connection, {**base, "duration": 190})
    short_value = short["rows"][0]["metrics"][-1]
    long_value = long["rows"][0]["metrics"][-1]
    assert short_value["tag"] == long_value["tag"] == "approximation"
    assert short_value["text"] != long_value["text"]
    assert short["slider"]["is_approximation"]
    assert short["slider"]["notices"][0].startswith("Straight-line approximation")


def test_slider_range_and_default_depend_on_the_study(connection):
    trappe = build_scenario_view(connection, {"study": "trappe-2009"})["slider"]
    greene = build_scenario_view(connection, {"study": "greene-2021"})["slider"]
    assert trappe["default"] == 177 and "161–192" in trappe["supported"]
    assert greene["default"] == 150 and "120–180" in greene["supported"]


def test_extrapolation_warning_appears_outside_the_supported_range(connection):
    view = build_scenario_view(connection, {"study": "trappe-2009", "duration": 230})
    assert view["slider"]["warning"].startswith("Extrapolation warning")
    assert view["rows"][0]["metrics"][-1]["tag"] == "extrapolation"


def test_multi_cohort_model_is_labelled_and_has_its_source_statement(connection):
    view = build_scenario_view(connection, {"study": "leblanc-2000", "category": "muscle_size", "region": "calf_ankle"})
    assert view["slider"]["model_label"].startswith("Fitted to several cohorts")
    assert any("no significant slope" in text for text in view["slider"]["statements"])


def test_every_displayed_result_names_its_source_table(connection):
    view = build_scenario_view(connection, {"study": "all", "category": "strength"})
    for row in view["rows"]:
        if row["detail_id"]:
            assert "PDF page" in row["source"]
            assert row["detail_id"] in view["details"]


def test_all_three_charts_are_built_with_hover_text(connection):
    view = build_scenario_view(connection, {"study": "english-2015", "category": "strength", "region": "thigh_knee"})
    for name in ("duration", "recovery", "comparison"):
        assert "figure" in view["charts"][name], name
    traces = view["charts"]["comparison"]["figure"]["data"]
    hover = json.dumps(traces)
    for word in ("Value type", "Uncertainty", "Sample", "Timepoint", "Source"):
        assert word in hover


def test_duration_chart_marks_extrapolated_segments_with_dashes(connection):
    view = build_scenario_view(connection, {"study": "trappe-2009"})
    dashes = {trace.get("line", {}).get("dash") for trace in view["charts"]["duration"]["figure"]["data"]}
    assert "dash" in dashes and "solid" in dashes


def test_abstract_range_gets_no_duration_chart(connection):
    view = build_scenario_view(connection, {"study": "gopalakrishnan-2010"})
    assert "message" in view["charts"]["duration"]
    assert not view["slider"]["is_approximation"]


def test_scenario_view_is_json_ready_for_every_study(connection):
    for study in ("all", "english-2015", "fitts-2010", "scott-2023", "trappe-2009",
                  "sprint-2020", "leblanc-2000", "gopalakrishnan-2010", "greene-2021"):
        for category in CATEGORIES:
            json.dumps(build_scenario_view(connection, {"study": study, "category": category}))


def test_measurements_page_shows_every_category_slot_for_every_study(connection):
    view = build_measurements_view(connection, {"study": "all"})
    assert len(view["studies"]) == 8
    for study in view["studies"]:
        assert [block["id"] for block in study["categories"]] == [*CATEGORIES, "recovery"]
        for block in study["categories"]:
            assert block["rows"] or block["empty"]
    fitts = next(study for study in view["studies"] if study["id"] == "fitts-2010")
    muscle = next(block for block in fitts["categories"] if block["id"] == "muscle_size")
    assert muscle["empty"] == "Not measured in this study."


def test_measurement_filters_narrow_the_table(connection):
    view = build_measurements_view(connection, {"study": "greene-2021", "timepoint": "365"})
    rows = [row for block in view["studies"][0]["categories"] for row in block["rows"]]
    assert rows and all("1 year" in row["cells"][3] for row in rows)


def test_library_keeps_external_evidence_separate(connection):
    view = build_library_view(connection, {})
    assert len(view["options"]) == 8
    assert [item["title"][:2] for item in view["external"]] == ["E1", "E2", "E3", "E4"]



def test_controls_view_returns_only_the_control_state(connection):
    for selection in ({}, {"study": "greene-2021", "category": "fibre"}, {"study": "english-2015", "subgroup": "women"}):
        controls = build_scenario_controls_view(connection, selection)
        full = build_scenario_view(connection, selection)
        assert set(controls) == {"notice", "controls"}
        assert controls["controls"] == full["controls"]


def test_measurements_payload_has_no_manual_records(connection):
    view = build_measurements_view(connection, {"study": "all"})
    assert "form" not in view
    for study in view["studies"]:
        assert "manual" not in study and "unverified" not in study
