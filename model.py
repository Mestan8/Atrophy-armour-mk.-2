"""Scenario analysis: selected evidence plus the flagged duration approximation.

Nothing here predicts an individual's or a mission's outcome. A scenario is a
set of published group results (one row per study, cohort and outcome, never
merged) and, for each, what the documented duration approximation gives at the
slider's mission length.
"""

from dataclasses import dataclass

from duration_model import DurationModel, model_for
from evidence_catalog import (
    Change,
    HarmonizedPoint,
    Series,
    calculate_change,
    duration_evidence,
    format_number,
    recovery_day_text,
)
from scenario_inputs import (
    Control,
    Selection,
    point_at,
    recovery_label,
    resolve_controls,
    selected_series,
)


__all__ = [
    "Change",
    "Scenario",
    "ScenarioRow",
    "analyze_scenario",
    "calculate_change",
]


@dataclass(frozen=True)
class ScenarioRow:
    """One series in the scenario."""

    series: Series
    point: HarmonizedPoint | None
    model: DurationModel | None
    model_output: dict[str, object] | None
    missing_reason: str | None
    association: dict[str, object] | None


@dataclass(frozen=True)
class Scenario:
    selection: Selection
    controls: tuple[Control, ...]
    rows: tuple[ScenarioRow, ...]
    duration_days: float
    slider_min: float
    slider_max: float
    slider_default: float
    supported_low: float | None
    supported_high: float | None


def _association(series: Series) -> dict[str, object] | None:
    """A within-study duration association for this outcome, if the paper prints one."""
    for item in duration_evidence()["within_study_associations"]:
        if item["study_id"] == series.study_id and series.outcome_id in item["values"]:
            return {**item, "value": item["values"][series.outcome_id]}
    return None


def _clean_duration(requested: object, default: float, maximum: float) -> float:
    try:
        value = float(requested)
    except (TypeError, ValueError):
        return default
    if value != value:  # NaN
        return default
    return min(max(round(value), 0.0), maximum)


def analyze_scenario(requested: dict[str, object]) -> Scenario:
    """Resolve the controls and evaluate every matching series."""
    selection, controls = resolve_controls(requested)
    prepared = []
    for series in selected_series(selection):
        point = point_at(series, selection.recovery)
        missing = None
        model = None
        if point is None:
            reported = ", ".join(
                recovery_day_text(item.observation) for item in series.points
            )
            missing = (
                f"Not measured at {recovery_label(selection.recovery)}. "
                f"Reported timepoints: {reported}."
            )
        else:
            model = model_for(series, point)
        prepared.append((series, point, model, missing))

    models = [model for _, _, model, _ in prepared if model is not None]
    slider_max = max((model.slider_max for model in models), default=240.0)
    slider_default = models[0].default_day if models else 180.0
    duration = _clean_duration(requested.get("duration"), round(slider_default), slider_max)
    lows = {model.supported_low for model in models}
    highs = {model.supported_high for model in models}

    rows = tuple(
        ScenarioRow(
            series=series,
            point=point,
            model=model,
            model_output=None if model is None else model.evaluate(duration),
            missing_reason=missing,
            association=_association(series),
        )
        for series, point, model, missing in prepared
    )
    return Scenario(
        selection=selection,
        controls=controls,
        rows=rows,
        duration_days=duration,
        slider_min=0.0,
        slider_max=slider_max,
        slider_default=float(round(slider_default)),
        supported_low=lows.pop() if len(lows) == 1 else None,
        supported_high=highs.pop() if len(highs) == 1 else None,
    )


def describe_change(value: float) -> str:
    direction = "lower" if value < 0 else "higher"
    return f"{format_number(abs(round(value, 1)))}% {direction} than the study's own baseline"
