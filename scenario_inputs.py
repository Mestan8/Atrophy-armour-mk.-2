"""Scenario input options, units, and study-specific validation."""

from dataclasses import dataclass

from scenario_evidence import (
    ENGLISH_OUTCOMES,
    PUBLISHED_OBSERVATIONS,
    PublishedObservation,
)


MISSION_DURATION_MIN_DAYS = 90
MISSION_DURATION_MAX_DAYS = 240
MISSION_DURATION_DEFAULT_DAYS = 177

FITTS_OUTCOME_UNITS = {
    "diameter": ("Fibre diameter", "μm"),
    "cross_sectional_area": ("Fibre cross-sectional area", "μm²"),
    "peak_force": ("Peak isometric fibre force", "mN"),
    "shortening_velocity": ("Maximal unloaded shortening velocity", "FL s⁻¹"),
    "peak_power": ("Peak fibre power", "mW"),
}

_ENGLISH_MEASUREMENT = "Mean percent change from L-60"
_FITTS_MEASUREMENT_PAIRS = {"Preflight value", "Postflight value"}


@dataclass(frozen=True)
class ScenarioInputs:
    """The five categorical inputs and one mission-duration context value."""

    study_id: str
    region: str
    outcome_id: str
    comparison_group: str
    timepoint: str
    mission_duration_days: int


def allowed_regions(study_id: str) -> tuple[str, ...]:
    """Return anatomical targets with complete curated numerical observations."""
    return tuple(
        dict.fromkeys(
            region
            for region, _ in _available_outcomes(study_id).values()
        )
    )


def allowed_scenario_outcomes(study_id: str) -> dict[str, tuple[str, str]]:
    """Map supported outcome IDs to their target and readable label."""
    return _available_outcomes(study_id)


def allowed_outcomes(study_id: str, region: str) -> dict[str, str]:
    """Map supported outcome IDs to labels for the selected target."""
    return {
        outcome_id: label
        for outcome_id, (outcome_region, label) in _available_outcomes(
            study_id
        ).items()
        if outcome_region == region
    }


def allowed_comparison_groups(
    study_id: str,
    region: str | None = None,
    outcome_id: str | None = None,
) -> dict[str, str]:
    """Return only comparisons with complete curated measurements."""
    labels = {
        "all": "All participants",
        "men": "Men",
        "women": "Women",
        "ired": "iRED era",
        "ared": "ARED era",
        "type_i": "Slow type I fibres",
        "type_ii": "Fast type II fibres",
    }
    groups = {
        _group_for_observation(observation)
        for observation in _observations_for(study_id, region, outcome_id)
        if _has_complete_observation(study_id, observation)
    }
    return {
        group: labels[group]
        for group in labels
        if group in groups
    }


def allowed_timepoints(
    study_id: str,
    region: str,
    comparison_group: str,
    outcome_id: str | None = None,
) -> tuple[str, ...]:
    """List only timepoints for which the selected comparison is curated."""
    if study_id == "fitts-2010":
        matching = [
            item
            for item in _observations_for(study_id, region, outcome_id)
            if _group_for_observation(item) == comparison_group
        ]
        return (
            ("preflight_to_landing",)
            if matching and _has_complete_observation(study_id, matching[0])
            else ()
        )
    return tuple(
        dict.fromkeys(
            item.timepoint
            for item in _observations_for(study_id, region, outcome_id)
            if _group_for_observation(item) == comparison_group
            and _has_complete_observation(study_id, item)
        )
    )


def _available_outcomes(study_id: str) -> dict[str, tuple[str, str]]:
    if study_id == "english-2015":
        supported_ids = {
            _outcome_for_observation(item)
            for item in _observations_for(study_id)
            if item.measurement_name == _ENGLISH_MEASUREMENT
        }
        return {
            outcome_id: details
            for outcome_id, details in ENGLISH_OUTCOMES.items()
            if outcome_id in supported_ids
        }
    if study_id == "fitts-2010":
        supported_targets = {
            _outcome_for_observation(item): _region_for_observation(item)
            for item in _observations_for(study_id)
            if _has_complete_observation(study_id, item)
        }
        return {
            outcome_id: (supported_targets[outcome_id], label)
            for outcome_id, (label, _) in FITTS_OUTCOME_UNITS.items()
            if outcome_id in supported_targets
            and supported_targets[outcome_id] is not None
        }
    return {}


def _observations_for(
    study_id: str,
    region: str | None = None,
    outcome_id: str | None = None,
) -> tuple[PublishedObservation, ...]:
    return tuple(
        observation
        for observation in PUBLISHED_OBSERVATIONS
        if observation.study_id == study_id
        and (region is None or _region_for_observation(observation) == region)
        and (
            outcome_id is None
            or _outcome_for_observation(observation) == outcome_id
        )
    )


def _region_for_observation(observation: PublishedObservation) -> str | None:
    if observation.study_id == "english-2015":
        return observation.record_key.split("::")[1].title()
    if observation.study_id == "fitts-2010":
        return observation.record_key.split("::")[1].title()
    return None


def _outcome_for_observation(observation: PublishedObservation) -> str:
    return observation.record_key.split("::")[2]


def _group_for_observation(observation: PublishedObservation) -> str:
    return observation.record_key.split("::")[3]


def _has_complete_observation(
    study_id: str, observation: PublishedObservation
) -> bool:
    if study_id == "english-2015":
        return observation.measurement_name == _ENGLISH_MEASUREMENT
    if study_id != "fitts-2010":
        return False
    record_key = observation.record_key
    measurement_names = {
        item.measurement_name
        for item in PUBLISHED_OBSERVATIONS
        if item.study_id == study_id and item.record_key == record_key
    }
    return _FITTS_MEASUREMENT_PAIRS.issubset(measurement_names)


def validate_scenario(inputs: ScenarioInputs) -> None:
    """Reject selections that have no compatible study or measurement."""
    if inputs.study_id not in {"english-2015", "fitts-2010"}:
        raise ValueError("Select one of the studies in the Study Library.")
    if inputs.region not in allowed_regions(inputs.study_id):
        raise ValueError("The selected anatomical region is not in this study.")
    if inputs.outcome_id not in allowed_outcomes(inputs.study_id, inputs.region):
        raise ValueError("The selected outcome is not available for this region.")
    if inputs.comparison_group not in allowed_comparison_groups(
        inputs.study_id, inputs.region, inputs.outcome_id
    ):
        raise ValueError("The selected comparison group is not available.")
    if inputs.timepoint not in allowed_timepoints(
        inputs.study_id,
        inputs.region,
        inputs.comparison_group,
        inputs.outcome_id,
    ):
        raise ValueError("The selected timepoint is not reported for this comparison.")
    if (
        isinstance(inputs.mission_duration_days, bool)
        or not isinstance(inputs.mission_duration_days, int)
        or not MISSION_DURATION_MIN_DAYS
        <= inputs.mission_duration_days
        <= MISSION_DURATION_MAX_DAYS
    ):
        raise ValueError(
            "Mission duration must be a whole number between "
            f"{MISSION_DURATION_MIN_DAYS} and {MISSION_DURATION_MAX_DAYS} days."
        )
