"""Unified evidence catalog: loading, schema validation, and harmonized series.

Every quantitative value the application shows comes from ``data/evidence``.
The JSON files there are compact (shared fields are written once per block);
this module expands them into one flat ``Observation`` per printed value and
refuses to load anything that lacks provenance or a ``value_type``.

Studies are never pooled here. A ``Series`` is one outcome in one cohort of one
study, and percent changes are either copied from the source or calculated from
that same study's own baseline.
"""

from dataclasses import asdict, dataclass, field
from functools import cache
import json
import math
from pathlib import Path
import re

from study_library import STUDIES


EVIDENCE_DIRECTORY = Path(__file__).resolve().parent / "data" / "evidence"
EXTERNAL_SOURCES_FILE = "external_sources.json"
DURATION_EVIDENCE_FILE = "duration_evidence.json"
_NON_STUDY_FILES = {EXTERNAL_SOURCES_FILE, DURATION_EVIDENCE_FILE}

# The harmonized measurement categories, in display order. "recovery" is a view
# over the postflight timepoints of the other six, not a separate kind of value.
CATEGORIES = {
    "muscle_size": "Muscle size",
    "strength": "Whole-joint strength",
    "endurance": "Muscle endurance / work capacity",
    "fibre": "Fibre-level properties",
    "body_composition": "Body composition",
    "aerobic": "Aerobic capacity",
}
RECOVERY_CATEGORY = ("recovery", "Recovery")
CATEGORY_DESCRIPTIONS = {
    "muscle_size": "Muscle volume or cross-sectional area from MRI or CT.",
    "strength": "Isokinetic or isometric torque, force, power and one-repetition maximum.",
    "endurance": "Total work over a set of repetitions.",
    "fibre": "Single-fibre diameter, cross-sectional area, force and velocity from biopsies.",
    "body_composition": "Lean mass, fat mass and muscle attenuation from DXA or CT.",
    "aerobic": "VO2peak and related cycle-test measures.",
    "recovery": "Outcomes above that were measured at more than one postflight day.",
}
REGIONS = {
    "thigh_knee": "Thigh / knee",
    "calf_ankle": "Calf / ankle",
    "trunk": "Trunk",
    "whole_leg": "Whole leg (multi-joint)",
    "upper_body": "Upper body",
    "whole_body": "Whole body",
    "not_reported": "Region not reported",
}
SUBGROUPS = {"all": "All crew (as reported)", "men": "Men", "women": "Women"}
VALUE_TYPES = {
    "reported": "Reported: copied from the source as printed.",
    "calculated": "Calculated: arithmetic on reported values.",
    "digitized": "Digitized: read off a published figure.",
    "approximation": "Approximation: an assumption, interpolation or fit that the source does not prove.",
}
MEASURE_KINDS = {
    "level",
    "percent_change",
    "percent_of_baseline",
    "proportion_change",
}
DISPERSION_LENGTHS = {
    "SD": 1,
    "SE": 1,
    "SEM": 1,
    "95% CI": 2,
    "range": 2,
    "none": 0,
}
VERIFICATION_STATUSES = {
    "rendered_page_checked": "Checked against the rendered PDF page",
    "text_layer_only": "Read from the PDF text layer only",
    "unverified": "Not yet verified",
}
NOT_REPORTED = "not reported"

_STUDY_FILES = {str(study["id"]): str(study["source_file"]) for study in STUDIES}
_CELL = re.compile(
    r"^\s*(?P<value>[+\-−]?\d+(?:\.\d+)?)\s*±\s*(?P<spread>\d+(?:\.\d+)?)"
)


class EvidenceSchemaError(ValueError):
    """An evidence record is missing something the evidence rules require."""


@dataclass(frozen=True)
class Change:
    absolute_change: float
    percent_change: float
    unit: str


def calculate_change(
    preflight_value: float | None,
    postflight_value: float | None,
    unit: str | None,
) -> Change:
    """Post-minus-pre difference and percent change from the preflight value."""
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


