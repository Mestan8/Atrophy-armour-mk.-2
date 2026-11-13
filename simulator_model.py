"""Science behind the 3D Simulator page (human soleus, fibre-level atrophy).

All values come from ``data/simulator/soleus_parameters.json``. That file is kept
apart from the evidence catalog on purpose: it allows the extra value type
``illustrative`` (render counts and placements that cannot be data-driven at real
scale), and it holds anatomy and ultrastructure sources that are not Study Library
studies. ``evidence_catalog`` and the other pages are not affected by it.

The browser turns what ``evaluate`` returns into geometry. It may derive visual
quantities (a radius from a diameter, for example) but holds no scientific
constants of its own.

Time course: no one measured the crew during flight. Day 0 returns the preflight
values and the end of the mission returns the reported postflight values exactly.
Every day in between is an ``approximation`` built from a 0-1 shape (see
``time_course`` in the parameter file and ``duration_model.normalized_shape``).
"""

from dataclasses import dataclass
from functools import cache
import json
import math
from pathlib import Path
from statistics import mean, stdev

from duration_model import normalized_shape
from evidence_catalog import format_number
from study_library import STUDIES


PARAMETER_FILE = (
    Path(__file__).resolve().parent / "data" / "simulator" / "soleus_parameters.json"
)

SIM_VALUE_TYPES = {
    "reported": "Reported: copied from the source as printed.",
    "calculated": "Calculated: arithmetic on reported values (formula shown).",
    "digitized": "Digitized: read off a published figure.",
    "approximation": "Approximation: an assumption, interpolation or correction the source does not prove.",
    "illustrative": "Illustrative: a drawn count, shape or position chosen for display; proportions and sizes come from data, this element does not.",
}
LEVELS = {
    "L0": "Leg",
    "L1": "Muscle",
    "L2": "Fascicle",
    "L3": "Fibre",
    "L4": "Sarcomere",
}
COHORTS = ("all", "high_treadmill", "low_treadmill")
SHAPES = ("spaceflight_cohorts", "linear")
PHASES = ("mission", "recovery")
_STUDY_IDS = {str(study["id"]) for study in STUDIES}
_SHAPE_OUTCOME = "soleus_volume"   # the LeBlanc multi-cohort series whose shape is borrowed

EDUCATIONAL_NOTICE = (
    "This page visualizes published group averages for nine ISS crew members. It is "
    "not a prediction for any individual or any mission."
)
TIMEPOINT_NOTICE = (
    "None of these values were measured in flight. Fibre and electron-microscopy "
    "values come from biopsies on landing day (R+0, 6–8 h after landing); muscle "
    "volumes come from MRI 4 days after landing (R+4)."
)


class SimulatorSchemaError(ValueError):
    """A simulator parameter lacks provenance or a valid value type."""


# --------------------------------------------------------------------------- loading


def _require(record: dict, name: str, where: str) -> object:
    value = record.get(name)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise SimulatorSchemaError(f"{where}: missing '{name}'.")
    return value


def _check_value_record(record: dict, sources: dict, where: str) -> None:
    value_type = _require(record, "value_type", where)
    if value_type not in SIM_VALUE_TYPES:
        raise SimulatorSchemaError(f"{where}: unknown value_type '{value_type}'.")
    if value_type == "illustrative":
        _require(record, "reason", where)
        return
    source = _require(record, "source", where)
    if source not in sources:
        raise SimulatorSchemaError(f"{where}: unknown source '{source}'.")
    _require(record, "location", where)
    _require(record, "quote", where)
    if value_type in {"calculated", "approximation"}:
        _require(record, "formula", where)
    if value_type == "approximation":
        _require(record, "assumed", where)


