import sqlite3
from dataclasses import fields
from typing import Generator, cast

import pytest

from model import (
    analyze_scenario,
    calculate_change,
    mission_duration_warning,
)
from scenario_inputs import (
    MISSION_DURATION_MAX_DAYS,
    MISSION_DURATION_MIN_DAYS,
    ScenarioInputs,
    allowed_comparison_groups,
    allowed_outcomes,
    allowed_regions,
    allowed_scenario_outcomes,
    allowed_timepoints,
    validate_scenario,
)
from scenario_evidence import (
    PUBLISHED_OBSERVATIONS,
    find_verified_observation,
    seed_abstract_context_measurements,
    seed_reference_measurements,
    verified_english_recovery_observations,
)
from study_library import MeasurementInput, add_measurement, initialize_database


@pytest.fixture
def connection() -> Generator[sqlite3.Connection, None, None]:
    database = initialize_database(":memory:")
    seed_reference_measurements(database)
    yield database
    database.close()


def english_scenario(
    *,
    outcome_id: str = "knee_extension_60",
    region: str = "Knee",
    comparison_group: str = "all",
    timepoint: str = "R+5",
    mission_duration_days: int = 177,
) -> ScenarioInputs:
    return ScenarioInputs(
        study_id="english-2015",
        region=region,
        outcome_id=outcome_id,
        comparison_group=comparison_group,
        timepoint=timepoint,
        mission_duration_days=mission_duration_days,
    )


def test_scenario_has_five_scientific_inputs_and_duration() -> None:
    assert [field.name for field in fields(ScenarioInputs)] == [
        "study_id",
        "region",
        "outcome_id",
        "comparison_group",
        "timepoint",
        "mission_duration_days",
    ]


def test_english_cohort_result_preserves_published_value_units_and_ci(
    connection: sqlite3.Connection,
) -> None:
    result = analyze_scenario(connection, english_scenario())

    assert result.mean_change == -11.0
    assert result.unit == "% mean change from L-60"
    assert result.timepoint == "R+5"
    assert result.sample_size == 37
    assert result.confidence_interval == pytest.approx((-14.8, -7.2))
    assert "negative sign indicates a lower postflight group mean" in result.interpretation
    assert result.source_location == "Table III"
    assert result.source_page == "4"


def test_recovery_series_contains_only_matching_verified_observations(
    connection: sqlite3.Connection,
) -> None:
    observations = verified_english_recovery_observations(
        connection,
        "english::knee::knee_extension_60::all",
    )

    assert [item["timepoint"] for item in observations] == [
        "R+5",
        "R+14",
        "R+30",
    ]
    assert [item["days_after_return"] for item in observations] == [5, 14, 30]
    assert [item["mean_change"] for item in observations] == [-11.0, -12.2, -8.5]
    assert [item["sample_size"] for item in observations] == [37, 34, 36]
    assert observations[0]["ci_lower"] == -14.8
    assert observations[0]["ci_upper"] == -7.2

    subgroup_observations = verified_english_recovery_observations(
        connection,
        "english::knee::knee_extension_60::women",
    )
    assert [item["timepoint"] for item in subgroup_observations] == ["R+5"]


def test_recovery_series_excludes_altered_library_records(
    connection: sqlite3.Connection,
) -> None:
    connection.execute(
        """
        UPDATE measurements
        SET source_wording = 'Altered record'
        WHERE study_id = 'english-2015'
          AND muscle_or_outcome = 'english::knee::knee_extension_60::all'
          AND timepoint = 'R+14'
        """
    )
    connection.commit()

    observations = verified_english_recovery_observations(
        connection,
        "english::knee::knee_extension_60::all",
    )

    assert [item["timepoint"] for item in observations] == ["R+5", "R+30"]


def test_postflight_recovery_timepoints_are_not_mission_days(
    connection: sqlite3.Connection,
) -> None:
    result = analyze_scenario(
        connection,
        english_scenario(timepoint="R+30", mission_duration_days=177),
    )

    assert result.mean_change == -8.5
    assert result.timepoint == "R+30"
    assert all("recovery" not in warning.lower() for warning in result.warnings)
    assert "not a measurement of change during the mission" in result.interpretation


