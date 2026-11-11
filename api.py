"""Page data for the web interface, built from the scientific modules.

Every function returns plain JSON-ready data. Selection rules, wording, number
formatting and chart construction all live in Python, so the browser only draws
what it is given and performs no scientific calculation.
"""

import json
import sqlite3
from collections.abc import Mapping

from duration_model import LINEAR_FALLBACK, MODEL_LABELS, MULTI_COHORT
from evidence_catalog import (
    CATEGORIES,
    CATEGORY_DESCRIPTIONS,
    RECOVERY_CATEGORY,
    REGIONS,
    SUBGROUPS,
    VALUE_TYPES,
    VERIFICATION_STATUSES,
    HarmonizedPoint,
    Observation,
    Series,
    all_series,
    duration_evidence,
    external_sources,
    format_n,
    format_number,
    series_label,
    source_reference,
    study_label,
)
from model import Scenario, ScenarioRow, analyze_scenario, describe_change
from plotting import (
    create_comparison_plot,
    create_duration_plot,
    create_recovery_plot,
)
from scenario_inputs import (
    ALL_STUDIES,
    FIRST_TIMEPOINT,
    STUDY_IDS,
    matching_series,
    point_at,
    recovery_key,
    recovery_label,
    resolve_controls,
)
from study_library import get_study, list_studies


# Bump whenever an endpoint is added, removed or changes shape. The Explorer page
# carries the same string and warns when the running server reports another one.
API_VERSION = "2026-11-11.two-step-explorer"

EDUCATIONAL_NOTICE = (
    "Educational tool. It organizes published group results and is not a "
    "clinical, operational or mission-planning predictor."
)
ANALOGUE_NOTICE = (
    "No ground-analogue (bed-rest) curve is drawn. The two bed-rest reviews in "
    "the external register are cited as context only."
)

_LIBRARY_SECTIONS = (
    ("Research question", "research_question"),
    ("Population and sample", "population"),
    ("Sample-size notes", "sample_size_note"),
    ("Study design", "study_design"),
    ("Measurement methods", "measurement_methods"),
    ("Outcomes", "outcomes"),
    ("Timepoints", "timepoints"),
    ("Main findings", "findings"),
    ("Limitations", "limitations"),
)


def _row(label: str | None, text: object) -> dict[str, object]:
    return {"label": label, "text": str(text)}


def _option(value: object, label: str) -> dict[str, object]:
    return {"value": value, "label": label}


def _figure(figure) -> dict[str, object] | None:
    return None if figure is None else json.loads(figure.to_json())


def _percent(value: float) -> str:
    return f"{format_number(round(value, 1))}%"


def _change_text(point: HarmonizedPoint) -> str:
    if point.percent_change is None:
        if point.low is not None:
            return f"range {format_number(point.low)}% to {format_number(point.high)}% (as printed)"
        return "No percent change"
    return _percent(point.percent_change)


def _duration_text(observation: Observation) -> str:
    duration = observation.mission_duration
    parts = []
    if duration.get("value") is not None:
        text = f'{format_number(duration["value"])} days'
        if duration.get("dispersion"):
            text += f' ± {format_number(duration["dispersion"][0])} ({duration.get("dispersion_type")})'
        parts.append(text)
    if duration.get("range"):
        low, high = duration["range"]
        parts.append(f"range {format_number(low)}–{format_number(high)} days")
    text = ", ".join(parts)
    if duration.get("note"):
        text += f'. {duration["note"]}'
    return text


