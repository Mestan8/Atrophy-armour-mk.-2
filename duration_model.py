"""Mission-duration models: what the slider is allowed to do, and why.

Two models exist, and both are approximations.

``multi_cohort``
    Muscle volume in LeBlanc et al. (2000) regions. Real cohort means exist at
    17 days and at 115-197 days in the same paper, plus an 8-day Shuttle value
    quoted by the NASA evidence report (external source E1). The model joins
    those cohort means with straight segments and holds the long-duration value
    flat across 115-197 days, because LeBlanc reports no significant slope with
    flight duration in that span.

``linear_fallback``
    Everything else. Each study gives one group mean at one mean duration, so
    the only thing that can be drawn is a straight line from (0 days, 0 change)
    through that point.

No model output is ever labelled as reported, and nothing is evaluated outside
the supported range without being flagged as an extrapolation.
"""

from dataclasses import dataclass
import math

from evidence_catalog import (
    Observation,
    Series,
    all_series,
    external_source,
    format_number,
    study_label,
)


MULTI_COHORT = "multi_cohort"
LINEAR_FALLBACK = "linear_fallback"

MODEL_LABELS = {
    MULTI_COHORT: "Fitted to several cohorts (approximation)",
    LINEAR_FALLBACK: "Linear approximation (fallback)",
}

LINEAR_NOTICE = (
    "Straight-line approximation. This study measured this outcome once, after "
    "missions of one typical length. The line assumes change grows evenly from "
    "zero at launch to the measured value. No data in this study show that it does."
)
MULTI_COHORT_NOTICE = (
    "Approximation from separate crews. The line joins group averages from "
    "different missions (Space Shuttle and Mir, not ISS). Those crews also "
    "differed in exercise, so the line mixes mission length with other differences."
)

_LEBLANC = "leblanc-2000"
_SHORT_COHORT = "spacelab"
_LONG_COHORT = "mir_all"
# LeBlanc outcome -> the 8-day data point in external source E1 that covers it.
_E1_POINTS = {
    "anterior_leg_volume": "E1-sts47-anterior-calf",
    "gastrocnemius_volume": "E1-sts47-gastrocnemius-soleus",
    "soleus_volume": "E1-sts47-gastrocnemius-soleus",
    "hamstrings_volume": "E1-sts47-hamstrings",
    "intrinsic_back_volume": "E1-sts47-intrinsic-back",
}


@dataclass(frozen=True)
class Anchor:
    """A real observation (or the defined zero point) that a model passes through."""

    day: float
    value: float
    label: str
    source: str
    low: float | None = None
    high: float | None = None
    day_low: float | None = None
    day_high: float | None = None
    is_defined_zero: bool = False


@dataclass(frozen=True)
class Segment:
    """Part of a model curve. ``kind`` controls how it is drawn."""

    kind: str  # "supported" | "interpolated" | "extrapolated"
    days: tuple[float, ...]
    values: tuple[float, ...]


@dataclass(frozen=True)
class DurationModel:
    kind: str
    series_key: tuple
    anchors: tuple[Anchor, ...]
    supported_low: float
    supported_high: float
    range_basis: str
    default_day: float
    slider_max: float
    assumed: str
    why: str
    anchored_to: str
    needed_to_replace: str
    sources: tuple[str, ...]

    @property
    def label(self) -> str:
        return MODEL_LABELS[self.kind]

    @property
    def notice(self) -> str:
        return LINEAR_NOTICE if self.kind == LINEAR_FALLBACK else MULTI_COHORT_NOTICE

    def value_at(self, day: float) -> float:
        """Model value at ``day``; beyond the last anchor the multi-cohort model is held flat."""
        if self.kind == LINEAR_FALLBACK:
            reference = self.anchors[-1]
            return reference.value * day / reference.day
        return _piecewise(self._nodes(), day)

    def _nodes(self) -> list[tuple[float, float]]:
        nodes = [(anchor.day, anchor.value) for anchor in self.anchors]
        last = self.anchors[-1]
        # The long-duration cohort mean applies across its whole reported span.
        nodes[-1] = (last.day_low, last.value)
        nodes.append((last.day_high, last.value))
        return nodes

    def status_at(self, day: float) -> str:
        if self.kind == LINEAR_FALLBACK:
            if self.supported_low <= day <= self.supported_high:
                return "supported"
            return "extrapolated"
        if day > self.supported_high:
            return "extrapolated"
        if day >= self.anchors[-1].day_low:
            return "supported"
        return "interpolated"

    def segments(self) -> tuple[Segment, ...]:
        """The curve from day 0 to the slider maximum, split by evidence status."""
        if self.kind == LINEAR_FALLBACK:
            cuts = [0.0, self.supported_low, self.supported_high, self.slider_max]
            kinds = ["extrapolated", "supported", "extrapolated"]
        else:
            nodes = [day for day, _ in self._nodes()]
            cuts = nodes + [self.slider_max]
            kinds = ["interpolated"] * (len(nodes) - 2) + ["supported", "extrapolated"]
        segments = []
        for kind, start, end in zip(kinds, cuts, cuts[1:]):
            if end <= start:
                continue
            days = (start, end)
            segments.append(
                Segment(kind, days, tuple(self.value_at(day) for day in days))
            )
        return tuple(segments)

    def evaluate(self, day: float) -> dict[str, object]:
        """Model output at ``day`` with its flags; always an approximation."""
        status = self.status_at(day)
        warning = None
        if status == "extrapolated":
            if self.kind == LINEAR_FALLBACK:
                warning = (
                    f"Extrapolation: {format_number(day)} days is outside the "
                    f"{format_number(self.supported_low)}–"
                    f"{format_number(self.supported_high)} day range this study "
                    f"covers ({self.range_basis}). The line is extended only to "
                    "show what the straight-line assumption implies; no data "
                    "support this value."
                )
            else:
                warning = (
                    f"Extrapolation: {format_number(day)} days is longer than the "
                    f"longest flight in the data ({format_number(self.supported_high)} "
                    "days). The value is held at the long-duration group average; "
                    "no data show what happens on longer missions."
                )
        return {
            "value": self.value_at(day),
            "value_type": "approximation",
            "status": status,
            "warning": warning,
            "model": self.kind,
        }