@dataclass(frozen=True)
class Observation:
    """One value as printed in a source, with everything needed to trace it."""

    id: str
    study_id: str
    outcome_category: str
    outcome_id: str
    outcome_name: str
    region: str
    muscle_or_joint: str
    biological_level: str
    measure_kind: str
    unit: str
    statistic_type: str
    value: float | None
    dispersion_type: str
    dispersion: tuple[float, ...]
    n: int | None
    n_counts: str
    cohort_id: str
    cohort: str
    subgroup: str
    sex: str
    countermeasure_id: str
    countermeasure: str
    mission_duration: dict
    baseline_timepoint: str
    timepoint: str
    timepoint_kind: str
    recovery_day: float | None
    recovery_window: tuple[float, float] | None
    source_file: str
    pdf_page: int
    table_or_figure: str
    source_wording: str
    value_type: str
    formula: str | None
    verification_status: str
    notes: str
    exclude_from_charts: str | None = None

    @property
    def series_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.study_id,
            self.outcome_id,
            self.cohort_id,
            self.subgroup,
            self.countermeasure_id,
        )

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["dispersion"] = list(self.dispersion)
        if self.recovery_window is not None:
            data["recovery_window"] = list(self.recovery_window)
        return data


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _parse_cell(cell: str) -> tuple[float, float]:
    match = _CELL.match(cell)
    if match is None:
        raise EvidenceSchemaError(f"Cannot read the printed cell {cell!r}.")
    return (
        float(match["value"].replace("−", "-")),
        float(match["spread"]),
    )


def _expand_file(document: dict) -> list[dict]:
    """Turn the compact per-study layout into one dictionary per observation."""
    study_id = document["study_id"]
    presets = document.get("presets", {})
    cell_notes = document.get("cell_notes", {})
    records: list[dict] = []
    for block in document["blocks"]:
        base = {
            "study_id": study_id,
            **document.get("defaults", {}),
            **block.get("defaults", {}),
        }
        columns = block.get("columns", document.get("columns"))
        for row in block["rows"]:
            fields = dict(zip(block["fields"], row, strict=True))
            if "cells" not in fields:
                records.append({**base, **fields})
                continue
            cells = fields.pop("cells")
            counts = fields.pop("ns", None)
            row_label = fields.pop("row_label")
            for index, (column, cell) in enumerate(zip(columns, cells, strict=True)):
                if cell is None:
                    continue
                column_fields = {
                    key: value
                    for key, value in column.items()
                    if key not in {"use", "label"}
                }
                value, spread = _parse_cell(cell)
                record = {
                    **base,
                    **presets.get(column.get("use"), {}),
                    **column_fields,
                    **fields,
                    "value": value,
                    "dispersion": [spread],
                    "source_wording": f'{row_label} | {column["label"]}: {cell}',
                    "_column_label": column["label"],
                }
                if counts is not None:
                    record["n"] = counts[index]
                records.append(record)
    for record in records:
        outcome_id = record.get("outcome_id")
        labels = (record.pop("_column_label", None), record.get("timepoint"), "*")
        extra = [
            cell_notes[f"{outcome_id}|{label}"]
            for label in labels
            if label is not None and f"{outcome_id}|{label}" in cell_notes
        ]
        if extra:
            record["notes"] = " ".join(
                part for part in (record.get("notes"), *extra) if part
            )
    return records


def _require_text(record: dict, name: str) -> str:
    value = record.get(name)
    if not isinstance(value, str) or not value.strip():
        raise EvidenceSchemaError(
            f'{record.get("study_id")}/{record.get("outcome_id")}: '
            f"'{name}' is required."
        )
    return value.strip()