def test_subgroup_comparisons_use_their_published_sample_and_warn_about_inference(
    connection: sqlite3.Connection,
) -> None:
    result = analyze_scenario(
        connection,
        english_scenario(comparison_group="ared", timepoint="R+5"),
    )

    assert result.mean_change == -7.1
    assert result.sample_size == 15
    assert result.confidence_interval == pytest.approx((-11.2, -3.1))
    assert any("not a causal device effect" in warning for warning in result.warnings)

    sex_result = analyze_scenario(
        connection,
        english_scenario(comparison_group="women", timepoint="R+5"),
    )
    assert sex_result.mean_change == -15.0
    assert sex_result.sample_size == 8
    assert any("no statistically significant sex difference" in warning
               for warning in sex_result.warnings)


def test_trunk_measurements_are_only_available_after_landing() -> None:
    assert allowed_timepoints("english-2015", "Trunk", "all") == ("R+14", "R+30")
    with pytest.raises(ValueError, match="timepoint is not reported"):
        validate_scenario(
            english_scenario(
                region="Trunk",
                outcome_id="trunk_extension_60",
                timepoint="R+5",
            )
        )


@pytest.mark.parametrize(
    ("preflight", "postflight", "unit", "expected_difference", "expected_percent"),
    [
        (98.0, 79.0, "µm", -19.0, -19.387755102040817),
        (0.86, 0.56, "mN", -0.30, -34.883720930232556),
        (10.0, 12.0, "N", 2.0, 20.0),
    ],
)
def test_change_uses_post_minus_pre_and_preflight_denominator(
    preflight: float,
    postflight: float,
    unit: str,
    expected_difference: float,
    expected_percent: float,
) -> None:
    change = calculate_change(preflight, postflight, unit)

    assert change.absolute_change == pytest.approx(expected_difference)
    assert change.percent_change == pytest.approx(expected_percent)
    assert change.unit == unit