def _piecewise(nodes: list[tuple[float, float]], day: float) -> float:
    if day <= nodes[0][0]:
        return nodes[0][1]
    for (start, start_value), (end, end_value) in zip(nodes, nodes[1:]):
        if day <= end:
            if end == start:
                return end_value
            share = (day - start) / (end - start)
            return start_value + share * (end_value - start_value)
    return nodes[-1][1]


def duration_support(observation: Observation) -> tuple[float, float, float, str]:
    """Reference day, supported range and how that range was obtained."""
    duration = observation.mission_duration
    value = duration.get("value")
    span = duration.get("range")
    spread = duration.get("dispersion") or []
    if span:
        low, high = float(span[0]), float(span[1])
        reference = float(value) if value is not None else (low + high) / 2
        if duration.get("range_is_approximate"):
            basis = "an approximate range converted from the weeks or months the paper reports"
        else:
            basis = "the reported minimum and maximum flight duration"
        if value is None:
            basis += "; no mean is reported, so the middle of the range is used as the reference"
        return reference, low, high, basis
    reference = float(value)
    if spread:
        low, high = reference - float(spread[0]), reference + float(spread[0])
        kind = duration.get("dispersion_type", "spread")
        basis = (
            f"the reported mean ± one {kind}"
            if kind in {"SD", "SE", "SEM"}
            else "the reported mean ± the printed spread (its type is not stated)"
        )
        return reference, low, high, basis + "; this is not an observed minimum and maximum"
    return reference, reference, reference, "a single reported mission length"


def _round_up(value: float, step: int = 10) -> float:
    return float(math.ceil(value / step) * step)


def _anchor_from_point(point, day: float, label: str, **extra) -> Anchor:
    observation = point.observation
    return Anchor(
        day=day,
        value=point.percent_change,
        label=label,
        source=(
            f"{study_label(observation.study_id)}, PDF page {observation.pdf_page}, "
            f"{observation.table_or_figure}"
        ),
        low=point.low,
        high=point.high,
        **extra,
    )


def _leblanc_series(outcome_id: str, cohort_id: str) -> Series | None:
    for series in all_series():
        if (
            series.study_id == _LEBLANC
            and series.outcome_id == outcome_id
            and series.first.cohort_id == cohort_id
        ):
            return series
    return None