def build_observation(record: dict) -> Observation:
    """Validate one expanded record and return it as an ``Observation``."""
    record = dict(record)
    study_id = _require_text(record, "study_id")
    if study_id not in _STUDY_FILES:
        raise EvidenceSchemaError(f"'{study_id}' is not a Study Library study.")
    label = f'{study_id}/{record.get("outcome_id")}'

    def fail(message: str) -> EvidenceSchemaError:
        return EvidenceSchemaError(f"{label}: {message}")

    for name in (
        "outcome_id",
        "outcome_name",
        "muscle_or_joint",
        "biological_level",
        "unit",
        "statistic_type",
        "n_counts",
        "cohort_id",
        "cohort",
        "sex",
        "countermeasure_id",
        "countermeasure",
        "baseline_timepoint",
        "timepoint",
        "table_or_figure",
        "source_wording",
    ):
        _require_text(record, name)

    choices = (
        ("outcome_category", CATEGORIES),
        ("region", REGIONS),
        ("measure_kind", MEASURE_KINDS),
        ("subgroup", SUBGROUPS),
        ("value_type", VALUE_TYPES),
        ("verification_status", VERIFICATION_STATUSES),
        ("dispersion_type", DISPERSION_LENGTHS),
        ("timepoint_kind", {"preflight", "postflight"}),
    )
    for name, allowed in choices:
        if record.get(name) not in allowed:
            raise fail(f"'{name}' must be one of {sorted(allowed)}.")

    dispersion = tuple(float(item) for item in record.get("dispersion") or ())
    if len(dispersion) != DISPERSION_LENGTHS[record["dispersion_type"]]:
        raise fail(
            f"dispersion {list(dispersion)} does not fit "
            f'dispersion_type {record["dispersion_type"]}.'
        )

    value = record.get("value")
    formula = record.get("formula")
    if value is None and record.get("value_rule") == "ci_midpoint":
        if record["dispersion_type"] != "95% CI":
            raise fail("a CI midpoint needs a 95% CI.")
        value = round((dispersion[0] + dispersion[1]) / 2, 2)
    if value is None and record["dispersion_type"] != "range":
        raise fail("a value is required unless the source prints only a range.")
    if value is not None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise fail("value must be a number.")
        if not math.isfinite(value):
            raise fail("value must be finite.")
        value = float(value)

    if record["value_type"] in {"calculated", "approximation"} and not formula:
        raise fail("calculated and approximated values need a formula.")
    if record["value_type"] in {"approximation", "digitized"} and not record.get(
        "notes"
    ):
        raise fail("approximated and digitized values need an explanation in notes.")

    n = record.get("n")
    if n is not None and (isinstance(n, bool) or not isinstance(n, int) or n < 1):
        raise fail("n must be a positive whole number or null.")

    pdf_page = record.get("pdf_page")
    if isinstance(pdf_page, bool) or not isinstance(pdf_page, int) or pdf_page < 1:
        raise fail("pdf_page must be a positive whole number.")

    recovery_day = record.get("recovery_day")
    window = record.get("recovery_window")
    if record["timepoint_kind"] == "preflight" and recovery_day is not None:
        raise fail("a preflight value cannot have a recovery day.")
    if recovery_day is not None and recovery_day < 0:
        raise fail("recovery_day cannot be negative.")
    if window is not None:
        window = (float(window[0]), float(window[1]))
        if not window[0] <= window[1]:
            raise fail("recovery_window must run from earlier to later.")

    duration = record.get("mission_duration")
    if not isinstance(duration, dict):
        raise fail("mission_duration is required.")
    if duration.get("value") is None and not duration.get("range"):
        raise fail("mission_duration needs a value or a range.")
    if not duration.get("wording") or not duration.get("pdf_page"):
        raise fail("mission_duration needs its source wording and PDF page.")

    timepoint_part = _slug(record["timepoint"])[:60]
    identifier = ":".join(
        (
            study_id,
            record["outcome_id"],
            record["cohort_id"],
            record["subgroup"],
            record["measure_kind"],
            timepoint_part,
        )
    )
    return Observation(
        id=identifier,
        study_id=study_id,
        outcome_category=record["outcome_category"],
        outcome_id=record["outcome_id"],
        outcome_name=record["outcome_name"],
        region=record["region"],
        muscle_or_joint=record["muscle_or_joint"],
        biological_level=record["biological_level"],
        measure_kind=record["measure_kind"],
        unit=record["unit"],
        statistic_type=record["statistic_type"],
        value=value,
        dispersion_type=record["dispersion_type"],
        dispersion=dispersion,
        n=n,
        n_counts=record["n_counts"],
        cohort_id=record["cohort_id"],
        cohort=record["cohort"],
        subgroup=record["subgroup"],
        sex=record["sex"],
        countermeasure_id=record["countermeasure_id"],
        countermeasure=record["countermeasure"],
        mission_duration=duration,
        baseline_timepoint=record["baseline_timepoint"],
        timepoint=record["timepoint"],
        timepoint_kind=record["timepoint_kind"],
        recovery_day=None if recovery_day is None else float(recovery_day),
        recovery_window=window,
        source_file=_STUDY_FILES[study_id],
        pdf_page=pdf_page,
        table_or_figure=record["table_or_figure"],
        source_wording=record["source_wording"],
        value_type=record["value_type"],
        formula=formula,
        verification_status=record["verification_status"],
        notes=record.get("notes") or "",
        exclude_from_charts=record.get("exclude_from_charts"),
    )


def load_observations(
    directory: str | Path = EVIDENCE_DIRECTORY,
) -> tuple[Observation, ...]:
    """Read every study file, validate each record, and reject duplicate ids."""
    observations: list[Observation] = []
    seen: set[str] = set()
    for path in sorted(Path(directory).glob("*.json")):
        if path.name in _NON_STUDY_FILES:
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        for record in _expand_file(document):
            observation = build_observation(record)
            if observation.id in seen:
                raise EvidenceSchemaError(f"Duplicate observation id {observation.id}.")
            seen.add(observation.id)
            observations.append(observation)
    return tuple(observations)


