"""The Scenario Explorer's controls: what can be selected, and why not otherwise.

There are five scientific inputs (outcome category, region, countermeasure,
crew subgroup, postflight recovery day), a study filter, and the duration
slider. Each option is offered only when the catalog holds matching evidence;
an option without evidence is still listed, disabled, with the reason.
"""

from dataclasses import dataclass

from evidence_catalog import (
    CATEGORIES,
    REGIONS,
    SUBGROUPS,
    Series,
    all_series,
    format_number,
    study_label,
)
from study_library import STUDIES


ALL_STUDIES = "all"
ANY_COUNTERMEASURE = "any"
FIRST_TIMEPOINT = "first"
DAY_NOT_REPORTED = "unreported"

STUDY_IDS = tuple(str(study["id"]) for study in STUDIES)
_ABSTRACT_ONLY = {
    str(study["id"]) for study in STUDIES if study["source_availability"] == "abstract_only"
}


@dataclass(frozen=True)
class Option:
    value: str
    label: str
    disabled: bool = False
    reason: str | None = None


@dataclass(frozen=True)
class Control:
    id: str
    label: str
    value: str
    options: tuple[Option, ...]
    help: str


@dataclass(frozen=True)
class Selection:
    study: str
    category: str
    region: str
    countermeasure: str
    subgroup: str
    recovery: str


def recovery_key(day: float | None) -> str:
    return DAY_NOT_REPORTED if day is None else format_number(day)


def recovery_label(key: str) -> str:
    if key == FIRST_TIMEPOINT:
        return "First postflight measurement of each study"
    if key == DAY_NOT_REPORTED:
        return "Postflight, day not reported"
    day = float(key)
    if day >= 365:
        return f"R+{key} (about {format_number(round(day / 365, 1))} years after landing)"
    return f"R+{key}"


def _who(study: str) -> str:
    return "any study" if study == ALL_STUDIES else study_label(study)


def _not_measured(study: str) -> str:
    if study in _ABSTRACT_ONLY:
        return f"Not reported in the abstract of {study_label(study)}"
    return f"Not measured by {_who(study)}"


def _pick(requested: object, options: list[Option]) -> str:
    enabled = [option.value for option in options if not option.disabled]
    if requested in enabled:
        return str(requested)
    return enabled[0] if enabled else options[0].value


def matching_series(
    study: str | None = None,
    category: str | None = None,
    region: str | None = None,
    countermeasure: str | None = None,
    subgroup: str | None = None,
) -> list[Series]:
    """Series matching every filter that is given."""
    result = []
    for series in all_series():
        first = series.first
        if study not in (None, ALL_STUDIES) and first.study_id != study:
            continue
        if category is not None and first.outcome_category != category:
            continue
        if region is not None and first.region != region:
            continue
        if countermeasure not in (None, ANY_COUNTERMEASURE) and (
            first.countermeasure_id != countermeasure
        ):
            continue
        if subgroup is not None and first.subgroup != subgroup:
            continue
        result.append(series)
    return result


def _recovery_keys(series_list: list[Series]) -> list[str]:
    days = {
        point.recovery_day for series in series_list for point in series.points
    }
    ordered = sorted(day for day in days if day is not None)
    keys = [recovery_key(day) for day in ordered]
    if None in days:
        keys.append(DAY_NOT_REPORTED)
    return keys