@pytest.mark.parametrize(
    ("preflight", "postflight", "unit", "message"),
    [
        (None, 1.0, "µm", "Both preflight and postflight values are required"),
        (1.0, None, "µm", "Both preflight and postflight values are required"),
        (0.0, 1.0, "µm", "undefined when the preflight value is zero"),
        (1.0, 2.0, None, "A unit is required"),
        (1.0, float("nan"), "µm", "finite numbers"),
        ("not a number", 2.0, "µm", "must be numbers"),
    ],
)
def test_change_rejects_missing_or_invalid_values(
    preflight: float | None,
    postflight: float | None,
    unit: str | None,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        calculate_change(preflight, postflight, unit)


def test_fitts_mean_changes_are_descriptive_and_have_no_invented_ci(
    connection: sqlite3.Connection,
) -> None:
    diameter = analyze_scenario(
        connection,
        ScenarioInputs(
            study_id="fitts-2010",
            region="Soleus",
            outcome_id="diameter",
            comparison_group="type_i",
            timepoint="preflight_to_landing",
            mission_duration_days=177,
        ),
    )
    force = analyze_scenario(
        connection,
        ScenarioInputs(
            study_id="fitts-2010",
            region="Soleus",
            outcome_id="peak_force",
            comparison_group="type_i",
            timepoint="preflight_to_landing",
            mission_duration_days=177,
        ),
    )

    assert diameter.preflight_value == 98.0
    assert diameter.postflight_value == 79.0
    assert diameter.absolute_change == -19.0
    assert diameter.mean_change == pytest.approx(-19.3877551)
    assert diameter.unit == "μm"
    assert diameter.sample_size is None
    assert diameter.preflight_sample_size == 540
    assert diameter.postflight_sample_size == 458
    assert diameter.preflight_standard_error == 1.0
    assert diameter.postflight_standard_error == 1.0
    assert diameter.confidence_interval is None
    assert any("not the mean of individual" in warning for warning in diameter.warnings)
    assert "n=540" in diameter.source_wording
    assert "n=458" in diameter.source_wording
    assert (diameter.source_page, diameter.source_location) == ("6", "Table 2")
    assert abs(abs(diameter.mean_change) - 20.0) < 1.0
    assert force.preflight_value == 0.86
    assert force.postflight_value == 0.56
    assert force.absolute_change == pytest.approx(-0.30)
    assert force.mean_change == pytest.approx(-34.88372093)
    assert force.unit == "mN"
    assert force.preflight_standard_error == 0.01
    assert force.postflight_standard_error == 0.01
    assert (force.source_page, force.source_location) == ("7", "Table 3")
    assert abs(abs(force.mean_change) - 35.0) < 0.2


def test_fibre_and_joint_outcomes_are_not_pooled(
    connection: sqlite3.Connection,
) -> None:
    with pytest.raises(ValueError, match="anatomical region"):
        analyze_scenario(
            connection,
            ScenarioInputs(
                study_id="fitts-2010",
                region="Gastrocnemius",
                outcome_id="diameter",
                comparison_group="type_i",
                timepoint="preflight_to_landing",
                mission_duration_days=177,
            ),
        )
    assert find_verified_observation(
        connection,
        "fitts-2010",
        "english::knee::knee_extension_60::all",
        "Mean percent change from L-60",
        "R+5",
    ) is None


def test_scenario_catalog_contains_only_outcomes_with_complete_evidence(
    connection: sqlite3.Connection,
) -> None:
    assert set(allowed_scenario_outcomes("english-2015")) == {
        item.record_key.split("::")[2]
        for item in PUBLISHED_OBSERVATIONS
        if item.study_id == "english-2015"
    }
    assert allowed_regions("fitts-2010") == ("Soleus",)
    assert allowed_outcomes("fitts-2010", "Soleus") == {
        "diameter": "Fibre diameter",
        "peak_force": "Peak isometric fibre force",
    }
    assert allowed_outcomes("fitts-2010", "Gastrocnemius") == {}
    assert allowed_comparison_groups(
        "fitts-2010", "Soleus", "diameter"
    ) == {"type_i": "Slow type I fibres"}
    assert allowed_timepoints(
        "fitts-2010", "Soleus", "type_i", "diameter"
    ) == ("preflight_to_landing",)
    assert allowed_timepoints(
        "fitts-2010", "Soleus", "type_ii", "diameter"
    ) == ()
    assert allowed_timepoints(
        "fitts-2010", "Soleus", "type_i", "cross_sectional_area"
    ) == ()


def test_every_offered_scenario_has_a_numerical_result(
    connection: sqlite3.Connection,
) -> None:
    for study_id in ("english-2015", "fitts-2010"):
        for outcome_id, (region, _) in allowed_scenario_outcomes(study_id).items():
            groups = allowed_comparison_groups(study_id, region, outcome_id)
            for comparison_group in groups:
                for timepoint in allowed_timepoints(
                    study_id, region, comparison_group, outcome_id
                ):
                    result = analyze_scenario(
                        connection,
                        ScenarioInputs(
                            study_id=study_id,
                            region=region,
                            outcome_id=outcome_id,
                            comparison_group=comparison_group,
                            timepoint=timepoint,
                            mission_duration_days=177,
                        ),
                    )
                    assert result.mean_change is not None


def test_unverified_record_cannot_supply_quantitative_result(
    connection: sqlite3.Connection,
) -> None:
    row = connection.execute(
        """
        SELECT id, muscle_or_outcome, measurement_name, value, unit, timepoint,
               comparison_baseline, sample_size, sample_size_status, source_page,
               source_location, source_wording, uncertainty_notes
        FROM measurements
        WHERE study_id = 'english-2015'
          AND muscle_or_outcome = 'english::knee::knee_extension_60::all'
          AND timepoint = 'R+5'
        """
    ).fetchone()
    assert row is not None
    connection.execute("DELETE FROM measurements WHERE id = ?", (row["id"],))
    connection.commit()
    add_measurement(
        connection,
        MeasurementInput(
            study_id="english-2015",
            muscle_or_outcome=row["muscle_or_outcome"],
            measurement_name=row["measurement_name"],
            value=row["value"],
            value_status="reported",
            unit=row["unit"],
            timepoint=row["timepoint"],
            comparison_baseline=row["comparison_baseline"],
            sample_size=row["sample_size"],
            sample_size_status=row["sample_size_status"],
            source_page=row["source_page"],
            source_location=row["source_location"],
            source_wording=row["source_wording"],
            uncertainty_notes=row["uncertainty_notes"],
        ),
    )

    result = analyze_scenario(connection, english_scenario())

    assert result.mean_change is None
    assert any("unverified or altered record is not used" in warning
               for warning in result.warnings)


def test_seed_is_idempotent_and_preserves_existing_records(
    connection: sqlite3.Connection,
) -> None:
    total = connection.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
    assert total == len(PUBLISHED_OBSERVATIONS)
    assert total == 86
    assert seed_reference_measurements(connection) == 0
    assert connection.execute("SELECT COUNT(*) FROM measurements").fetchone()[0] == total


def test_every_curated_record_matches_its_verified_source_metadata(
    connection: sqlite3.Connection,
) -> None:
    for observation in PUBLISHED_OBSERVATIONS:
        record = find_verified_observation(
            connection,
            observation.study_id,
            observation.record_key,
            observation.measurement_name,
            observation.timepoint,
        )
        assert record is not None
        assert record["value"] == str(observation.value)
        assert record["unit"] == observation.unit
        assert record["sample_size"] == observation.sample_size
        assert record["source_page"] == observation.source_page
        assert record["source_location"] == observation.source_location


@pytest.mark.parametrize(
    ("days", "expected_warning"),
    [(105, False), (205, False), (104, True), (206, True)],
)
def test_english_duration_summary_envelope(
    days: int,
    expected_warning: bool,
) -> None:
    warning = mission_duration_warning("english-2015", days)
    assert (warning is not None) is expected_warning


@pytest.mark.parametrize(
    ("days", "expected_warning"),
    [(161, False), (192, False), (160, True), (193, True)],
)
def test_fitts_duration_observed_range(
    days: int,
    expected_warning: bool,
) -> None:
    warning = mission_duration_warning("fitts-2010", days)
    assert (warning is not None) is expected_warning


@pytest.mark.parametrize(
    ("days", "expected_warning"),
    [
        (MISSION_DURATION_MIN_DAYS, True),
        (165, False),
        (MISSION_DURATION_MAX_DAYS, True),
    ],
)
def test_slider_boundaries_are_valid_and_duration_does_not_change_result(
    connection: sqlite3.Connection,
    days: int,
    expected_warning: bool,
) -> None:
    inputs = english_scenario(mission_duration_days=days)
    validate_scenario(inputs)
    result = analyze_scenario(connection, inputs)

    assert result.mean_change == -11.0
    assert any("outside" in warning for warning in result.warnings) is expected_warning
    assert any(
        "does not estimate a duration-dependent change" in warning
        for warning in result.warnings
    ) is expected_warning


@pytest.mark.parametrize(
    "days",
    [MISSION_DURATION_MIN_DAYS - 1, MISSION_DURATION_MAX_DAYS + 1],
)
def test_duration_outside_slider_bounds_is_rejected(days: int) -> None:
    with pytest.raises(ValueError, match="between 90 and 240 days"):
        validate_scenario(english_scenario(mission_duration_days=days))


@pytest.mark.parametrize("days", [90.5, True, None])
def test_duration_must_be_a_whole_number(days: object) -> None:
    with pytest.raises(ValueError, match="whole number"):
        validate_scenario(
            english_scenario(mission_duration_days=cast(int, days))
        )


def test_duration_warning_is_study_specific_and_does_not_change_observation(
    connection: sqlite3.Connection,
) -> None:
    within = analyze_scenario(connection, english_scenario(mission_duration_days=177))
    outside = analyze_scenario(connection, english_scenario(mission_duration_days=240))

    assert within.mean_change == outside.mean_change == -11.0
    assert not any("outside" in warning for warning in within.warnings)
    assert any("outside" in warning for warning in outside.warnings)


def test_scenario_rejects_incompatible_study_region_and_group() -> None:
    with pytest.raises(ValueError, match="anatomical region"):
        validate_scenario(
            ScenarioInputs(
                study_id="fitts-2010",
                region="Knee",
                outcome_id="diameter",
                comparison_group="type_i",
                timepoint="preflight_to_landing",
                mission_duration_days=177,
            )
        )


def test_abstract_only_evidence_cannot_enter_engine_or_curated_catalog(
    connection: sqlite3.Connection,
) -> None:
    seed_abstract_context_measurements(connection)
    assert {
        observation.study_id for observation in PUBLISHED_OBSERVATIONS
    } == {"english-2015", "fitts-2010"}
    assert find_verified_observation(
        connection,
        "gopalakrishnan-2010",
        "gopalakrishnan::muscle-volume",
        "Reported muscle volume change ranges",
        "Preflight to postflight",
    ) is None
    with pytest.raises(ValueError, match="Select one of the studies"):
        validate_scenario(
            ScenarioInputs(
                study_id="gopalakrishnan-2010",
                region="Calf",
                outcome_id="muscle_volume",
                comparison_group="all",
                timepoint="preflight_to_postflight",
                mission_duration_days=177,
            )
        )