def observation_details(point: HarmonizedPoint, series: Series | None = None) -> dict[str, object]:
    """Everything known about one displayed value, for the provenance dialog."""
    observation = point.observation
    value_rows = [
        _row("Percent change from the study's own baseline", _change_text(point)),
        _row("Value type", f"{point.value_type} — {VALUE_TYPES[point.value_type]}"),
    ]
    if point.formula:
        value_rows.append(_row("Formula", point.formula))
    value_rows += [
        _row("Original value as reported", point.original_text),
        _row("Statistic", observation.statistic_type),
        _row("Uncertainty", point.dispersion_text),
        _row("Baseline", point.baseline_text),
    ]
    if point.not_plotted_reason:
        value_rows.append(_row("Why this is not plotted", point.not_plotted_reason))
    return {
        "heading": f"{study_label(observation.study_id)} — {observation.outcome_name}",
        "sections": [
            {"title": "Value", "rows": value_rows},
            {
                "title": "Who and what was measured",
                "rows": [
                    _row("Outcome category", CATEGORIES[observation.outcome_category]),
                    _row("Region", REGIONS[observation.region]),
                    _row("Muscle or joint", observation.muscle_or_joint),
                    _row("Biological level", observation.biological_level),
                    _row("Sample size", format_n(observation)),
                    _row("Cohort", observation.cohort),
                    _row("Sex", observation.sex),
                    _row("Countermeasure / hardware", observation.countermeasure),
                ],
            },
            {
                "title": "Timing",
                "rows": [
                    _row("Measurement timepoint", observation.timepoint),
                    _row("Mission duration", _duration_text(observation)),
                    _row(
                        "Mission duration, source wording",
                        f'"{observation.mission_duration["wording"]}" '
                        f'(PDF page {observation.mission_duration["pdf_page"]})',
                    ),
                ],
            },
            {
                "title": "Source",
                "rows": [
                    _row("File and location", source_reference(observation)),
                    _row("Exact source wording or cell", observation.source_wording),
                    _row(
                        "Verification",
                        VERIFICATION_STATUSES[observation.verification_status],
                    ),
                    _row("Notes and limitations", observation.notes or "None recorded"),
                ],
            },
        ],
    }


# --- Scenario Explorer ---------------------------------------------------------


def _model_card(row: ScenarioRow) -> dict[str, object]:
    model = row.model
    return {
        "title": series_label(row.series),
        "rows": [
            _row("Model type", model.label),
            _row("Value type of every model output", "approximation"),
            _row("What is assumed", model.assumed),
            _row("Why this model", model.why),
            _row("Anchored to", model.anchored_to),
            _row(
                "Supported range",
                f"{format_number(model.supported_low)}–{format_number(model.supported_high)} "
                f"days ({model.range_basis})",
            ),
            _row("What would replace it", model.needed_to_replace),
            _row("Sources", "; ".join(model.sources)),
        ],
    }


def _row_payload(row: ScenarioRow, duration: float) -> dict[str, object]:
    series = row.series
    first = series.first
    payload: dict[str, object] = {
        "title": series_label(series),
        "study": study_label(series.study_id),
        "subtitle": f"{first.countermeasure} · {SUBGROUPS[first.subgroup]} ({first.sex})",
        "metrics": [],
        "warnings": [],
        "notes": [],
        "detail_id": None,
        "value_type": None,
    }
    if row.point is None:
        payload["notes"].append(row.missing_reason)
        return payload

    point = row.point
    observation = point.observation
    payload["detail_id"] = observation.id
    payload["value_type"] = point.value_type
    payload["metrics"] = [
        {
            "label": f"Measured change at {observation.timepoint}",
            "text": _change_text(point),
            "tag": point.value_type,
        },
        {"label": "Uncertainty", "text": point.dispersion_text, "tag": None},
        {"label": "Sample", "text": format_n(observation), "tag": None},
    ]
    if row.model_output is not None:
        status = str(row.model_output["status"])
        payload["metrics"].append(
            {
                "label": f"Model value at {format_number(duration)} days",
                "text": _percent(float(row.model_output["value"])),
                "tag": "extrapolation" if status == "extrapolated" else "approximation",
            }
        )
        if row.model_output["warning"]:
            payload["warnings"].append(row.model_output["warning"])
        if status == "interpolated":
            payload["notes"].append(
                "This mission length falls between two separate cohorts; the "
                "value is interpolated between their group averages."
            )
    elif first.study_id == "leblanc-2000" and first.outcome_category == "muscle_size":
        payload["notes"].append(
            "No separate duration line: this cohort is covered by the "
            "multi-cohort curve shown on the 'Shuttle/Mir crew, American and "
            "Russian' result for the same muscle."
        )
    else:
        payload["notes"].append(
            "No duration model: the source gives no single measured value to "
            "anchor one on."
        )
    payload["source"] = (
        f"{study_label(observation.study_id)}, PDF page {observation.pdf_page}, "
        f"{observation.table_or_figure}"
    )
    if point.formula:
        payload["notes"].append(f"Formula: {point.formula}.")
    if point.not_plotted_reason:
        payload["warnings"].append(point.not_plotted_reason)
    if row.association is not None:
        payload["notes"].append(
            f'{study_label(series.study_id)} reports a rank association between '
            f'mission length and change in this outcome of Somers\' D = '
            f'{format_number(row.association["value"])} '
            f'({row.association["table_or_figure"]}, PDF page '
            f'{row.association["pdf_page"]}). It shows direction only and is not '
            "used as an equation."
        )
    return payload


