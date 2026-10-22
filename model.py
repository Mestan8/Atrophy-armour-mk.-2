"""Validated, evidence-limited scenario analysis; no mission-loss prediction."""

from dataclasses import dataclass
import math
import sqlite3

from scenario_evidence import find_verified_observation
from scenario_inputs import (
    FITTS_OUTCOME_UNITS,
    ScenarioInputs,
    allowed_comparison_groups,
    allowed_outcomes,
    validate_scenario,
)
from study_library import get_study, list_measurements


_ENGLISH_DURATION_ENVELOPE = (105, 205)
_FITTS_DURATION_RANGE = (161, 192)


@dataclass(frozen=True)
class Change:
    absolute_change: float
    percent_change: float
    unit: str


@dataclass(frozen=True)
class ScenarioResult:
    analysis_mode: str
    study_id: str
    study_title: str
    population: str
    region: str
    outcome: str
    unit: str
    comparison_group: str
    timepoint: str
    mission_duration_days: int
    mean_change: float | None
    absolute_change: float | None
    preflight_value: float | None
    postflight_value: float | None
    sample_size: int | None
    confidence_interval: tuple[float, float] | None
    source_page: str | None
    source_location: str | None
    source_wording: str | None
    interpretation: str
    warnings: tuple[str, ...]
    preflight_sample_size: int | None = None
    postflight_sample_size: int | None = None
    preflight_standard_error: float | None = None
    postflight_standard_error: float | None = None


def calculate_change(
    preflight_value: float | None,
    postflight_value: float | None,
    unit: str | None,
) -> Change:
    """Calculate a post-minus-pre difference and percent change from preflight."""
    if preflight_value is None or postflight_value is None:
        raise ValueError("Both preflight and postflight values are required.")
    if unit is None or not unit.strip():
        raise ValueError("A unit is required to interpret the absolute change.")
    try:
        preflight_value = float(preflight_value)
        postflight_value = float(postflight_value)
    except (TypeError, ValueError) as error:
        raise ValueError("Preflight and postflight values must be numbers.") from error
    if not math.isfinite(preflight_value) or not math.isfinite(postflight_value):
        raise ValueError("Preflight and postflight values must be finite numbers.")
    if preflight_value == 0:
        raise ValueError("Percent change is undefined when the preflight value is zero.")
    absolute_change = postflight_value - preflight_value
    return Change(
        absolute_change=absolute_change,
        percent_change=(absolute_change / preflight_value) * 100.0,
        unit=unit,
    )


def mission_duration_warning(
    study_id: str,
    mission_duration_days: int,
) -> str | None:
    """Warn when duration is outside the selected study's reported duration data."""
    if study_id == "english-2015":
        low, high = _ENGLISH_DURATION_ENVELOPE
        basis = (
            "the 105–205 day envelope spanned by the reported cohort/subgroup "
            "means ± one SD (not an individual minimum/maximum)"
        )
    elif study_id == "fitts-2010":
        low, high = _FITTS_DURATION_RANGE
        basis = "the observed 161–192 day flight range"
    else:
        return "The selected study has no mission-duration evidence."
    if low <= mission_duration_days <= high:
        return None
    return (
        f"{mission_duration_days} days is outside {basis}. "
        "Mission duration is shown for context only; the engine does not "
        "estimate a duration-dependent change."
    )


