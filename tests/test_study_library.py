import sqlite3
from pathlib import Path

import pytest

from study_library import (
    MeasurementInput,
    add_measurement,
    get_study,
    initialize_database,
    list_measurements,
    list_studies,
    mark_measurement_source_verified,
)


@pytest.fixture
def connection() -> sqlite3.Connection:
    database = initialize_database(":memory:")
    yield database
    database.close()


def test_initialization_seeds_both_distinct_study_records(
    connection: sqlite3.Connection,
) -> None:
    studies = list_studies(connection)

    assert {study["id"] for study in studies} == {
        "english-2015",
        "fitts-2010",
        "scott-2023",
        "trappe-2009",
        "sprint-2020",
        "leblanc-2000",
        "gopalakrishnan-2010",
        "greene-2021",
    }
    english = get_study(connection, "english-2015")
    fitts = get_study(connection, "fitts-2010")

    assert english is not None
    assert fitts is not None
    assert english["sample_size"] == 37
    assert fitts["sample_size"] == 9
    assert "knee, ankle, and trunk" in english["measurement_methods"]
    assert "cellular fibre findings" in fitts["findings"]
    assert english["source_availability"] == "full_text"
    assert english["quantitative_verification_status"] == "source_verified"


def test_new_studies_match_local_references_and_abstract_is_separately_marked(
    connection: sqlite3.Connection,
) -> None:
    project_root = Path(__file__).resolve().parents[1]
    studies_by_id = {study["id"]: study for study in list_studies(connection)}

    for study_id in (
        "scott-2023",
        "trappe-2009",
        "sprint-2020",
        "leblanc-2000",
        "gopalakrishnan-2010",
        "greene-2021",
    ):
        study = studies_by_id[study_id]
        assert (project_root / "data" / "references" / study["source_file"]).is_file()

    abstract = studies_by_id["gopalakrishnan-2010"]
    assert abstract["source_availability"] == "abstract_only"
    assert abstract["extraction_status"] == "abstract_extracted"
    assert abstract["quantitative_verification_status"] == "context_only"
    assert "one-page abstract" in abstract["sample_size_note"]
    assert "ambiguous" in abstract["limitations"]


def test_study_and_measurement_records_persist_to_sqlite(tmp_path) -> None:
    database_path = tmp_path / "study-library.sqlite3"
    connection = initialize_database(database_path)
    measurement_id = add_measurement(
        connection,
        MeasurementInput(
            study_id="english-2015",
            muscle_or_outcome="Knee extension",
            measurement_name="Peak torque",
        ),
    )
    connection.close()

    reopened = initialize_database(database_path)
    try:
        assert get_study(reopened, "english-2015") is not None
        assert list_measurements(reopened, "english-2015")[0]["id"] == measurement_id
    finally:
        reopened.close()


def test_measurement_storage_and_retrieval_preserve_unverified_status(
    connection: sqlite3.Connection,
) -> None:
    measurement_id = add_measurement(
        connection,
        MeasurementInput(
            study_id="english-2015",
            muscle_or_outcome="Knee extension",
            measurement_name="Peak torque",
            value="-11.0",
            value_status="reported",
            unit="percent change",
            timepoint="R+5",
            comparison_baseline="L-60",
            sample_size=37,
            sample_size_status="reported",
            source_page="4",
            source_location="Table III",
            source_wording="Example source context.",
        ),
    )

    measurement = list_measurements(connection, "english-2015")[0]
    assert measurement["id"] == measurement_id
    assert measurement["value"] == "-11.0"
    assert measurement["unit"] == "percent change"
    assert measurement["verification_status"] == "unverified"


def test_unreported_value_and_sample_size_remain_explicit(
    connection: sqlite3.Connection,
) -> None:
    add_measurement(
        connection,
        MeasurementInput(
            study_id="fitts-2010",
            muscle_or_outcome="Soleus type I fibre",
            measurement_name="Peak force",
            value_status="unreported",
            sample_size_status="unknown",
        ),
    )

    measurement = list_measurements(connection, "fitts-2010")[0]
    assert measurement["value"] is None
    assert measurement["value_status"] == "unreported"
    assert measurement["sample_size"] is None
    assert measurement["sample_size_status"] == "unknown"


def test_source_verification_requires_page_and_exact_wording(
    connection: sqlite3.Connection,
) -> None:
    measurement_id = add_measurement(
        connection,
        MeasurementInput(
            study_id="fitts-2010",
            muscle_or_outcome="Soleus fibre",
            measurement_name="Fibre diameter",
        ),
    )

    with pytest.raises(ValueError, match="source page and exact source wording"):
        mark_measurement_source_verified(
            connection,
            measurement_id,
            source_page="",
            source_wording="",
        )

    assert list_measurements(connection, "fitts-2010")[0][
        "verification_status"
    ] == "unverified"


def test_source_verified_measurement_stores_evidence(
    connection: sqlite3.Connection,
) -> None:
    measurement_id = add_measurement(
        connection,
        MeasurementInput(
            study_id="fitts-2010",
            muscle_or_outcome="Soleus type I fibre",
            measurement_name="Fibre diameter",
        ),
    )
    mark_measurement_source_verified(
        connection,
        measurement_id,
        source_page="6",
        source_location="Table 2",
        source_wording="Pre-flight and post-flight fibre diameter values.",
    )

    measurement = list_measurements(connection, "fitts-2010")[0]
    assert measurement["verification_status"] == "source_verified"
    assert measurement["source_page"] == "6"
    assert measurement["source_location"] == "Table 2"
    assert measurement["source_wording"].startswith("Pre-flight")


def test_reported_measurement_requires_a_value(
    connection: sqlite3.Connection,
) -> None:
    with pytest.raises(ValueError, match="reported measurement value is required"):
        add_measurement(
            connection,
            MeasurementInput(
                study_id="english-2015",
                muscle_or_outcome="Knee",
                measurement_name="Peak torque",
                value_status="reported",
            ),
        )