def _slider_payload(scenario: Scenario) -> dict[str, object]:
    models = [row.model for row in scenario.rows if row.model is not None]
    kinds = {model.kind for model in models}
    if not models:
        label = "No duration model for this selection"
        notices = [
            "None of the selected results has a single measured value to anchor "
            "a duration model on, so the slider has no effect here."
        ]
    else:
        label = MODEL_LABELS[kinds.pop()] if len(kinds) == 1 else "Mixed: see each result"
        notices = list(dict.fromkeys(model.notice for model in models))
    if scenario.supported_low is not None:
        supported = (
            f"Supported range: {format_number(scenario.supported_low)}–"
            f"{format_number(scenario.supported_high)} days "
            f"({models[0].range_basis})."
        )
    elif models:
        supported = (
            "Supported range differs between the selected studies; it is listed "
            "under 'How the duration model works' for each."
        )
    else:
        supported = ""
    extrapolated = [
        series_label(row.series)
        for row in scenario.rows
        if row.model_output and row.model_output["status"] == "extrapolated"
    ]
    warning = None
    if extrapolated:
        warning = (
            f"Extrapolation warning: {format_number(scenario.duration_days)} days is "
            f"outside the range the data cover for {len(extrapolated)} of "
            f"{len(models)} results. Those values are assumptions, not evidence."
        )
    sources = list(dict.fromkeys(source for model in models for source in model.sources))
    statements = [
        item["source_wording"] + f' — {study_label(item["study_id"])}, PDF page {item["pdf_page"]}.'
        for item in duration_evidence()["statements"]
        if item["applies_to_category"] == scenario.selection.category
        and any(row.series.study_id == item["study_id"] for row in scenario.rows)
    ]
    return {
        "min": scenario.slider_min,
        "max": scenario.slider_max,
        "step": 1,
        "value": scenario.duration_days,
        "default": scenario.slider_default,
        "label": "Mission duration (days)",
        "model_label": label,
        "is_approximation": bool(models),
        "notices": notices,
        "supported": supported,
        "warning": warning,
        "sources": sources,
        "statements": statements,
    }


def _context_rows() -> list[dict[str, object]]:
    return [
        _row(
            f'{source["id"]} ({"ground analogue, not spaceflight" if source["evidence_type"] == "analogue" else "spaceflight"})',
            f'{source["short_label"]}: {source["used_for"][0]}',
        )
        for source in external_sources()
    ]


def build_health_view(
    connection: sqlite3.Connection,
    selection: Mapping[str, object],
) -> dict[str, object]:
    """A cheap liveness and version check; the page uses it to spot an outdated server."""
    return {"status": "ok", "api_version": API_VERSION}