def analyze_scenario(
    connection: sqlite3.Connection,
    inputs: ScenarioInputs,
) -> ScenarioResult:
    """Retrieve a verified publication observation and interpret it descriptively."""
    validate_scenario(inputs)
    study = get_study(connection, inputs.study_id)
    if study is None:
        raise ValueError("The selected study is missing from the Study Library.")

    groups = allowed_comparison_groups(inputs.study_id)
    outcomes = allowed_outcomes(inputs.study_id, inputs.region)
    warnings: list[str] = []
    duration_warning = mission_duration_warning(
        inputs.study_id, inputs.mission_duration_days
    )
    if duration_warning is not None:
        warnings.append(duration_warning)

    if inputs.study_id == "english-2015":
        observation = find_verified_observation(
            connection,
            inputs.study_id,
            f"english::{inputs.region.lower()}::{inputs.outcome_id}::"
            f"{inputs.comparison_group}",
            "Mean percent change from L-60",
            inputs.timepoint,
        )
        outcome_label = outcomes[inputs.outcome_id]
        if observation is None:
            warnings.append(
                "No matching source-verified Study Library measurement is available. "
                "An unverified or altered record is not used."
            )
            return _result(
                inputs,
                study,
                "Observed-data comparison (source value unavailable)",
                groups[inputs.comparison_group],
                outcome_label,
                "% mean change from L-60",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "No numerical result is shown because the required table value "
                "could not be matched to a source-verified Study Library record.",
                warnings,
            )

        value = float(observation["value"])
        confidence_interval = _confidence_interval(
            str(observation["uncertainty_notes"])
        )
        sample_size = (
            int(observation["sample_size"])
            if observation["sample_size"] is not None
            else None
        )
        direction = "decrease" if value < 0 else "increase"
        interpretation = (
            f"The paper reports a {abs(value):.1f}% mean {direction} from the "
            f"L-60 preflight value at {inputs.timepoint} (n={sample_size}). "
            "A negative sign indicates a lower postflight group mean; this is "
            "not a measurement of change during the mission."
        )
        if confidence_interval is not None:
            interpretation += (
                f" The reported 95% CI is "
                f"{confidence_interval[0]:.1f}% to "
                f"{confidence_interval[1]:.1f}%."
            )
        if inputs.comparison_group in {"men", "women"}:
            warnings.append(
                "The paper reports no statistically significant sex difference; "
                "these subgroup values are descriptive, not sex-specific forecasts."
            )
        elif inputs.comparison_group in {"ired", "ared"}:
            warnings.append(
                "iRED and ARED correspond to different expedition eras, not a "
                "randomized trial; the paper reports no significant hardware "
                "interaction. This comparison is not a causal device effect."
            )
        return _result(
            inputs,
            study,
            "Observed-data comparison",
            groups[inputs.comparison_group],
            outcome_label,
            "% mean change from L-60",
            value,
            None,
            None,
            None,
            sample_size,
            confidence_interval,
            str(observation["source_page"]),
            str(observation["source_location"]),
            str(observation["source_wording"]),
            interpretation,
            warnings,
        )

    outcome_label, raw_unit = FITTS_OUTCOME_UNITS[inputs.outcome_id]
    record_key = (
        f"fitts::{inputs.region.lower()}::{inputs.outcome_id}::"
        f"{inputs.comparison_group}"
    )
    preflight = find_verified_observation(
        connection, inputs.study_id, record_key, "Preflight value", "L-55 ± 2 days"
    )
    postflight = find_verified_observation(
        connection,
        inputs.study_id,
        record_key,
        "Postflight value",
        "R+0, landing day",
    )
    if preflight is None or postflight is None:
        unverified = any(
            row["study_id"] == inputs.study_id
            and row["muscle_or_outcome"] == record_key
            and row["verification_status"] != "source_verified"
            for row in list_measurements(connection, inputs.study_id)
        )
        note = (
            " A matching unverified record exists and was excluded."
            if unverified
            else ""
        )
        warnings.append(
            "No curated, source-verified preflight/postflight values support this "
            "muscle, fibre type, and outcome combination."
            + note
        )
        warnings.append(
            "Fitts et al. report individual fibre and participant-level summaries; "
            "fibre counts are not independent crew members. Further source review "
            "must preserve participant, muscle, fibre type, units, and variability."
        )
        return _result(
            inputs,
            study,
            "Observed-data comparison (source values unavailable)",
            groups[inputs.comparison_group],
            outcome_label,
            raw_unit,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "No numerical result is shown for this selection. The source contains "
            "fibre-level observations, but this specific comparison has not been "
            "curated as a verified Study Library measurement.",
            warnings,
        )

    pre_value = float(preflight["value"])
    post_value = float(postflight["value"])
    change = calculate_change(pre_value, post_value, raw_unit)
    warnings.append(
        "This percentage is calculated from published group mean levels; it is "
        "not the mean of individual astronauts' percent changes."
    )
    warnings.append(
        "The tables report SEM and fibre counts for each group mean. Those "
        "fibre counts are not crew sample sizes, and no CI or SEM for the "
        "paired change is calculated."
    )
    source_words = (
        f"Preflight: {preflight['source_wording']} "
        f"Postflight: {postflight['source_wording']}"
    )
    return _result(
        inputs,
        study,
        "Descriptive change from published group means",
        groups[inputs.comparison_group],
        outcome_label,
        raw_unit,
        change.percent_change,
        change.absolute_change,
        pre_value,
        post_value,
        None,
        None,
        str(postflight["source_page"]),
        str(postflight["source_location"]),
        source_words,
        (
            f"Published group values changed from {pre_value:g} to "
            f"{post_value:g} {raw_unit}. The derived post-minus-pre difference "
            f"is {change.absolute_change:g} {raw_unit}; the ratio of those "
            f"group means is {change.percent_change:.1f}%."
        ),
        warnings,
        preflight_sample_size=int(preflight["sample_size"]),
        postflight_sample_size=int(postflight["sample_size"]),
        preflight_standard_error=_standard_error(
            str(preflight["uncertainty_notes"])
        ),
        postflight_standard_error=_standard_error(
            str(postflight["uncertainty_notes"])
        ),
    )


