"""Source-checked numerical observations used by the Scenario Explorer."""

from dataclasses import dataclass
import math
import sqlite3

from study_library import (
    MeasurementInput,
    add_measurement,
    list_measurements,
)


@dataclass(frozen=True)
class PublishedObservation:
    study_id: str
    record_key: str
    measurement_name: str
    value: float
    unit: str
    timepoint: str
    baseline: str | None
    sample_size: int | None
    sample_size_status: str
    source_page: str
    source_location: str
    source_wording: str
    uncertainty_notes: str


ENGLISH_OUTCOMES = {
    "knee_extension_60": ("Knee", "Knee extension peak torque at 60°/s"),
    "knee_flexion_60": ("Knee", "Knee flexion peak torque at 60°/s"),
    "knee_extension_180": ("Knee", "Knee extension peak torque at 180°/s"),
    "knee_flexion_180": ("Knee", "Knee flexion peak torque at 180°/s"),
    "knee_extension_work_180": ("Knee", "Knee extension total work at 180°/s"),
    "knee_flexion_work_180": ("Knee", "Knee flexion total work at 180°/s"),
    "ankle_extension_con_30": (
        "Ankle",
        "Ankle concentric extension peak torque at 30°/s",
    ),
    "ankle_flexion_con_30": (
        "Ankle",
        "Ankle concentric flexion peak torque at 30°/s",
    ),
    "ankle_extension_ecc_30": (
        "Ankle",
        "Ankle eccentric extension peak torque at 30°/s",
    ),
    "ankle_flexion_ecc_30": (
        "Ankle",
        "Ankle eccentric flexion peak torque at 30°/s",
    ),
    "trunk_extension_60": ("Trunk", "Trunk extension peak torque at 60°/s"),
    "trunk_flexion_60": ("Trunk", "Trunk flexion peak torque at 60°/s"),
}

_COHORT_ROWS = {
    "knee_extension_60": (
        (-11.0, -7.2, -14.8, 37),
        (-12.2, -8.8, -15.6, 34),
        (-8.5, -5.2, -11.8, 36),
    ),
    "knee_flexion_60": (
        (-16.6, -13.1, -20.2, 37),
        (-12.8, -9.3, -16.3, 34),
        (-6.6, -2.6, -10.6, 36),
    ),
    "knee_extension_180": (
        (-15.6, -12.4, -18.8, 37),
        (-10.6, -7.0, -14.2, 34),
        (-4.6, -1.8, -7.5, 36),
    ),
    "knee_flexion_180": (
        (-16.2, -11.7, -20.6, 37),
        (-12.9, -9.2, -16.6, 34),
        (-3.9, 0.8, -8.6, 36),
    ),
    "knee_extension_work_180": (
        (-7.9, -3.8, -12.0, 34),
        (-7.8, -4.4, -11.1, 31),
        (-5.2, -2.3, -8.0, 33),
    ),
    "knee_flexion_work_180": (
        (-8.5, -4.6, -12.3, 34),
        (-11.1, -7.6, -14.6, 31),
        (-4.4, -0.3, -8.5, 33),
    ),
    "ankle_extension_con_30": (
        (-13.6, -9.7, -17.4, 37),
        (-8.4, -3.7, -13.1, 34),
        (-3.5, 0.7, -7.7, 36),
    ),
    "ankle_flexion_con_30": (
        (-10.7, -6.5, -14.8, 37),
        (-9.0, -5.3, -12.7, 34),
        (-4.0, -0.4, -7.6, 36),
    ),
    "ankle_extension_ecc_30": (
        (-11.4, -4.6, -18.1, 32),
        (-3.3, 2.8, -9.3, 31),
        (-1.3, 5.0, -7.5, 32),
    ),
    "ankle_flexion_ecc_30": (
        (-8.7, -5.9, -11.6, 31),
        (-6.7, -2.9, -10.4, 30),
        (-4.3, -1.6, -7.1, 32),
    ),
    "trunk_extension_60": (
        (-6.3, -1.9, -10.7, 25),
        (-0.8, 4.0, -5.6, 27),
    ),
    "trunk_flexion_60": (
        (-8.1, -3.3, -12.9, 25),
        (-5.6, -1.9, -9.4, 27),
    ),
}