def _controls_payload(controls) -> list[dict[str, object]]:
    """Control state shared by the controls-only and the full results endpoints."""
    return [
        {
            "id": control.id,
            "label": control.label,
            "value": control.value,
            "help": control.help,
            "options": [
                {
                    "value": option.value,
                    "label": option.label
                    + (f" — {option.reason}" if option.disabled else ""),
                    "disabled": option.disabled,
                    "reason": option.reason,
                }
                for option in control.options
            ],
        }
        for control in controls
    ]


def build_scenario_controls_view(
    connection: sqlite3.Connection,
    selection: Mapping[str, object],
) -> dict[str, object]:
    """Only the control state for a selection: no results, slider or charts.

    Used while the reader is still choosing a scenario, so that dependent
    options and their reasons stay live without computing any results.
    """
    _, controls = resolve_controls(dict(selection))
    return {"notice": EDUCATIONAL_NOTICE, "controls": _controls_payload(controls)}


def build_scenario_view(
    connection: sqlite3.Connection,
    selection: Mapping[str, object],
) -> dict[str, object]:
    """Resolve the controls, evaluate the scenario and build its three charts."""
    scenario = analyze_scenario(dict(selection))
    chosen = scenario.selection
    details: dict[str, object] = {}

    modelled = [
        (row.series, row.point, row.model, row.model_output)
        for row in scenario.rows
        if row.model is not None
    ]
    duration_chart: dict[str, object]
    if modelled:
        linear = any(model.kind == LINEAR_FALLBACK for _, _, model, _ in modelled)
        multi = any(model.kind == MULTI_COHORT for _, _, model, _ in modelled)
        caption = [
            "Filled markers are measured group values with their reported "
            "uncertainty; horizontal bars show the mission lengths behind them. "
            "Lines and open diamonds are model output (value type: approximation)."
        ]
        if linear:
            caption.append(
                "Linear approximation: each straight line assumes change grows "
                "evenly from zero at launch to the single measured value. Dashed "
                "parts lie outside the mission lengths the study covers."
            )
        if multi:
            caption.append(
                "Multi-cohort approximation: dotted parts join averages from "
                "separate Shuttle and Mir crews; the solid flat part is where "
                "LeBlanc et al. report no significant slope with duration."
            )
        caption.append(ANALOGUE_NOTICE)
        duration_chart = {
            "figure": _figure(create_duration_plot(modelled, scenario.duration_days)),
            "caption": " ".join(caption),
        }
    else:
        duration_chart = {
            "message": "No duration chart: none of the selected results has a "
            "single measured value to anchor a model on."
        }

    series_list = [row.series for row in scenario.rows]
    selected_ids = {row.point.observation.id for row in scenario.rows if row.point}
    recovery_figure = create_recovery_plot(series_list, selected_ids)
    recovery_chart = (
        {
            "figure": _figure(recovery_figure),
            "caption": (
                "Each marker is a reported postflight test; larger markers are "
                "the selected recovery day. Markers are not joined because "
                "nothing was measured between them. Days after landing (R+x) "
                "are separate from mission duration."
            ),
        }
        if recovery_figure is not None
        else {"message": "No recovery chart: the selected results have no dated postflight value to plot."}
    )

    comparison_series = matching_series(
        ALL_STUDIES, chosen.category, chosen.region, None, chosen.subgroup
    )
    entries = []
    for series in comparison_series:
        point = point_at(series, chosen.recovery)
        if point is not None:
            entries.append((series, point))
    comparison_figure = create_comparison_plot(
        entries,
        f"{CATEGORIES[chosen.category]}, {REGIONS[chosen.region].lower()}: all studies side by side",
    )
    comparison_chart = (
        {
            "figure": _figure(comparison_figure),
            "caption": (
                f"Every study and cohort reporting this category and region at "
                f"{recovery_label(chosen.recovery).lower()}, each relative to its "
                "own baseline. Studies differ in population, method, timepoint "
                "and statistic, so the rows are shown together but never "
                "averaged. Bars are the uncertainty each source reports (SD, SE "
                "or 95% CI; see the tooltip)."
            ),
        }
        if comparison_figure is not None
        else {"message": "No comparison chart for this selection."}
    )

    for series in [*series_list, *comparison_series]:
        for point in series.points:
            details[point.observation.id] = observation_details(point, series)

    measured = [row for row in scenario.rows if row.point is not None]
    if not scenario.rows:
        summary = "No published result matches this selection."
    else:
        studies = list(dict.fromkeys(study_label(row.series.study_id) for row in scenario.rows))
        summary = (
            f"{len(scenario.rows)} published group result"
            f'{"s" if len(scenario.rows) != 1 else ""} from {", ".join(studies)}; '
            f"{len(measured)} measured at {recovery_label(chosen.recovery).lower()}. "
            "Results are listed separately and are not combined."
        )
    headline = None
    if len(measured) == 1 and measured[0].point.percent_change is not None:
        headline = (
            f"{series_label(measured[0].series)}: "
            f"{describe_change(measured[0].point.percent_change)} at "
            f"{measured[0].point.observation.timepoint}."
        )

    return {
        "notice": EDUCATIONAL_NOTICE,
        "controls": _controls_payload(scenario.controls),
        "slider": _slider_payload(scenario),
        "summary": summary,
        "headline": headline,
        "rows": [_row_payload(row, scenario.duration_days) for row in scenario.rows],
        "charts": {
            "duration": duration_chart,
            "recovery": recovery_chart,
            "comparison": comparison_chart,
        },
        "models": [_model_card(row) for row in scenario.rows if row.model is not None],
        "context": _context_rows(),
        "details": details,
        "value_types": [_row(name, text) for name, text in VALUE_TYPES.items()],
    }