@cache
def catalog() -> tuple[Observation, ...]:
    """The curated catalog, loaded once per process."""
    return load_observations()


@cache
def external_sources() -> tuple[dict, ...]:
    """External supporting evidence, kept apart from the Study Library."""
    path = EVIDENCE_DIRECTORY / EXTERNAL_SOURCES_FILE
    sources = json.loads(path.read_text(encoding="utf-8"))["sources"]
    for source in sources:
        for name in ("id", "citation", "url", "access", "population", "evidence_type"):
            if not source.get(name):
                raise EvidenceSchemaError(
                    f'External source {source.get("id")} needs {name}.'
                )
    return tuple(sources)


@cache
def duration_evidence() -> dict:
    """Within-library links between mission duration and outcome (context only)."""
    path = EVIDENCE_DIRECTORY / DURATION_EVIDENCE_FILE
    return json.loads(path.read_text(encoding="utf-8"))


def external_source(source_id: str) -> dict:
    for source in external_sources():
        if source["id"] == source_id:
            return source
    raise KeyError(source_id)


# --- Harmonized view -----------------------------------------------------------


@dataclass(frozen=True)
class HarmonizedPoint:
    """One postflight timepoint of a series on the common percent-change axis."""

    observation: Observation
    percent_change: float | None
    low: float | None
    high: float | None
    dispersion_text: str
    value_type: str
    formula: str | None
    original_text: str
    baseline_text: str
    plottable: bool
    not_plotted_reason: str | None

    @property
    def recovery_day(self) -> float | None:
        return self.observation.recovery_day


@dataclass(frozen=True)
class Series:
    """One outcome in one cohort of one study, across its postflight timepoints."""

    key: tuple[str, str, str, str, str]
    points: tuple[HarmonizedPoint, ...] = field(default_factory=tuple)

    @property
    def first(self) -> Observation:
        return self.points[0].observation

    @property
    def study_id(self) -> str:
        return self.key[0]

    @property
    def outcome_id(self) -> str:
        return self.key[1]