def _standard_error(notes: str) -> float | None:
    prefix = "SEM="
    if not notes.startswith(prefix):
        return None
    value_text = notes[len(prefix) :].split(maxsplit=1)[0].rstrip(";")
    try:
        return float(value_text)
    except ValueError:
        return None


def _confidence_interval(notes: str) -> tuple[float, float] | None:
    prefix = "95% CI as printed: ("
    if not notes.startswith(prefix):
        return None
    values_text = notes[len(prefix) :].split(")", maxsplit=1)[0]
    try:
        first, second = (float(value.strip()) for value in values_text.split(","))
    except (TypeError, ValueError):
        return None
    return min(first, second), max(first, second)


def _result(
    inputs: ScenarioInputs,
    study: dict[str, object],
    analysis_mode: str,
    comparison_group: str,
    outcome: str,
    unit: str,
    mean_change: float | None,
    absolute_change: float | None,
    preflight_value: float | None,
    postflight_value: float | None,
    sample_size: int | None,
    confidence_interval: tuple[float, float] | None,
    source_page: str | None,
    source_location: str | None,
    source_wording: str | None,
    interpretation: str,
    warnings: list[str],
    *,
    preflight_sample_size: int | None = None,
    postflight_sample_size: int | None = None,
    preflight_standard_error: float | None = None,
    postflight_standard_error: float | None = None,
) -> ScenarioResult:
    return ScenarioResult(
        analysis_mode=analysis_mode,
        study_id=inputs.study_id,
        study_title=str(study["title"]),
        population=str(study["population"]),
        region=inputs.region,
        outcome=outcome,
        unit=unit,
        comparison_group=comparison_group,
        timepoint=inputs.timepoint,
        mission_duration_days=inputs.mission_duration_days,
        mean_change=mean_change,
        absolute_change=absolute_change,
        preflight_value=preflight_value,
        postflight_value=postflight_value,
        sample_size=sample_size,
        confidence_interval=confidence_interval,
        source_page=source_page,
        source_location=source_location,
        source_wording=source_wording,
        interpretation=interpretation,
        warnings=tuple(warnings),
        preflight_sample_size=preflight_sample_size,
        postflight_sample_size=postflight_sample_size,
        preflight_standard_error=preflight_standard_error,
        postflight_standard_error=postflight_standard_error,
    )