def validate(document: dict) -> None:
    """Refuse a parameter file in which any value lacks provenance or a value type."""
    sources = _require(document, "sources", "file")
    for source_id, source in sources.items():
        kind = _require(source, "kind", f"source {source_id}")
        if kind == "study":
            if source.get("study_id") not in _STUDY_IDS:
                raise SimulatorSchemaError(f"source {source_id}: not a Study Library study.")
        elif kind == "external":
            for name in ("citation", "url", "access", "population"):
                _require(source, name, f"source {source_id}")
        elif kind != "external_register":
            raise SimulatorSchemaError(f"source {source_id}: unknown kind '{kind}'.")
    _check_value_record(
        {**document["mission"], "value_type": document["mission"]["value_type"]},
        sources, "mission",
    )
    for parameter in document["time_varying"]:
        where = f"parameter {parameter.get('id')}"
        for name in ("id", "name", "levels", "unit", "pre_timepoint", "end_timepoint"):
            _require(parameter, name, where)
        if "all" not in parameter["values"] and "individuals" not in parameter:
            raise SimulatorSchemaError(f"{where}: no all-crew values.")
        if not parameter.get("interpolate", True):
            _require(parameter, "no_interpolation_reason", where)
        for cohort, values in parameter["values"].items():
            if cohort not in COHORTS:
                raise SimulatorSchemaError(f"{where}: unknown cohort '{cohort}'.")
            for key in ("pre", "end"):
                record = _require(values, key, f"{where} {cohort}")
                _check_value_record(record, sources, f"{where} {cohort} {key}")
                _require(record, "n_counts", f"{where} {cohort} {key}")
                _require(record, "dispersion", f"{where} {cohort} {key}")
        if "individuals" in parameter:
            _require(parameter["individuals"], "source", where)
            _require(parameter["individuals"], "location", where)
    distribution = document["fibre_type_distribution"]
    _require(distribution, "source", "fibre_type_distribution")
    _require(distribution, "location", "fibre_type_distribution")
    for category in distribution["categories"]:
        for key in ("pre", "end", "quote_pre", "quote_end", "render_class"):
            _require(category, key, f"fibre type {category.get('id')}")
    for record in document["static"]:
        _check_value_record(record, sources, f"static {record.get('id')}")
        _require(record, "n_counts", f"static {record.get('id')}")
    for record in document["illustrative"]:
        if record.get("value_type") != "illustrative":
            raise SimulatorSchemaError(f"illustrative {record.get('id')}: must be labelled illustrative.")
        _require(record, "reason", f"illustrative {record.get('id')}")
    for structure in document["structures"]:
        function = structure.get("function")
        if function is not None:
            _require(function, "text", f"structure {structure['id']}")
            if function.get("source") not in sources:
                raise SimulatorSchemaError(f"structure {structure['id']}: unknown source.")
    for finding in document["qualitative_findings"]:
        _check_value_record(finding, sources, f"finding {finding.get('id')}")
    for shape_id, shape in document["time_course"]["shapes"].items():
        if shape_id not in SHAPES:
            raise SimulatorSchemaError(f"shape {shape_id}: unknown.")
        if shape.get("value_type") != "approximation":
            raise SimulatorSchemaError(f"shape {shape_id}: in-between days must be approximations.")
        for name in ("label", "method", "sources", "assumed", "why", "needed_to_replace", "notice"):
            _require(shape, name, f"shape {shape_id}")
        for source in shape["sources"]:
            if source not in sources:
                raise SimulatorSchemaError(f"shape {shape_id}: unknown source '{source}'.")
    for point in document["time_course"]["check_points"]:
        _check_value_record({**point, "value_type": "reported"}, sources, f"check point {point['id']}")


@cache
def parameters() -> dict:
    """The validated parameter file (cached)."""
    with PARAMETER_FILE.open(encoding="utf-8") as handle:
        document = json.load(handle)
    validate(document)
    return document


def source_label(source_id: str) -> str:
    return parameters()["sources"][source_id]["short_label"]


def source_details(source_id: str) -> dict[str, object]:
    source = parameters()["sources"][source_id]
    details = {"id": source_id, "label": source["short_label"], "kind": source["kind"]}
    for name in ("citation", "doi", "url", "access", "population", "evidence_type", "study_id", "register_id"):
        if source.get(name):
            details[name] = source[name]
    return details


# ------------------------------------------------------------------ cohort values


def _standard_error(values: list[float]) -> float:
    return stdev(values) / math.sqrt(len(values)) if len(values) > 1 else 0.0