_SEX_ROWS = {
    "men": {
        "knee_extension_60": (-10.0, -5.5, -14.4, 29),
        "knee_flexion_60": (-16.2, -13.2, -19.2, 29),
        "knee_extension_180": (-15.1, -12.3, -17.8, 29),
        "knee_flexion_180": (-14.6, -10.1, -19.0, 29),
        "knee_extension_work_180": (-7.4, -2.4, -12.5, 27),
        "knee_flexion_work_180": (-6.7, -2.3, -11.2, 27),
        "ankle_extension_con_30": (-12.0, -8.0, -16.1, 29),
        "ankle_flexion_con_30": (-10.8, -6.0, -15.5, 29),
        "ankle_extension_ecc_30": (-10.3, -2.0, -18.7, 25),
        "ankle_flexion_ecc_30": (-9.2, -5.8, -12.5, 25),
        "trunk_extension_60": (-5.1, -0.4, -9.8, 19),
        "trunk_flexion_60": (-7.3, -1.5, -13.2, 19),
    },
    "women": {
        "knee_extension_60": (-15.0, -8.2, -21.7, 8),
        "knee_flexion_60": (-18.3, -5.3, -31.3, 8),
        "knee_extension_180": (-17.6, -6.1, -29.0, 8),
        "knee_flexion_180": (-21.9, -9.0, -34.8, 8),
        "knee_extension_work_180": (-9.6, -5.7, -13.5, 7),
        "knee_flexion_work_180": (-15.1, -9.3, -20.9, 7),
        "ankle_extension_con_30": (-19.1, -9.6, -28.7, 8),
        "ankle_flexion_con_30": (-10.4, -1.1, -19.6, 8),
        "ankle_extension_ecc_30": (-15.1, -6.2, -23.9, 7),
        "ankle_flexion_ecc_30": (-7.0, -1.4, -12.6, 6),
        "trunk_extension_60": (-10.0, 0.9, -21.0, 6),
        "trunk_flexion_60": (-10.6, -2.3, -18.9, 6),
    },
}

_DEVICE_ROWS = {
    "ired": {
        "knee_extension_60": (-13.7, -8.1, -19.3, 22),
        "knee_flexion_60": (-19.5, -15.1, -23.9, 22),
        "knee_extension_180": (-17.4, -12.8, -22.1, 22),
        "knee_flexion_180": (-17.3, -10.5, -24.1, 22),
        "knee_extension_work_180": (-10.7, -6.6, -14.7, 19),
        "knee_flexion_work_180": (-8.9, -4.4, -13.4, 19),
        "ankle_extension_con_30": (-14.2, -8.9, -19.6, 22),
        "ankle_flexion_con_30": (-9.7, -4.4, -15.1, 22),
        "ankle_extension_ecc_30": (-11.3, -0.3, -22.2, 19),
        "ankle_flexion_ecc_30": (-8.5, -4.1, -12.8, 17),
        "trunk_extension_60": (-7.4, 0.3, -15.2, 12),
        "trunk_flexion_60": (-8.0, -1.4, -14.6, 12),
    },
    "ared": {
        "knee_extension_60": (-7.1, -3.1, -11.2, 15),
        "knee_flexion_60": (-12.4, -7.1, -17.7, 15),
        "knee_extension_180": (-12.9, -9.2, -16.6, 15),
        "knee_flexion_180": (-14.5, -9.6, -19.4, 15),
        "knee_extension_work_180": (-4.3, 3.2, -11.9, 15),
        "knee_flexion_work_180": (-7.9, -1.1, -14.8, 15),
        "ankle_extension_con_30": (-12.6, -7.1, -18.2, 15),
        "ankle_flexion_con_30": (-12.0, -5.3, -18.7, 15),
        "ankle_extension_ecc_30": (-11.5, -6.2, -16.8, 13),
        "ankle_flexion_ecc_30": (-9.1, -5.4, -12.7, 14),
        "trunk_extension_60": (-5.3, -0.5, -10.0, 13),
        "trunk_flexion_60": (-8.2, -1.0, -15.4, 13),
    },
}

