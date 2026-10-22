"""Map selectable chart points to the verified records that they display."""

from collections.abc import Mapping


def observation_identifier(record: Mapping[str, object]) -> str:
    """Build a stable point ID from a study record's identifying fields."""
    fields = (
        "study_id",
        "muscle_or_outcome",
        "measurement_name",
        "timepoint",
    )
    values = [str(record.get(field) or "") for field in fields]
    return "::".join(values)


def build_observation_details(
    study: Mapping[str, object],
    record: Mapping[str, object],
    *,
    region: str,
    outcome: str,
    comparison: str,
    unit: str,
) -> dict[str, object]:
    """Create point-specific display metadata from a study and its record."""
    study_id = str(record.get("study_id") or "")
    if study_id == "english-2015":
        meaning = (
            "A whole-joint isokinetic torque or work outcome measured after "
            "return, expressed relative to the L-60 preflight baseline. A "
            "more negative value indicates a larger reduction from baseline; "
            "a less negative value indicates a smaller reduction. It is not "
            "an in-flight measurement."
        )
        statistic = "Original reported group mean change from L-60."
        sample_definition = (
            "The row's n is the number of flight datasets contributing to "
            "that outcome and timepoint; it is not necessarily a count of "
            "unique astronauts."
        )
        limitation = (
            "This postflight joint-level result is not a direct muscle-fibre "
            "measurement or an individual prediction."
        )
    else:
        if "diameter" in outcome.lower():
            direction_meaning = (
                "A larger or smaller value means a larger or smaller fibre "
                "diameter."
            )
        else:
            direction_meaning = (
                "A larger or smaller value means more or less peak force "
                "produced by an isolated fibre."
            )
        meaning = (
            f"A {outcome.lower()} measurement from isolated {region.lower()} "
            "slow type I muscle fibres. "
            f"{direction_meaning} This is a fibre-level property, not "
            "whole-joint strength or overall muscle function."
        )
        statistic = "Original published mean for the sampled muscle fibres."
        sample_definition = (
            "The row's n counts fibres, not astronaut participants. The study "
            "analyzed nine crew members."
        )
        limitation = (
            "Sampled fibres may not fully represent whole-muscle changes; "
            "fibre counts are subsamples, not independent crew observations."
        )

    sample_size = record.get("sample_size")
    source_page = record.get("source_page")
    source_location = record.get("source_location")
    doi = study.get("doi")
    return {
        "observation_id": observation_identifier(record),
        "outcome": outcome,
        "anatomical_target": region,
        "value": record.get("value"),
        "unit": record.get("unit") or unit,
        "timepoint": record.get("timepoint"),
        "comparison": comparison,
        "value_status": "Original reported measurement",
        "statistic": statistic,
        "scientific_meaning": meaning,
        "authors_year": f'{study.get("authors", "Unavailable")} ({study.get("year", "Unavailable")})',
        "study_title": study.get("title"),
        "doi": doi,
        "source_pdf": study.get("source_file"),
        "source_page": source_page,
        "source_location": source_location,
        "sample_size": sample_size,
        "sample_definition": (
            sample_definition if sample_size is not None else None
        ),
        "uncertainty": record.get("uncertainty_notes"),
        "source_wording": record.get("source_wording"),
        "limitations": (
            f"{limitation} {study.get('limitations', '')}".strip()
        ),
    }


def selected_observation_id(selection: object) -> str | None:
    """Extract the first selected point's stable customdata identifier."""
    if isinstance(selection, Mapping):
        points = selection.get("points", ())
    else:
        points = getattr(selection, "points", ())
    if not isinstance(points, (list, tuple)) or not points:
        return None

    point = points[0]
    if not isinstance(point, Mapping):
        return None
    customdata = point.get("customdata")
    if isinstance(customdata, str):
        return customdata or None
    if isinstance(customdata, Mapping):
        identifier = customdata.get("observation_id")
        return identifier if isinstance(identifier, str) and identifier else None
    if isinstance(customdata, (list, tuple)) and customdata:
        identifier = customdata[0]
        return identifier if isinstance(identifier, str) and identifier else None
    return None


def resolve_selected_observation(
    selection: object,
    details_by_id: Mapping[str, dict[str, object]],
) -> dict[str, object] | None:
    """Resolve a chart selection only against the active chart's records."""
    identifier = selected_observation_id(selection)
    if identifier is None:
        return None
    return details_by_id.get(identifier)