def _subgroup_record(parameter: dict, cohort: str, key: str) -> dict | None:
    """A subgroup mean calculated from the individual values printed in a table."""
    individuals = parameter.get("individuals")
    if not individuals or cohort not in individuals.get("subgroups", ()):
        return None
    members = parameters()["cohorts"][cohort]["members"]
    table = individuals.get(key)
    if table is None:
        return None
    values = [float(table[member]) for member in members if member in table]
    letters = [member for member in members if member in table]
    return {
        "value": round(mean(values), 1),
        "dispersion": [round(_standard_error(values), 1)],
        "n": len(values),
        "n_counts": "crew members",
        "value_type": "calculated",
        "source": individuals["source"],
        "location": individuals["location"],
        "quote": ", ".join(f"{letter} {format_number(table[letter])}" for letter in letters),
        "formula": (
            f"Mean of the printed values for crew members {', '.join(letters)}; "
            "dispersion is the SE of those values (SD ÷ √n)."
        ),
    }


def cohort_record(parameter: dict, cohort: str, key: str) -> dict | None:
    """The pre/end/recovery record for a cohort, or ``None`` if not reported."""
    values = parameter["values"].get(cohort)
    if values is not None and values.get(key) is not None:
        return values[key]
    return _subgroup_record(parameter, cohort, key)


def _distribution_records(cohort: str, key: str) -> list[dict]:
    """Fibre-type shares for a cohort: Table 8 means, or subgroup means calculated from its rows."""
    distribution = parameters()["fibre_type_distribution"]
    order = distribution["individuals"]["order"]
    records = []
    for category in distribution["categories"]:
        if cohort == "all":
            value, spread = category[key]
            records.append({
                "id": category["id"], "label": category["label"],
                "render_class": category["render_class"],
                "value": float(value), "dispersion": [float(spread)],
                "n": distribution["n"], "n_counts": distribution["n_counts"],
                "value_type": "reported", "source": distribution["source"],
                "location": distribution["location"],
                "quote": category["quote_pre" if key == "pre" else "quote_end"],
            })
            continue
        members = parameters()["cohorts"][cohort]["members"]
        table = distribution["individuals"][key]
        index = order.index(category["id"])
        letters = [member for member in members if member in table]
        values = [float(table[letter][index]) for letter in letters]
        records.append({
            "id": category["id"], "label": category["label"],
            "render_class": category["render_class"],
            "value": round(mean(values), 1),
            "dispersion": [round(_standard_error(values), 1)],
            "n": len(values), "n_counts": "crew members (subject B has no fibre-type data)",
            "value_type": "calculated", "source": distribution["source"],
            "location": distribution["location"] + ", individual rows",
            "quote": ", ".join(f"{letter} {format_number(table[letter][index])}" for letter in letters),
            "formula": f"Mean of the printed rows for crew members {', '.join(letters)}; dispersion is SE (SD ÷ √n).",
        })
    return records


# -------------------------------------------------------------------- time course


@dataclass(frozen=True)
class DayState:
    requested: float
    day: float
    clamped: bool
    phase: str
    shape: str
    fraction: float
    status: str   # "preflight" | "end_of_mission" | "interpolated" | "recovery"


def shape_fraction(shape: str, day: float) -> float:
    """Share of the launch-to-end change reached on ``day`` (0 at launch, 1 at the end)."""
    end = float(parameters()["time_course"]["end_day"])
    if day <= 0:
        return 0.0
    if day >= end:
        return 1.0
    if shape == "linear":
        return day / end
    curve = normalized_shape(_SHAPE_OUTCOME, end)
    if curve is None:   # pragma: no cover - the catalog always holds the LeBlanc soleus series
        raise SimulatorSchemaError("The LeBlanc soleus multi-cohort curve is missing.")
    return max(0.0, min(1.0, curve.fraction_at(day)))


def shape_nodes(shape: str) -> list[dict[str, float]]:
    """Corner points of the 0-1 shape, for drawing it next to the slider."""
    end = float(parameters()["time_course"]["end_day"])
    if shape == "linear":
        return [{"day": 0.0, "fraction": 0.0}, {"day": end, "fraction": 1.0}]
    curve = normalized_shape(_SHAPE_OUTCOME, end)
    return [{"day": day, "fraction": abs(round(fraction, 4))} for day, fraction in curve.nodes()]