def _multi_cohort_model(series: Series) -> DurationModel | None:
    short = _leblanc_series(series.outcome_id, _SHORT_COHORT)
    long = _leblanc_series(series.outcome_id, _LONG_COHORT)
    if short is None or long is None:
        return None
    anchors = [
        Anchor(0.0, 0.0, "Launch (defined as no change)", "Definition, not a measurement",
               is_defined_zero=True)
    ]
    sources = [f"{study_label(_LEBLANC)} (Study Library)"]
    point_id = _E1_POINTS.get(series.outcome_id)
    if point_id is not None:
        source = external_source("E1")
        data = next(item for item in source["data_points"] if item["id"] == point_id)
        anchors.append(
            Anchor(
                day=float(data["mission_duration_days"]),
                value=float(data["value"]),
                label=(
                    f'8-day Space Shuttle flight, {data["muscle_or_joint"]}, '
                    f'n = {data["n"]}, measured at {data["timepoint"]} '
                    "(spread not reported)"
                ),
                source=f'External source E1, p. {data["page"]}: {source["short_label"]}',
            )
        )
        sources.append(f'External source E1: {source["short_label"]}')
    short_point = short.points[0]
    anchors.append(
        _anchor_from_point(
            short_point, 17.0,
            f"17-day Spacelab flight, n = {short_point.observation.n}, landing day (± SD)",
        )
    )
    long_point = long.points[0]
    low, high = (float(item) for item in long_point.observation.mission_duration["range"])
    reference = float(long_point.observation.mission_duration["value"])
    anchors.append(
        _anchor_from_point(
            long_point, reference,
            f"Shuttle/Mir flights of {format_number(low)}–{format_number(high)} days, "
            f"n = {long_point.observation.n}, first scan R+0 to R+4 (± SD)",
            day_low=low, day_high=high,
        )
    )
    shared = (
        " The 8-day value is for gastrocnemius and soleus measured together, so "
        "the same number is used for either muscle."
        if point_id == "E1-sts47-gastrocnemius-soleus"
        else ""
    )
    return DurationModel(
        kind=MULTI_COHORT,
        series_key=series.key,
        anchors=tuple(anchors),
        supported_low=float(anchors[1].day),
        supported_high=high,
        range_basis="the shortest and longest flights with a measured group mean",
        default_day=reference,
        slider_max=_round_up(high * 1.25),
        assumed=(
            "Group means from separate crews can be joined by straight segments, "
            f"and the long-duration mean applies unchanged from {format_number(low)} "
            f"to {format_number(high)} days." + shared
        ),
        why=(
            "This is the only outcome with measured group means at more than one "
            "mission length. LeBlanc et al. report that percent loss had no "
            "significant slope against flight duration across "
            f"{format_number(low)}–{format_number(high)} days, which supports a "
            "flat segment there. There are too few points to fit or test a curve, "
            "so no goodness-of-fit is given."
        ),
        anchored_to="; ".join(
            f"{format_number(anchor.day)} d: {format_number(anchor.value)}% ({anchor.source})"
            for anchor in anchors[1:]
        ),
        needed_to_replace=(
            "Repeated measurements of the same crew during flight, or group means "
            "from many mission lengths with the same exercise programme."
        ),
        sources=tuple(sources),
    )


def _linear_model(series: Series, point) -> DurationModel:
    observation = point.observation
    reference, low, high, basis = duration_support(observation)
    anchors = (
        Anchor(0.0, 0.0, "Launch (defined as no change)", "Definition, not a measurement",
               is_defined_zero=True),
        _anchor_from_point(
            point, reference,
            f"{study_label(series.study_id)}: {observation.timepoint}",
            day_low=low, day_high=high,
        ),
    )
    return DurationModel(
        kind=LINEAR_FALLBACK,
        series_key=series.key,
        anchors=anchors,
        supported_low=low,
        supported_high=high,
        range_basis=basis,
        default_day=reference,
        slider_max=_round_up(high * 1.25),
        assumed=(
            "Change is zero at launch and grows in direct proportion to days in "
            f"flight, reaching the measured value at {format_number(reference)} days."
        ),
        why=(
            "The study reports this outcome at a single postflight timepoint for "
            "one group of missions, so there is one data point. No published "
            "time-course function for this outcome in spaceflight was found, and "
            "one point cannot support a fitted curve."
        ),
        anchored_to=(
            f"{format_number(reference)} d: {format_number(point.percent_change)}% "
            f"({anchors[1].source}); mission duration from PDF page "
            f'{observation.mission_duration["pdf_page"]}: '
            f'"{observation.mission_duration["wording"]}"'
        ),
        needed_to_replace=(
            "Measurements of this outcome in flight or after missions of several "
            "different lengths under the same exercise programme."
        ),
        sources=(f"{study_label(series.study_id)} (Study Library)",),
    )


def model_for(series: Series, point=None) -> DurationModel | None:
    """Choose the duration model for a series, anchored on ``point``.

    ``point`` is the selected postflight timepoint; it defaults to the first.
    Returns ``None`` when the point has no single percent change to anchor on
    (for example an abstract that prints only a range), and for LeBlanc cohorts
    that are covered by that muscle's multi-cohort curve.
    """
    first = series.first
    if first.study_id == _LEBLANC and first.outcome_category == "muscle_size":
        model = _multi_cohort_model(series)
        if model is not None:
            # One curve per muscle: it belongs to the 16-crew Shuttle/Mir series
            # whose mean it ends on. The other LeBlanc cohorts are its anchors
            # or a landing-day subset, and get no second copy of the curve.
            return model if first.cohort_id == _LONG_COHORT else None
    point = series.points[0] if point is None else point
    if point.percent_change is None or not point.plottable:
        return None
    return _linear_model(series, point)