_TIMEPOINTS = ("R+5", "R+14", "R+30")
_GROUP_LABELS = {
    "all": "All participants",
    "men": "Men",
    "women": "Women",
    "ired": "iRED",
    "ared": "ARED",
}


def _english_observations() -> list[PublishedObservation]:
    observations: list[PublishedObservation] = []
    for outcome_id, rows in _COHORT_ROWS.items():
        for index, (mean, ci_first, ci_second, sample_size) in enumerate(rows):
            timepoint = _TIMEPOINTS[index] if outcome_id.startswith(
                ("knee_", "ankle_")
            ) else ("R+14", "R+30")[index]
            observations.append(
                _english_observation(
                    outcome_id,
                    "all",
                    timepoint,
                    mean,
                    ci_first,
                    ci_second,
                    sample_size,
                    "Table III",
                    "4",
                )
            )

    for group_id, rows_by_outcome in _SEX_ROWS.items():
        for outcome_id, row in rows_by_outcome.items():
            timepoint = "R+14" if outcome_id.startswith("trunk_") else "R+5"
            observations.append(
                _english_observation(
                    outcome_id,
                    group_id,
                    timepoint,
                    *row,
                    "Table IV",
                    "5",
                )
            )

    for group_id, rows_by_outcome in _DEVICE_ROWS.items():
        for outcome_id, row in rows_by_outcome.items():
            timepoint = "R+14" if outcome_id.startswith("trunk_") else "R+5"
            observations.append(
                _english_observation(
                    outcome_id,
                    group_id,
                    timepoint,
                    *row,
                    "Table V",
                    "5",
                )
            )
    return observations


def _english_observation(
    outcome_id: str,
    group_id: str,
    timepoint: str,
    mean: float,
    ci_first: float,
    ci_second: float,
    sample_size: int,
    table: str,
    source_page: str,
) -> PublishedObservation:
    region, label = ENGLISH_OUTCOMES[outcome_id]
    group_label = _GROUP_LABELS[group_id]
    wording = (
        f"{label}, {group_label}, {timepoint}: N={sample_size}; "
        f"mean (95% CI) = {mean:.1f} ({ci_first:.1f}, {ci_second:.1f})."
    )
    return PublishedObservation(
        study_id="english-2015",
        record_key=f"english::{region.lower()}::{outcome_id}::{group_id}",
        measurement_name="Mean percent change from L-60",
        value=mean,
        unit="%",
        timepoint=timepoint,
        baseline="L-60",
        sample_size=sample_size,
        sample_size_status="reported",
        source_page=source_page,
        source_location=table,
        source_wording=wording,
        uncertainty_notes=(
            f"95% CI as printed: ({ci_first:.1f}, {ci_second:.1f}); "
            "group-level summary, not individual participant observations."
        ),
    )