def resolve_day(day: object, shape: object, phase: object) -> DayState:
    end = float(parameters()["time_course"]["end_day"])
    shape = shape if shape in SHAPES else parameters()["time_course"]["default_shape"]
    phase = phase if phase in PHASES else "mission"
    try:
        requested = float(day)
        if not math.isfinite(requested):
            raise ValueError
    except (TypeError, ValueError):
        requested = 0.0
    clamped_day = min(max(requested, 0.0), end)
    clamped = clamped_day != requested
    if phase == "recovery":
        return DayState(requested, end, clamped, phase, shape, 1.0, "recovery")
    fraction = shape_fraction(shape, clamped_day)
    if clamped_day == 0:
        status = "preflight"
    elif clamped_day == end:
        status = "end_of_mission"
    else:
        status = "interpolated"
    return DayState(requested, clamped_day, clamped, phase, shape, fraction, status)


def _percent(value: float | None, reference: float | None) -> float | None:
    if value is None or reference in (None, 0):
        return None
    return (value - reference) / reference * 100.0


def _source_block(record: dict) -> dict[str, object]:
    block = {
        "source": source_label(record["source"]),
        "source_id": record["source"],
        "location": record.get("location"),
        "quote": record.get("quote"),
    }
    if record.get("formula"):
        block["formula"] = record["formula"]
    return block


def _blend(pre: dict, end: dict, state: DayState, interpolate: bool, timepoints: tuple[str, str],
           reason: str | None) -> dict[str, object]:
    """Value, value type and timepoint for one day between a pre and an end record."""
    pre_value, end_value = float(pre["value"]), float(end["value"])
    if state.status == "preflight":
        return {"value": pre_value, "value_type": pre["value_type"], "timepoint": timepoints[0],
                "dispersion": pre["dispersion"], "n": pre["n"], "n_counts": pre["n_counts"],
                "provenance": [_source_block(pre)], "status": "preflight"}
    if state.status in ("end_of_mission", "recovery"):
        return {"value": end_value, "value_type": end["value_type"], "timepoint": timepoints[1],
                "dispersion": end["dispersion"], "n": end["n"], "n_counts": end["n_counts"],
                "provenance": [_source_block(end)], "status": "end_of_mission"}
    if not interpolate:
        return {"value": pre_value, "value_type": "approximation",
                "timepoint": f"{timepoints[0]} value shown; not modelled between the endpoints",
                "dispersion": pre["dispersion"], "n": pre["n"], "n_counts": pre["n_counts"],
                "provenance": [_source_block(pre)], "status": "held_at_preflight",
                "assumption": reason}
    value = pre_value + (end_value - pre_value) * state.fraction
    shape = parameters()["time_course"]["shapes"][state.shape]
    return {"value": value, "value_type": "approximation",
            "timepoint": f"Mission day {format_number(state.day)} (no measurement on this day)",
            "dispersion": [], "n": None, "n_counts": "not applicable (interpolated value)",
            "provenance": [_source_block(pre), _source_block(end)], "status": "interpolated",
            "assumption": shape["assumed"],
            "formula": (
                f"preflight + (end − preflight) × {state.fraction:.3f} "
                f"({shape['label'].lower()} shape at day {format_number(state.day)})"
            )}