# --- Study Library -------------------------------------------------------------


def _study_option_label(study: Mapping[str, object]) -> str:
    return f'{study_label(str(study["id"]))} — {study["title"]}'


def build_library_view(
    connection: sqlite3.Connection,
    selection: Mapping[str, object],
) -> dict[str, object]:
    """The eight library studies, and separately the external supporting evidence."""
    studies = {str(study["id"]): study for study in list_studies(connection)}
    ordered = [study_id for study_id in STUDY_IDS if study_id in studies]
    requested = selection.get("study")
    selected_id = requested if requested in studies else (ordered[0] if ordered else None)
    view: dict[str, object] = {
        "label": "Select a study",
        "value": selected_id,
        "options": [_option(item, _study_option_label(studies[item])) for item in ordered],
        "study": None,
        "error": None,
        "library_note": (
            f"The Study Library holds exactly these {len(ordered)} studies. "
            "External supporting evidence is listed separately below and is not "
            "part of the library."
        ),
        "external": [
            {
                "title": f'{source["id"]} — {source["short_label"]}',
                "rows": [
                    _row("Citation", source["citation"]),
                    _row("Link", source["url"]),
                    _row("How it was read", source["access"]),
                    _row("Population", source["population"]),
                    _row("Used for", " ".join(source["used_for"])),
                    *[
                        _row(f'Quoted ({quote["page"] if isinstance(quote["page"], str) else "p. " + str(quote["page"])})', f'"{quote["text"]}"')
                        for quote in source["quotes"]
                    ],
                    _row("Limitations", source["limitations"]),
                ],
            }
            for source in external_sources()
        ],
    }
    study = get_study(connection, str(selected_id)) if selected_id else None
    if study is None:
        view["error"] = "The selected study could not be found in the library."
        return view

    observations = [item for item in all_series() if item.study_id == selected_id]
    categories = sorted({CATEGORIES[item.first.outcome_category] for item in observations})
    view["study"] = {
        "title": str(study["title"]),
        "captions": [
            f'{study["authors"]} ({study["year"]}). {study["journal"]}. '
            f'DOI: {study["doi"]}',
            f'Source file: data/references/{study["source_file"]} · '
            f'Availability: {study["source_availability"]}',
            f'Extraction status: {study["extraction_status"]} · '
            "Quantitative verification status: "
            f'{study["quantitative_verification_status"]}',
            f"Evidence catalog: {len(observations)} outcome series in "
            f'{", ".join(categories) if categories else "no category"}.',
        ],
        "sections": [
            {"heading": heading, "text": str(study[field])}
            for heading, field in _LIBRARY_SECTIONS
        ],
    }
    return view