def _fitts_observations() -> list[PublishedObservation]:
    source_values = (
        (
            "diameter",
            "Preflight value",
            98.0,
            1.0,
            "μm",
            "L-55 ± 2 days",
            540,
            "6",
            "Table 2",
            "All crew members, Pre-flight: n=540; 98 ± 1 μm.",
        ),
        (
            "diameter",
            "Postflight value",
            79.0,
            1.0,
            "μm",
            "R+0, landing day",
            458,
            "6",
            "Table 2",
            "All crew members, Post-flight: n=458; 79 ± 1* μm.",
        ),
        (
            "peak_force",
            "Preflight value",
            0.86,
            0.01,
            "mN",
            "L-55 ± 2 days",
            540,
            "7",
            "Table 3",
            "All crew members, Pre-flight: n=540; 0.86 ± 0.01 mN.",
        ),
        (
            "peak_force",
            "Postflight value",
            0.56,
            0.01,
            "mN",
            "R+0, landing day",
            458,
            "7",
            "Table 3",
            "All crew members, Post-flight: n=458; 0.56 ± 0.01* mN.",
        ),
    )
    observations = []
    for (
        outcome_id,
        measurement_name,
        value,
        sem,
        unit,
        timepoint,
        sample_size,
        source_page,
        source_location,
        source_wording,
    ) in source_values:
        observations.append(
            PublishedObservation(
                study_id="fitts-2010",
                record_key=f"fitts::soleus::{outcome_id}::type_i",
                measurement_name=measurement_name,
                value=value,
                unit=unit,
                timepoint=timepoint,
                baseline="L-55 ± 2 days" if "Postflight" in measurement_name else None,
                sample_size=sample_size,
                sample_size_status="reported",
                source_page=source_page,
                source_location=source_location,
                source_wording=source_wording,
                uncertainty_notes=(
                    f"SEM={sem:g} {unit}; n={sample_size} fibres. "
                    "Fibre counts are subsamples, not crew members; the study "
                    "analyzed nine crew members. No uncertainty for the paired "
                    "pre/post change is derived."
                ),
            )
        )
    return observations


PUBLISHED_OBSERVATIONS = tuple(
    _english_observations() + _fitts_observations()
)

ABSTRACT_CONTEXT_MEASUREMENTS = (
    MeasurementInput(
        study_id="gopalakrishnan-2010",
        muscle_or_outcome="ISS mission duration",
        measurement_name="Mean flight duration ± reported variability",
        value="181 ± 15",
        value_status="reported",
        unit="days",
        timepoint="Long-duration ISS mission",
        sample_size=4,
        sample_size_status="reported",
        source_page="1",
        source_location="Abstract, Methods",
        source_wording=(
            "before and after long-duration spaceflight (181 +/- 15 d)."
        ),
        verification_status="source_verified",
        uncertainty_notes=(
            "Abstract-only transcription. The definition of the reported "
            "variability is not specified here; duration is contextual and "
            "is not a model input."
        ),
    ),
    MeasurementInput(
        study_id="gopalakrishnan-2010",
        muscle_or_outcome="Broad regional muscle volume",
        measurement_name="Reported muscle volume change ranges",
        value="Calf: -10 to 16%; thigh: -4% to -7%; upper arm: +0.4 to -0.8%",
        value_status="reported",
        unit="% change",
        timepoint="Preflight to postflight",
        sample_size=4,
        sample_size_status="reported",
        source_page="1",
        source_location="Abstract, Results",
        source_wording=(
            "Muscle volume change was greater in the calf (-10 to 16%) than "
            "the thigh (-4% to -7%), but there was no change in the upper "
            "arm (+0.4 to -0.8%)."
        ),
        verification_status="source_verified",
        uncertainty_notes=(
            "Exact abstract wording only. The calf range is flagged as "
            "ambiguous/suspicious in the accessibility audit; ranges do not "
            "identify a specific compatible outcome and are context only."
        ),
    ),
    MeasurementInput(
        study_id="gopalakrishnan-2010",
        muscle_or_outcome="Knee, ankle, and elbow strength",
        measurement_name="Reported isometric/isokinetic strength change ranges",
        value=(
            "Knee: -10.4 to -24.1%; ankle: -4 to -22.3%; "
            "elbow: -7.5 to -16.7%"
        ),
        value_status="reported",
        unit="% change",
        timepoint="Preflight to postflight",
        sample_size=4,
        sample_size_status="reported",
        source_page="1",
        source_location="Abstract, Results",
        source_wording=(
            "Isometric and isokinetic strength changes at the knee (range "
            "-10.4 to -24.1%), ankle (range -4 to -22.3%), and elbow "
            "(range -7.5 to -16.7%) were observed."
        ),
        verification_status="source_verified",
        uncertainty_notes=(
            "Abstract-only ranges; individual tests, exact endpoint "
            "definitions, and outcome-specific sample sizes are unavailable. "
            "Context only; not engine inputs."
        ),
    ),
    MeasurementInput(
        study_id="gopalakrishnan-2010",
        muscle_or_outcome="Endurance test total work",
        measurement_name="Reported total-work change",
        value="-14",
        value_status="reported",
        unit="% change",
        timepoint="Postflight",
        sample_size=4,
        sample_size_status="reported",
        source_page="1",
        source_location="Abstract, Results",
        source_wording=(
            "Although there was an overall postflight decline in total work "
            "(-14%) during the endurance test"
        ),
        verification_status="source_verified",
        uncertainty_notes=(
            "Abstract-only result. Test details, exact comparison definition, "
            "and outcome-specific sample size are unavailable; context only."
        ),
    ),
    MeasurementInput(
        study_id="gopalakrishnan-2010",
        muscle_or_outcome="In-shoe peak force during exercise",
        measurement_name="ISS exercise force relative to 1-g values",
        value="Running: approximately 46%; cycling: approximately 50% lower",
        value_status="reported",
        unit="% lower than 1-g values",
        timepoint="In-flight exercise",
        sample_size=4,
        sample_size_status="reported",
        source_page="1",
        source_location="Abstract, Results",
        source_wording=(
            "The peak in-shoe forces during running and cycling on ISS were "
            "approximately 46% and 50% lower compared to 1-g values."
        ),
        verification_status="source_verified",
        uncertainty_notes=(
            "Abstract-only relative force values. Force units, detailed "
            "measurement protocol, and outcome-specific sample size are "
            "unavailable; not a countermeasure dose-response estimate."
        ),
    ),
)