def _parameter_entry(parameter: dict, cohort: str, state: DayState) -> dict[str, object]:
    pre = cohort_record(parameter, cohort, "pre")
    end = cohort_record(parameter, cohort, "end")
    base = {
        "id": parameter["id"], "name": parameter["name"], "levels": parameter["levels"],
        "unit": parameter["unit"], "statistic": parameter.get("statistic"),
        "dispersion_type": parameter.get("dispersion_type"),
        "biological_level": parameter.get("biological_level"),
        "note": parameter.get("note"),
        "function": _function(parameter.get("function")),
    }
    if pre is None or end is None:
        return {**base, "available": False, "value": None, "status": "not_reported_for_cohort",
                "message": f"Not reported for the {parameters()['cohorts'][cohort]['label'].lower()}."}
    timepoints = (parameter["pre_timepoint"], parameter["end_timepoint"])
    recovery = None
    if state.phase == "recovery":
        recovery = cohort_record(parameter, cohort, "recovery")
        if recovery is not None:
            end = recovery
            timepoints = (parameter["pre_timepoint"], parameter["recovery_timepoint"])
    current = _blend(pre, end, state, parameter.get("interpolate", True), timepoints,
                     parameter.get("no_interpolation_reason"))
    entry = {
        **base, **current, "available": True,
        "pre": {"value": float(pre["value"]), "dispersion": pre["dispersion"], "n": pre["n"],
                "n_counts": pre["n_counts"], "value_type": pre["value_type"],
                "timepoint": parameter["pre_timepoint"], **_source_block(pre)},
        "end": {"value": float(end["value"]), "dispersion": end["dispersion"], "n": end["n"],
                "n_counts": end["n_counts"], "value_type": end["value_type"],
                "timepoint": timepoints[1], **_source_block(end)},
        "percent_change": _percent(current["value"], float(pre["value"])),
        "percent_change_type": "calculated",
        "percent_change_formula": "(current − preflight) ÷ preflight × 100, from group means",
        "interpolated_in_flight": parameter.get("interpolate", True),
    }
    if state.phase == "recovery" and recovery is None:
        entry["recovery_note"] = (
            "Not measured at R+19; the landing-day (end-of-mission) value is shown."
        )
    reported_change = parameter["values"].get(cohort, {}).get(
        "reported_change_recovery" if state.phase == "recovery" and recovery is not None
        else "reported_change_end"
    )
    if reported_change and state.status in ("end_of_mission", "recovery"):
        entry["reported_change"] = {
            "value": reported_change["value"], "dispersion": reported_change.get("dispersion", []),
            "unit": reported_change.get("unit", "%"), "note": reported_change.get("note"),
            **_source_block(reported_change),
        }
    if not parameter.get("interpolate", True) and state.status == "interpolated":
        entry["no_interpolation_quote"] = parameter.get("no_interpolation_quote")
    return entry


def _function(function: dict | None) -> dict | None:
    if not function:
        return None
    return {"text": function["text"], "source": source_label(function["source"]),
            "location": function["location"]}


def _distribution_entry(cohort: str, state: DayState) -> dict[str, object]:
    distribution = parameters()["fibre_type_distribution"]
    pre_records = _distribution_records(cohort, "pre")
    end_records = _distribution_records(cohort, "end")
    timepoints = (distribution["pre_timepoint"], distribution["end_timepoint"])
    categories = []
    for pre, end in zip(pre_records, end_records):
        current = _blend(pre, end, state, True, timepoints, None)
        categories.append({
            "id": pre["id"], "label": pre["label"], "render_class": pre["render_class"],
            **current,
            "pre": {"value": pre["value"], "dispersion": pre["dispersion"], "value_type": pre["value_type"], **_source_block(pre)},
            "end": {"value": end["value"], "dispersion": end["dispersion"], "value_type": end["value_type"], **_source_block(end)},
        })
    shares = {}
    for category in categories:
        shares[category["render_class"]] = shares.get(category["render_class"], 0.0) + category["value"]
    total = sum(shares.values()) or 1.0
    return {
        "id": distribution["id"], "name": distribution["name"], "unit": distribution["unit"],
        "levels": distribution["levels"], "note": distribution["note"],
        "n": pre_records[0]["n"], "n_counts": pre_records[0]["n_counts"],
        "categories": categories,
        "render_shares": {
            "values": {key: value / total for key, value in shares.items()},
            "value_type": "calculated" if state.status in ("preflight", "end_of_mission") else "approximation",
            "formula": "Shares of the categories in each render class, divided by their sum (Table 8 rows sum to about 100 %).",
            "classes": distribution["render_classes"],
        },
        "timepoint": categories[0]["timepoint"],
        "recovery_note": "Not measured at R+19; the landing-day value is shown." if state.phase == "recovery" else None,
    }


# ------------------------------------------------------------------ derived values