# --- Measurements --------------------------------------------------------------

_ALL = "all"


def _table_row(series: Series, point: HarmonizedPoint) -> dict[str, object]:
    observation = point.observation
    return {
        "detail_id": observation.id,
        "cells": [
            observation.outcome_name,
            f"{REGIONS[observation.region]} — {observation.muscle_or_joint}",
            observation.cohort,
            observation.timepoint,
            _change_text(point),
            point.value_type + (f": {point.formula}" if point.formula else ""),
            point.dispersion_text,
            point.original_text,
            f"{observation.statistic_type}; {format_n(observation)}",
            f"PDF p. {observation.pdf_page}, {observation.table_or_figure}",
        ],
        "value_type": point.value_type,
    }


_TABLE_COLUMNS = [
    "Outcome",
    "Region",
    "Cohort",
    "Timepoint",
    "% change from own baseline",
    "Value type and formula",
    "Uncertainty",
    "Original reported value",
    "Statistic and n",
    "Source",
]


def _timepoint_matches(series: Series, point: HarmonizedPoint, timepoint: str) -> bool:
    if timepoint == _ALL:
        return True
    if timepoint == FIRST_TIMEPOINT:
        return point is series.points[0]
    return recovery_key(point.recovery_day) == timepoint


def _has_recovery(series: Series) -> bool:
    return len(series.points) > 1