def resolve_controls(requested: dict[str, object]) -> tuple[Selection, tuple[Control, ...]]:
    """Resolve a request into a valid selection plus the controls to draw.

    Controls are resolved in order; each one's options depend on those before it.
    A requested value that has no evidence is replaced by the first that has.
    """
    study_options = [Option(ALL_STUDIES, "Compare all studies that report this")] + [
        Option(study_id, study_label(study_id)) for study_id in STUDY_IDS
    ]
    study = _pick(requested.get("study"), study_options)

    category_options = [
        Option(
            category,
            label,
            disabled=not matching_series(study, category),
            reason=None if matching_series(study, category) else _not_measured(study),
        )
        for category, label in CATEGORIES.items()
    ]
    category = _pick(requested.get("category"), category_options)
    category_label = CATEGORIES[category].lower()

    used_regions = {series.first.region for series in all_series()}
    region_options = []
    for region, label in REGIONS.items():
        if region not in used_regions:
            continue
        available = bool(matching_series(study, category, region))
        region_options.append(
            Option(
                region,
                label,
                disabled=not available,
                reason=None
                if available
                else f"No {category_label} data for this region in {_who(study)}",
            )
        )
    region = _pick(requested.get("region"), region_options)

    regimens: dict[str, str] = {}
    for series in matching_series(study, category):
        regimens.setdefault(series.first.countermeasure_id, series.first.countermeasure)
    countermeasure_options = [
        Option(ANY_COUNTERMEASURE, "All reported regimens (shown separately)")
    ]
    for regimen_id, label in regimens.items():
        available = bool(matching_series(study, category, region, regimen_id))
        owner = study_label(
            next(
                series.study_id
                for series in matching_series(study, category)
                if series.first.countermeasure_id == regimen_id
            )
        )
        countermeasure_options.append(
            Option(
                regimen_id,
                f"{owner}: {label}" if study == ALL_STUDIES else label,
                disabled=not available,
                reason=None
                if available
                else f"{owner} reports no {category_label} data for this region under this regimen",
            )
        )
    countermeasure = _pick(requested.get("countermeasure"), countermeasure_options)

    subgroup_options = []
    for subgroup, label in SUBGROUPS.items():
        available = bool(
            matching_series(study, category, region, countermeasure, subgroup)
        )
        subgroup_options.append(
            Option(
                subgroup,
                label,
                disabled=not available,
                reason=None
                if available
                else f"Not reported separately by {_who(study)} for this selection",
            )
        )
    subgroup = _pick(requested.get("subgroup"), subgroup_options)

    selected = matching_series(study, category, region, countermeasure, subgroup)
    available_keys = set(_recovery_keys(selected))
    recovery_options = [Option(FIRST_TIMEPOINT, recovery_label(FIRST_TIMEPOINT))]
    for key in _recovery_keys(matching_series(study, category)):
        available = key in available_keys
        recovery_options.append(
            Option(
                key,
                recovery_label(key),
                disabled=not available,
                reason=None
                if available
                else f"Not a reported timepoint for this selection in {_who(study)}",
            )
        )
    recovery = _pick(requested.get("recovery"), recovery_options)

    selection = Selection(study, category, region, countermeasure, subgroup, recovery)
    controls = (
        Control(
            "study", "Study filter", study, tuple(study_options),
            "A filter, not a scientific variable. Studies are shown side by side and never averaged.",
        ),
        Control(
            "category", "1. Outcome category", category, tuple(category_options),
            "The harmonized measurement categories used on the Measurements page.",
        ),
        Control(
            "region", "2. Muscle group / region", region, tuple(region_options),
            "Only regions with data in the selected category can be chosen.",
        ),
        Control(
            "countermeasure", "3. Countermeasure / exercise regimen", countermeasure,
            tuple(countermeasure_options),
            "Regimens are the groups each paper reports. Differences between them are not causal effects.",
        ),
        Control(
            "subgroup", "4. Crew subgroup", subgroup, tuple(subgroup_options),
            "Men and women are available only where a paper reports them separately.",
        ),
        Control(
            "recovery", "5. Postflight recovery day", recovery, tuple(recovery_options),
            "Reported test days only; nothing is interpolated between them. R+x is days after landing, separate from mission duration.",
        ),
    )
    return selection, controls


def selected_series(selection: Selection) -> list[Series]:
    return matching_series(
        selection.study,
        selection.category,
        selection.region,
        selection.countermeasure,
        selection.subgroup,
    )


def point_at(series: Series, recovery: str):
    """The series' point at the selected recovery key, or ``None`` if not measured then."""
    if recovery == FIRST_TIMEPOINT:
        return series.points[0]
    for point in series.points:
        if recovery_key(point.recovery_day) == recovery:
            return point
    return None