def _derived(entries: dict[str, dict], state: DayState, cohort: str) -> list[dict[str, object]]:
    """Visual scale factors calculated from the entries; each states its formula."""
    derived = []
    for muscle in ("soleus_volume", "gastrocnemius_volume"):
        entry = entries.get(muscle)
        if entry and entry["available"]:
            ratio = entry["value"] / entry["pre"]["value"]
            derived.append({
                "id": muscle.replace("_volume", "_transverse_scale"),
                "name": f"{entry['name']}: cross-section scale factor for the 3D shape",
                "value": math.sqrt(ratio), "unit": "×",
                "value_type": "calculated" if entry["value_type"] != "approximation" else "approximation",
                "formula": "√(volume ÷ preflight volume): the length is kept (the bones it attaches to do not shrink), so the whole volume change is applied to the cross-section, and each linear cross-section size scales by the square root.",
                "levels": ["L0", "L1"],
            })
            derived.append({
                "id": muscle.replace("_volume", "_area_ratio"),
                "name": f"{entry['name']}: cross-sectional area relative to preflight",
                "value": ratio, "unit": "×",
                "value_type": "calculated" if entry["value_type"] != "approximation" else "approximation",
                "formula": "volume ÷ preflight volume (length held constant)",
                "levels": ["L1"],
            })
    fibre = entries.get("type_i_diameter")
    if fibre and fibre["available"]:
        ratio = (fibre["value"] / fibre["pre"]["value"]) ** 2
        base = next(item for item in parameters()["illustrative"] if item["id"] == "l3_myofibril_count_pre")
        derived.append({
            "id": "myofibril_count_rendered", "name": "Myofibrils drawn in the fibre",
            "value": round(base["value"] * ratio), "unit": "count",
            "value_type": "approximation" if state.status != "preflight" else "illustrative",
            "formula": f"{base['value']} drawn preflight × (diameter ÷ preflight diameter)²",
            "assumed": "Myofibril size and packing stay constant, so the number of myofibrils falls in proportion to fibre cross-sectional area. Fitts et al. describe smaller myofibrils only qualitatively.",
            "levels": ["L3"],
        })
    thick = next(item for item in parameters()["time_varying"] if item["id"] == "thick_filament_density")
    density = float(thick["values"]["all"]["pre"]["value"])   # filaments per µm²
    derived.append({
        "id": "thick_lattice_spacing", "name": "Centre-to-centre distance between thick filaments in the drawn lattice",
        "value": math.sqrt(2.0 / (math.sqrt(3.0) * density)) * 1000.0, "unit": "nm",
        "value_type": "calculated",
        "formula": f"√(2 ÷ (√3 × {format_number(density)} μm⁻²)) for a hexagonal lattice, from the preflight thick-filament density (Fitts et al. PDF page 5)",
        "note": "The thick-filament density did not change significantly (P = 0.07), so this spacing is held constant. It is a geometric consequence of the reported density, not a separately measured spacing; Fitts et al. normalised their counts to a 31.3 nm thick-filament spacing.",
        "levels": ["L4"],
    })
    thin = entries.get("thin_filament_density")
    maximum = next(item for item in parameters()["static"] if item["id"] == "z_band_thin_density_max")
    if thin and thin["available"]:
        derived.append({
            "id": "thin_reach_fraction", "name": "Share of thin filaments long enough to reach the near-M region",
            "value": thin["value"] / maximum["value"], "unit": "fraction",
            "pre_value": thin["pre"]["value"] / maximum["value"],
            "value_type": "calculated" if thin["status"] in ("preflight", "end_of_mission") else "approximation",
            "formula": f"thin-filament density near the M line ÷ {format_number(maximum['value'])} μm⁻² (the largest number nucleated at the Z band; Fitts et al. PDF pages 14–15)",
            "assumed": "All thin filaments start at the Z band, so the density near the M line divided by the Z-band density gives the share that are long enough to reach it.",
            "levels": ["L4"],
        })
    return derived


# ------------------------------------------------------------------------ evaluate