def build_measurements_view(
    connection: sqlite3.Connection,
    selection: Mapping[str, object],
) -> dict[str, object]:
    """Every study through the same seven category slots, plus comparison charts."""
    studies = {str(study["id"]): study for study in list_studies(connection)}
    ordered = [study_id for study_id in STUDY_IDS if study_id in studies]
    slots = [*CATEGORIES.items(), RECOVERY_CATEGORY]

    def choose(name: str, allowed: list[str], default: str) -> str:
        value = selection.get(name)
        return str(value) if value in allowed else default

    study_filter = choose("study", [_ALL, *ordered], ordered[0] if ordered else _ALL)
    category_filter = choose("category", [_ALL, *[key for key, _ in slots]], _ALL)
    used_regions = [region for region in REGIONS if any(s.first.region == region for s in all_series())]
    region_filter = choose("region", [_ALL, *used_regions], _ALL)
    keys = sorted(
        {recovery_key(p.recovery_day) for s in all_series() for p in s.points if p.recovery_day is not None},
        key=float,
    )
    timepoint_filter = choose("timepoint", [_ALL, FIRST_TIMEPOINT, *keys, "unreported"], _ALL)

    def in_slot(series: Series, slot: str) -> bool:
        if region_filter != _ALL and series.first.region != region_filter:
            return False
        if slot == "recovery":
            return _has_recovery(series)
        return series.first.outcome_category == slot

    details: dict[str, object] = {}
    shown_studies = ordered if study_filter == _ALL else [study_filter]
    shown_slots = [slot for slot in slots if category_filter in (_ALL, slot[0])]
    study_blocks = []
    for study_id in shown_studies:
        study = studies[study_id]
        abstract_only = study["source_availability"] == "abstract_only"
        blocks = []
        for slot, label in shown_slots:
            rows = []
            for series in all_series():
                if series.study_id != study_id or not in_slot(series, slot):
                    continue
                for point in series.points:
                    if _timepoint_matches(series, point, timepoint_filter):
                        rows.append(_table_row(series, point))
                        details[point.observation.id] = observation_details(point, series)
            measured_at_all = any(
                series.study_id == study_id
                and (
                    _has_recovery(series) if slot == "recovery"
                    else series.first.outcome_category == slot
                )
                for series in all_series()
            )
            if rows:
                empty = None
            elif measured_at_all:
                empty = "Measured in this study, but nothing matches the current region and timepoint filters."
            elif slot == "recovery":
                empty = "Not measured in this study: each outcome has a single postflight timepoint."
            elif abstract_only:
                empty = "Not reported in the abstract (only the abstract of this study is available)."
            else:
                empty = "Not measured in this study."
            blocks.append(
                {
                    "id": slot,
                    "label": label,
                    "description": CATEGORY_DESCRIPTIONS[slot],
                    "rows": rows,
                    "empty": empty,
                }
            )
        study_blocks.append(
            {
                "id": study_id,
                "title": f'{study_label(study_id)} — {study["title"]}',
                "caption": (
                    f'Source availability: {study["source_availability"]}. '
                    + (
                        "Abstract-level values only: ranges without means, so "
                        "they are listed but cannot anchor a calculation."
                        if abstract_only
                        else "Values were transcribed from the rendered PDF pages."
                    )
                ),
                "categories": blocks,
            }
        )

    charts = []
    for slot, label in shown_slots:
        members = [series for series in all_series() if in_slot(series, slot)]
        if slot == "recovery":
            if timepoint_filter not in (_ALL, FIRST_TIMEPOINT):
                wanted = {
                    p.observation.id for s in members for p in s.points
                    if recovery_key(p.recovery_day) == timepoint_filter
                }
            else:
                wanted = set()
            figure = create_recovery_plot(members, wanted)
            caption = (
                "All studies with more than one postflight timepoint. Markers "
                "are reported tests and are not joined into a trajectory."
            )
        else:
            entries = []
            for series in members:
                for point in series.points:
                    if _timepoint_matches(
                        series, point,
                        FIRST_TIMEPOINT if timepoint_filter == _ALL else timepoint_filter,
                    ):
                        entries.append((series, point))
            figure = create_comparison_plot(entries, f"{label}: studies side by side")
            caption = (
                "One row per study, cohort and outcome at "
                + (
                    "its first postflight measurement"
                    if timepoint_filter in (_ALL, FIRST_TIMEPOINT)
                    else recovery_label(timepoint_filter)
                )
                + ", relative to that study's own baseline. Never averaged across studies."
            )
        for series in members:
            for point in series.points:
                details.setdefault(point.observation.id, observation_details(point, series))
        charts.append(
            {
                "id": slot,
                "label": label,
                "figure": _figure(figure),
                "caption": caption,
                "message": None if figure is not None else "Nothing to plot for the current filters.",
            }
        )

    return {
        "notice": EDUCATIONAL_NOTICE,
        "filters": [
            {
                "id": "study", "label": "Study", "value": study_filter,
                "options": [_option(_ALL, "All eight studies")]
                + [_option(item, study_label(item)) for item in ordered],
            },
            {
                "id": "category", "label": "Category", "value": category_filter,
                "options": [_option(_ALL, "All seven categories")]
                + [_option(key, label) for key, label in slots],
            },
            {
                "id": "region", "label": "Region", "value": region_filter,
                "options": [_option(_ALL, "All regions")]
                + [_option(region, REGIONS[region]) for region in used_regions],
            },
            {
                "id": "timepoint", "label": "Timepoint", "value": timepoint_filter,
                "options": [
                    _option(_ALL, "All postflight timepoints"),
                    _option(FIRST_TIMEPOINT, recovery_label(FIRST_TIMEPOINT)),
                    *[_option(key, recovery_label(key)) for key in keys],
                    _option("unreported", recovery_label("unreported")),
                ],
            },
        ],
        "columns": _TABLE_COLUMNS,
        "studies": study_blocks,
        "charts": charts,
        "details": details,
        "value_types": [_row(name, text) for name, text in VALUE_TYPES.items()],
    }