def seed_reference_measurements(connection: sqlite3.Connection) -> int:
    """Add source-checked publication values without replacing library records."""
    existing_keys = {
        _database_key(row)
        for study_id in ("english-2015", "fitts-2010")
        for row in list_measurements(connection, study_id)
    }
    added = 0
    for observation in PUBLISHED_OBSERVATIONS:
        key = _observation_key(observation)
        if key in existing_keys:
            continue
        add_measurement(
            connection,
            MeasurementInput(
                study_id=observation.study_id,
                muscle_or_outcome=observation.record_key,
                measurement_name=observation.measurement_name,
                value=str(observation.value),
                value_status="reported",
                unit=observation.unit,
                timepoint=observation.timepoint,
                comparison_baseline=observation.baseline,
                sample_size=observation.sample_size,
                sample_size_status=observation.sample_size_status,
                source_page=observation.source_page,
                source_location=observation.source_location,
                source_wording=observation.source_wording,
                verification_status="source_verified",
                uncertainty_notes=observation.uncertainty_notes,
            ),
        )
        existing_keys.add(key)
        added += 1
    return added


def seed_abstract_context_measurements(connection: sqlite3.Connection) -> int:
    """Store source-checked abstract values as contextual, non-model evidence."""
    existing_keys = {
        (row["muscle_or_outcome"], row["measurement_name"], row["timepoint"])
        for row in list_measurements(connection, "gopalakrishnan-2010")
    }
    added = 0
    for measurement in ABSTRACT_CONTEXT_MEASUREMENTS:
        key = (
            measurement.muscle_or_outcome,
            measurement.measurement_name,
            measurement.timepoint,
        )
        if key in existing_keys:
            continue
        add_measurement(connection, measurement)
        existing_keys.add(key)
        added += 1
    return added