def evaluate(day: object = 0, cohort: object = "all", shape: object = None,
             phase: object = "mission") -> dict[str, object]:
    """Every simulator value for one day, with provenance and value type."""
    document = parameters()
    cohort = cohort if cohort in COHORTS else "all"
    state = resolve_day(day, shape, phase)
    entries = {
        parameter["id"]: _parameter_entry(parameter, cohort, state)
        for parameter in document["time_varying"]
    }
    shape_info = document["time_course"]["shapes"][state.shape]
    notices = [EDUCATIONAL_NOTICE, TIMEPOINT_NOTICE]
    if state.status == "interpolated":
        notices.append(shape_info["notice"])
    if state.clamped:
        notices.append(
            f"Clamped: day {format_number(state.requested)} is outside the 0–"
            f"{document['time_course']['end_day']} day range of this cohort (missions averaged "
            f"{document['time_course']['end_day']} days), so day {format_number(state.day)} is shown. "
            "No data exist for longer missions, and nothing is extrapolated."
        )
    if state.phase == "recovery":
        notices.append(
            "Recovery view (R+19): only muscle volumes were measured again at R+19 (MRI). "
            "Fibre, fibre-type and electron-microscopy values were measured only on landing "
            "day; those levels keep their R+0 values and say so."
        )
    if cohort != "all":
        info = document["cohorts"][cohort]
        notices.append(
            f"{info['label']} (n = {info['n_crew']} crew members). {info['note']} "
            "Values for this group are never mixed with all-crew values; levels without "
            "subgroup data say so instead."
        )
    return {
        "notice": EDUCATIONAL_NOTICE,
        "notices": notices,
        "cohort": {"id": cohort, **document["cohorts"][cohort]},
        "cohorts": [{"id": key, "label": value["label"], "n_crew": value["n_crew"]} for key, value in document["cohorts"].items()],
        "day": {
            "requested": state.requested, "value": state.day, "clamped": state.clamped,
            "end": document["time_course"]["end_day"], "range": document["mission"]["range"],
            "status": state.status, "phase": state.phase, "fraction": state.fraction,
            "range_note": (
                f"Slider ends at {document['time_course']['end_day']} days, the cohort's mean mission "
                f"length. Individual missions lasted {document['mission']['range'][0]}–"
                f"{document['mission']['range'][1]} days; no value is available per mission length."
            ),
            "mission_quote": {"source": source_label(document["mission"]["source"]),
                              "location": document["mission"]["location"],
                              "quote": document["mission"]["quote"]},
        },
        "time_course": {
            "shape": state.shape,
            "shapes": [
                {"id": key, "label": value["label"], "value_type": value["value_type"],
                 "method": value["method"], "assumed": value["assumed"], "why": value["why"],
                 "needed_to_replace": value["needed_to_replace"], "notice": value["notice"],
                 "sources": [source_details(source) for source in value["sources"]],
                 "supporting_quotes": [
                     {**quote, "source": source_label(quote["source"])}
                     for quote in value["supporting_quotes"]
                 ],
                 "nodes": shape_nodes(key)}
                for key, value in document["time_course"]["shapes"].items()
            ],
            "check_points": [
                {**point, "source": source_label(point["source"]),
                 "model_percent_change": _check_point_model(entries, point, state.shape)}
                for point in document["time_course"]["check_points"]
            ],
            "context": [
                {**item, "source": source_label(item["source"])}
                for item in document["time_course"]["context"]
            ],
        },
        "parameters": list(entries.values()),
        "fibre_types": _distribution_entry(cohort, state),
        "derived": _derived(entries, state, cohort),
        "static": [
            {**{key: value for key, value in record.items() if key != "source"},
             "source": source_label(record["source"]), "source_id": record["source"]}
            for record in document["static"]
        ],
        "structures": [
            {**structure, "function": _function(structure.get("function"))}
            for structure in document["structures"]
        ],
        "illustrative": document["illustrative"],
        "qualitative_findings": [
            {**finding, "source": source_label(finding["source"])}
            for finding in document["qualitative_findings"]
        ],
        "levels": [{"id": key, "label": value} for key, value in LEVELS.items()],
        "value_types": SIM_VALUE_TYPES,
        "sources": [source_details(key) for key in document["sources"]],
    }


def _check_point_model(entries: dict, point: dict, shape: str) -> float | None:
    """What the chosen shape gives on the check-point day, for comparison with the other crew."""
    entry = entries.get(point["parameter"])
    if not entry or not entry["available"]:
        return None
    pre, end = entry["pre"]["value"], entry["end"]["value"]
    fraction = shape_fraction(shape, float(point["day"]))
    return _percent(pre + (end - pre) * fraction, pre)
