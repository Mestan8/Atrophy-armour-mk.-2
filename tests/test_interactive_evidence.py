import sqlite3

import pytest

from interactive_evidence import (
    build_observation_details,
    observation_identifier,
    resolve_selected_observation,
    selected_observation_id,
)
from plotting import (
    create_fibre_comparison_plot,
    create_recovery_plot,
    create_relative_change_plot,
)
from scenario_evidence import (
    find_verified_observation,
    seed_reference_measurements,
    verified_english_recovery_observations,
)
from study_library import get_study, initialize_database


@pytest.fixture
def connection() -> sqlite3.Connection:
    database = initialize_database(":memory:")
    seed_reference_measurements(database)
    yield database
    database.close()


def test_english_point_metadata_describes_postflight_joint_measurement(
    connection: sqlite3.Connection,
) -> None:
    study = get_study(connection, "english-2015")
    record = find_verified_observation(
        connection,
        "english-2015",
        "english::knee::knee_extension_60::all",
        "Mean percent change from L-60",
        "R+5",
    )
    assert study is not None
    assert record is not None

    details = build_observation_details(
        study,
        record,
        region="Knee",
        outcome="Knee extension peak torque at 60°/s",
        comparison="All participants",
        unit="% mean change from L-60",
    )

    assert details["value"] == "-11.0"
    assert details["unit"] == "%"
    assert details["timepoint"] == "R+5"
    assert details["source_page"] == "4"
    assert details["source_location"] == "Table III"
    assert details["sample_size"] == 37
    assert "flight datasets" in details["sample_definition"]
    assert "not an in-flight measurement" in details["scientific_meaning"]
    assert "Original reported group mean" in details["statistic"]
    assert details["doi"] == "10.3357/AMHP.EC09.2015"


def test_fitts_point_metadata_keeps_fibre_counts_distinct_from_crew(
    connection: sqlite3.Connection,
) -> None:
    study = get_study(connection, "fitts-2010")
    record = find_verified_observation(
        connection,
        "fitts-2010",
        "fitts::soleus::diameter::type_i",
        "Preflight value",
        "L-55 ± 2 days",
    )
    assert study is not None
    assert record is not None

    details = build_observation_details(
        study,
        record,
        region="Soleus",
        outcome="Fibre diameter",
        comparison="Slow type I fibres",
        unit="μm",
    )

    assert details["value"] == "98.0"
    assert details["timepoint"] == "L-55 ± 2 days"
    assert details["sample_size"] == 540
    assert "fibres, not astronaut participants" in details["sample_definition"]
    assert "not whole-joint strength" in details["scientific_meaning"]
    assert details["source_page"] == "6"
    assert details["source_location"] == "Table 2"


def test_point_selection_resolves_only_the_active_observation() -> None:
    preflight_details = {
        "observation_id": "study::record::measurement::R+5",
        "value": "98",
    }
    landing_details = {
        "observation_id": "study::record::measurement::R+0",
        "value": "79",
    }
    active_details = {
        preflight_details["observation_id"]: preflight_details,
        landing_details["observation_id"]: landing_details,
    }
    selected = {
        "points": [
            {"customdata": landing_details["observation_id"], "point_index": 1}
        ]
    }

    assert selected_observation_id(selected) == landing_details["observation_id"]
    assert resolve_selected_observation(selected, active_details) is landing_details
    assert resolve_selected_observation(
        {"points": [{"customdata": "old-scenario-point"}]},
        active_details,
    ) is None
    assert resolve_selected_observation({"points": []}, {}) is None
    assert selected_observation_id({"points": [{"point_index": 0}]}) is None


def test_optional_source_metadata_can_be_absent(
    connection: sqlite3.Connection,
) -> None:
    study = get_study(connection, "fitts-2010")
    record = find_verified_observation(
        connection,
        "fitts-2010",
        "fitts::soleus::diameter::type_i",
        "Preflight value",
        "L-55 ± 2 days",
    )
    assert study is not None
    assert record is not None
    optional_record = dict(record)
    optional_record.update(
        sample_size=None,
        source_page=None,
        source_location=None,
        uncertainty_notes=None,
        source_wording=None,
    )
    optional_study = dict(study)
    optional_study["doi"] = None

    details = build_observation_details(
        optional_study,
        optional_record,
        region="Soleus",
        outcome="Fibre diameter",
        comparison="Slow type I fibres",
        unit="μm",
    )

    assert details["sample_size"] is None
    assert details["sample_definition"] is None
    assert details["source_page"] is None
    assert details["source_location"] is None
    assert details["doi"] is None


def test_plot_points_carry_matching_stable_record_identifiers(
    connection: sqlite3.Connection,
) -> None:
    recovery = verified_english_recovery_observations(
        connection,
        "english::knee::knee_extension_60::all",
    )
    recovery_figure = create_recovery_plot(recovery, "Recovery")
    assert recovery_figure is not None
    assert list(recovery_figure.data[0].customdata) == [
        item["observation_id"] for item in recovery
    ]

    preflight = find_verified_observation(
        connection,
        "fitts-2010",
        "fitts::soleus::diameter::type_i",
        "Preflight value",
        "L-55 ± 2 days",
    )
    postflight = find_verified_observation(
        connection,
        "fitts-2010",
        "fitts::soleus::diameter::type_i",
        "Postflight value",
        "R+0, landing day",
    )
    assert preflight is not None and postflight is not None
    identifiers = (
        observation_identifier(preflight),
        observation_identifier(postflight),
    )
    fibre_figure = create_fibre_comparison_plot(
        98.0,
        79.0,
        "μm",
        "Soleus fibre diameter",
        observation_ids=identifiers,
    )
    assert list(fibre_figure.data[0].customdata) == list(identifiers)

    english_figure = create_relative_change_plot(
        -11.0,
        "%",
        "Observed R+5",
        observation_id=identifiers[0],
    )
    assert list(english_figure.data[0].customdata) == [identifiers[0]]