def find_verified_observation(
    connection: sqlite3.Connection,
    study_id: str,
    record_key: str,
    measurement_name: str,
    timepoint: str,
) -> dict[str, object] | None:
    """Retrieve only a value matching its curated source and verification data."""
    expected = next(
        (
            observation
            for observation in PUBLISHED_OBSERVATIONS
            if observation.study_id == study_id
            and observation.record_key == record_key
            and observation.measurement_name == measurement_name
            and observation.timepoint == timepoint
        ),
        None,
    )
    if expected is None:
        return None

    for row in list_measurements(connection, study_id):
        if (
            row["muscle_or_outcome"] == expected.record_key
            and row["measurement_name"] == expected.measurement_name
            and row["value_status"] == "reported"
            and row["verification_status"] == "source_verified"
            and row["timepoint"] == expected.timepoint
            and row["comparison_baseline"] == expected.baseline
            and row["sample_size"] == expected.sample_size
            and row["sample_size_status"] == expected.sample_size_status
            and row["source_page"] == expected.source_page
            and row["source_location"] == expected.source_location
            and row["source_wording"] == expected.source_wording
            and row["uncertainty_notes"] == expected.uncertainty_notes
            and _matches_expected_value(row["value"], expected.value)
        ):
            return row
    return None


def verified_english_recovery_observations(
    connection: sqlite3.Connection,
    record_key: str,
) -> list[dict[str, object]]:
    """Return only curated, verified postflight observations for one outcome."""
    timepoint_order = {"R+5": 5, "R+14": 14, "R+30": 30}
    observations = []
    for expected in PUBLISHED_OBSERVATIONS:
        if (
            expected.study_id != "english-2015"
            or expected.record_key != record_key
            or expected.measurement_name != "Mean percent change from L-60"
            or expected.timepoint not in timepoint_order
        ):
            continue
        row = find_verified_observation(
            connection,
            expected.study_id,
            expected.record_key,
            expected.measurement_name,
            expected.timepoint,
        )
        if row is None:
            continue

        ci_first, ci_second = _confidence_interval_values(
            expected.uncertainty_notes
        )
        observations.append(
            {
                "study_id": row["study_id"],
                "muscle_or_outcome": row["muscle_or_outcome"],
                "measurement_name": row["measurement_name"],
                "unit": row["unit"],
                "comparison_baseline": row["comparison_baseline"],
                "source_page": row["source_page"],
                "source_location": row["source_location"],
                "source_wording": row["source_wording"],
                "uncertainty_notes": row["uncertainty_notes"],
                "observation_id": (
                    f'{row["study_id"]}::{row["muscle_or_outcome"]}::'
                    f'{row["measurement_name"]}::{row["timepoint"]}'
                ),
                "timepoint": expected.timepoint,
                "days_after_return": timepoint_order[expected.timepoint],
                "mean_change": float(row["value"]),
                "ci_lower": min(ci_first, ci_second),
                "ci_upper": max(ci_first, ci_second),
                "sample_size": expected.sample_size,
            }
        )
    return sorted(observations, key=lambda item: int(item["days_after_return"]))


def _confidence_interval_values(notes: str) -> tuple[float, float]:
    prefix = "95% CI as printed: ("
    if not notes.startswith(prefix):
        raise ValueError("Curated English observations require a reported 95% CI.")
    values_text = notes[len(prefix) :].split(")", maxsplit=1)[0]
    first, second = (float(value.strip()) for value in values_text.split(","))
    return first, second


def _observation_key(observation: PublishedObservation) -> tuple[object, ...]:
    return (
        observation.study_id,
        observation.record_key,
        observation.measurement_name,
        str(observation.value),
        observation.unit,
        observation.timepoint,
        observation.baseline,
        observation.sample_size,
        observation.sample_size_status,
        observation.source_page,
        observation.source_location,
        observation.source_wording,
        "source_verified",
        observation.uncertainty_notes,
    )


def _database_key(row: dict[str, object]) -> tuple[object, ...]:
    return (
        row["study_id"],
        row["muscle_or_outcome"],
        row["measurement_name"],
        row["value"],
        row["unit"],
        row["timepoint"],
        row["comparison_baseline"],
        row["sample_size"],
        row["sample_size_status"],
        row["source_page"],
        row["source_location"],
        row["source_wording"],
        row["verification_status"],
        row["uncertainty_notes"],
    )


def _matches_expected_value(value: object, expected: float) -> bool:
    if value is None:
        return False
    try:
        return math.isclose(float(value), expected)
    except (TypeError, ValueError):
        return False