def format_number(value: float) -> str:
    """Print a number without inventing precision the source did not give."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if text in {"-0", ""} else text


def format_dispersion(observation: Observation) -> str:
    kind = observation.dispersion_type
    if kind == "none":
        return NOT_REPORTED
    values = [format_number(item) for item in observation.dispersion]
    if kind in {"95% CI", "range"}:
        return f"{kind} {values[0]} to {values[1]}"
    return f"{kind} {values[0]}"


def format_value(observation: Observation) -> str:
    if observation.value is None:
        low, high = observation.dispersion
        return (
            f"range {format_number(low)} to {format_number(high)} "
            f"{observation.unit} (as printed)"
        )
    if observation.value_type == "approximation" and observation.dispersion_type == "95% CI":
        low, high = observation.dispersion
        return (
            f"printed 95% CI {format_number(low)} to {format_number(high)} "
            f"{observation.unit}; centre ≈ {format_number(observation.value)} "
            f"{observation.unit} is the CI midpoint (approximation)"
        )
    text = f"{format_number(observation.value)} {observation.unit}"
    if observation.dispersion_type in {"SD", "SE", "SEM"}:
        text += f" (± {format_number(observation.dispersion[0])} {observation.dispersion_type})"
    elif observation.dispersion_type == "95% CI":
        low, high = observation.dispersion
        text += f" (95% CI {format_number(low)} to {format_number(high)})"
    return text


def format_n(observation: Observation) -> str:
    if observation.n is None:
        return f"n {NOT_REPORTED}"
    return f"n = {observation.n} {observation.n_counts}"


def _bounds(value: float, observation: Observation) -> tuple[float | None, float | None]:
    kind = observation.dispersion_type
    if kind in {"SD", "SE", "SEM"}:
        spread = observation.dispersion[0]
        return value - spread, value + spread
    if kind == "95% CI":
        return min(observation.dispersion), max(observation.dispersion)
    return None, None


def _harmonize(
    primary: Observation,
    level: Observation | None,
    baseline: Observation | None,
) -> HarmonizedPoint:
    reason = primary.exclude_from_charts
    baseline_text = primary.baseline_timepoint
    if baseline is not None:
        baseline_text += f": {format_value(baseline)}, {format_n(baseline)}"

    if primary.measure_kind == "percent_change":
        original = format_value(primary)
        if level is not None:
            original += f"; level {format_value(level)}"
        if primary.value is None:
            low, high = min(primary.dispersion), max(primary.dispersion)
            return HarmonizedPoint(
                primary, None, low, high, format_dispersion(primary),
                primary.value_type, primary.formula, original, baseline_text,
                reason is None, reason,
            )
        low, high = _bounds(primary.value, primary)
        return HarmonizedPoint(
            primary, primary.value, low, high, format_dispersion(primary),
            primary.value_type, primary.formula, original, baseline_text,
            reason is None, reason,
        )

    if primary.measure_kind == "percent_of_baseline":
        change = primary.value - 100.0
        low, high = _bounds(change, primary)
        return HarmonizedPoint(
            primary, change, low, high, format_dispersion(primary), "calculated",
            "percent change = printed percent of baseline − 100",
            format_value(primary), baseline_text, reason is None, reason,
        )

    if primary.measure_kind == "level":
        if baseline is None:
            return HarmonizedPoint(
                primary, None, None, None, NOT_REPORTED, primary.value_type,
                None, format_value(primary), baseline_text, False,
                "No baseline value is stored for this outcome, so no percent "
                "change can be calculated.",
            )
        change = calculate_change(baseline.value, primary.value, primary.unit)
        return HarmonizedPoint(
            primary, change.percent_change, None, None,
            f"{NOT_REPORTED} for the change (group means only)", "calculated",
            "percent change = (postflight mean − preflight mean) / preflight mean × 100"
            f" = ({format_number(primary.value)} − {format_number(baseline.value)})"
            f" / {format_number(baseline.value)} × 100",
            format_value(primary), baseline_text, reason is None, reason,
        )

    return HarmonizedPoint(
        primary, None, None, None, format_dispersion(primary), primary.value_type,
        primary.formula, format_value(primary), baseline_text, False,
        "This value is a change in fibre-type share, not a percent change in a "
        "quantity, so it is listed but not placed on the percent-change axis.",
    )


def _sort_day(point: HarmonizedPoint) -> tuple[int, float]:
    day = point.observation.recovery_day
    return (1, 0.0) if day is None else (0, day)


def build_series(observations: tuple[Observation, ...] | None = None) -> tuple[Series, ...]:
    """Group observations into series and put each on the percent-change axis.

    A percent change printed by the source is preferred. Otherwise it is
    calculated from that series' own preflight and postflight group means.
    """
    observations = catalog() if observations is None else observations
    grouped: dict[tuple, list[Observation]] = {}
    for observation in observations:
        grouped.setdefault(observation.series_key, []).append(observation)

    result: list[Series] = []
    for key, members in grouped.items():
        baseline = next(
            (
                item
                for item in members
                if item.timepoint_kind == "preflight" and item.measure_kind == "level"
            ),
            None,
        )
        by_timepoint: dict[str, list[Observation]] = {}
        for item in members:
            if item.timepoint_kind == "postflight":
                by_timepoint.setdefault(item.timepoint, []).append(item)
        points = []
        for group in by_timepoint.values():
            level = next((item for item in group if item.measure_kind == "level"), None)
            printed = next(
                (
                    item
                    for item in group
                    if item.measure_kind in {"percent_change", "percent_of_baseline"}
                ),
                None,
            )
            primary = printed or level or group[0]
            points.append(
                _harmonize(primary, level if primary is not level else None, baseline)
            )
        if points:
            result.append(Series(key, tuple(sorted(points, key=_sort_day))))
    return tuple(result)


@cache
def all_series() -> tuple[Series, ...]:
    return build_series()


def study_label(study_id: str) -> str:
    for study in STUDIES:
        if study["id"] == study_id:
            return f'{str(study["authors"]).split(",")[0].split()[-1]} et al. ({study["year"]})'
    raise KeyError(study_id)


def series_label(series: Series, *, with_study: bool = True) -> str:
    first = series.first
    parts = [first.outcome_name]
    if first.cohort_id != "all":
        parts.append(first.cohort.split(":")[0].split("(")[0].strip())
    text = " · ".join(parts)
    return f"{study_label(series.study_id)} · {text}" if with_study else text


def source_reference(observation: Observation) -> str:
    return (
        f"data/references/{observation.source_file}, PDF page {observation.pdf_page}, "
        f"{observation.table_or_figure}"
    )


def recovery_day_text(observation: Observation) -> str:
    """The postflight timepoint exactly as the catalog labels it."""
    return observation.timepoint
