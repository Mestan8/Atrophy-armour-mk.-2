"""Charts for the Scenario Explorer and Measurements pages.

These functions only draw values that already exist in the catalog or in a
duration model; they do no scientific inference. Visual conventions:

* filled circle  - percent change printed by the source (reported)
* filled square  - calculated from the source's own group means
* open circle    - approximation (for example a confidence-interval midpoint)
* open diamond   - duration-model output at the slider (always an approximation)
* solid line     - model inside the range the data cover
* dotted line    - interpolation between separate cohorts
* dashed line    - extrapolation beyond the data

Colour identifies the study and is fixed per study. No ground-analogue curve is
drawn anywhere, because no analogue function was available to draw.
"""

import math

import plotly.graph_objects as go

from duration_model import DurationModel
from evidence_catalog import (
    HarmonizedPoint,
    NOT_REPORTED,
    Series,
    format_n,
    format_number,
    series_label,
    source_reference,
    study_label,
)
from scenario_inputs import STUDY_IDS


# One fixed colour per study (validated categorical palette, fixed order).
_PALETTE = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100",
    "#e87ba4", "#008300", "#6250d6", "#e34948",
)
STUDY_COLOURS = dict(zip(STUDY_IDS, _PALETTE))

_SYMBOLS = {
    "reported": "circle",
    "calculated": "square",
    "digitized": "triangle-up",
    "approximation": "circle-open",
}
_LINE_STYLES = {
    "supported": ("solid", "Model inside the range the data cover"),
    "interpolated": ("dot", "Interpolated between separate cohorts"),
    "extrapolated": ("dash", "Extrapolated beyond the data"),
}
_Y_TITLE = "Change from the study's own baseline (%)"


def _wrap(text: str, width: int = 70) -> str:
    words, lines, line = text.split(), [], ""
    for word in words:
        if len(line) + len(word) + 1 > width and line:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    lines.append(line)
    return "<br>".join(lines)


def point_hover(series: Series, point: HarmonizedPoint) -> str:
    """Tooltip text: value, unit, dispersion, n, timepoint, value type, source."""
    observation = point.observation
    if point.percent_change is None:
        value = f"range {format_number(point.low)} to {format_number(point.high)} % (as printed)"
    else:
        value = f"{format_number(round(point.percent_change, 2))} % change from baseline"
    lines = [
        f"<b>{series_label(series)}</b>",
        f"Value: {value}",
        f"Original: {_wrap(point.original_text)}",
        f"Uncertainty: {point.dispersion_text}",
        f"Sample: {format_n(observation)}",
        f"Timepoint: {_wrap(observation.timepoint)}",
        f"Value type: {point.value_type}",
        f"Source: {study_label(observation.study_id)}, PDF page "
        f"{observation.pdf_page}, {observation.table_or_figure}",
    ]
    return "<br>".join(lines)


def _errors(value: float, low: float | None, high: float | None) -> dict[str, object]:
    if low is None or high is None:
        return {"type": "data", "visible": False}
    return {
        "type": "data",
        "symmetric": False,
        "array": [max(0.0, high - value)],
        "arrayminus": [max(0.0, value - low)],
        "visible": True,
        "thickness": 1.5,
        "width": 4,
    }


def _layout(figure: go.Figure, title: str, x_title: str, y_title: str, height: int) -> None:
    figure.update_layout(
        title={"text": title},
        xaxis_title=x_title,
        yaxis_title=y_title,
        height=height,
        legend={"orientation": "h", "yanchor": "top", "y": -0.25, "x": 0},
        hovermode="closest",
    )


def _style_legend(figure: go.Figure, kinds: set[str]) -> None:
    """Legend entries that explain the line styles, independent of any study."""
    for kind, (dash, label) in _LINE_STYLES.items():
        if kind in kinds:
            figure.add_trace(
                go.Scatter(
                    x=[None], y=[None], mode="lines", name=label,
                    line={"color": "#555555", "dash": dash, "width": 2},
                    hoverinfo="skip",
                )
            )


def create_duration_plot(
    rows: list[tuple[Series, HarmonizedPoint, DurationModel, dict[str, object]]],
    duration_days: float,
) -> go.Figure:
    """Outcome against mission duration: real anchor points plus the flagged model curve."""
    figure = go.Figure()
    kinds: set[str] = set()
    for series, point, model, output in rows:
        colour = STUDY_COLOURS[series.study_id]
        name = series_label(series)
        for segment in model.segments():
            kinds.add(segment.kind)
            figure.add_trace(
                go.Scatter(
                    x=list(segment.days), y=list(segment.values), mode="lines",
                    line={"color": colour, "width": 2, "dash": _LINE_STYLES[segment.kind][0]},
                    legendgroup=name, showlegend=False,
                    hovertemplate=(
                        f"<b>{name}</b><br>{model.label}<br>"
                        f"{_LINE_STYLES[segment.kind][1]}<br>"
                        "%{x:.0f} days: %{y:.1f} %<br>Value type: approximation"
                        "<extra></extra>"
                    ),
                )
            )
        anchors = [anchor for anchor in model.anchors if not anchor.is_defined_zero]
        for index, anchor in enumerate(anchors):
            error_x = {"type": "data", "visible": False}
            if anchor.day_low is not None and anchor.day_high is not None:
                error_x = {
                    "type": "data", "symmetric": False, "visible": True,
                    "array": [anchor.day_high - anchor.day],
                    "arrayminus": [anchor.day - anchor.day_low],
                    "thickness": 1.5, "width": 4,
                }
            hover = "<br>".join(
                [
                    f"<b>{name}</b>",
                    f"Measured group value: {format_number(round(anchor.value, 2))} %",
                    f"Mission duration: {format_number(anchor.day)} days"
                    + (
                        f" (horizontal bar: {format_number(anchor.day_low)}–"
                        f"{format_number(anchor.day_high)} days, {model.range_basis})"
                        if anchor.day_low is not None
                        else ""
                    ),
                    _wrap(anchor.label),
                    "Uncertainty bar: "
                    + (
                        f"{format_number(anchor.low)} to {format_number(anchor.high)} %"
                        if anchor.low is not None
                        else NOT_REPORTED
                    ),
                    f"Source: {_wrap(anchor.source)}",
                ]
            )
            is_selected = index == len(anchors) - 1
            figure.add_trace(
                go.Scatter(
                    x=[anchor.day], y=[anchor.value], mode="markers",
                    marker={
                        "color": colour, "size": 11,
                        "symbol": _SYMBOLS.get(point.value_type, "circle") if is_selected else "circle",
                        "line": {"color": colour, "width": 2},
                    },
                    error_y=_errors(anchor.value, anchor.low, anchor.high),
                    error_x=error_x,
                    name=name, legendgroup=name, showlegend=index == 0,
                    customdata=[point.observation.id] if is_selected else None,
                    hovertemplate=hover + "<extra></extra>",
                )
            )
        figure.add_trace(
            go.Scatter(
                x=[duration_days], y=[output["value"]], mode="markers",
                marker={
                    "color": colour, "size": 13, "symbol": "diamond-open",
                    "line": {"color": colour, "width": 2},
                },
                legendgroup=name, showlegend=False,
                hovertemplate=(
                    f"<b>{name}</b><br>Model value at {format_number(duration_days)} days: "
                    f"{format_number(round(float(output['value']), 1))} %<br>"
                    f"{model.label}<br>Status: {output['status']}<br>"
                    "Value type: approximation<extra></extra>"
                ),
            )
        )
    figure.add_trace(
        go.Scatter(
            x=[None], y=[None], mode="markers", name="Model value at the slider (approximation)",
            marker={"color": "#555555", "size": 12, "symbol": "diamond-open"},
            hoverinfo="skip",
        )
    )
    _style_legend(figure, kinds)
    figure.add_vline(x=duration_days, line_color="#555555", line_width=1, line_dash="dot")
    figure.add_hline(y=0, line_color="#999999", line_width=1)
    _layout(
        figure, "Outcome against mission duration", "Mission duration (days)", _Y_TITLE,
        460 + 18 * len(rows),
    )
    figure.update_xaxes(rangemode="tozero")
    return figure


def _compressed_day(day: float) -> float:
    return day + 1.0


def create_recovery_plot(
    series_list: list[Series],
    selected_ids: set[str],
) -> go.Figure | None:
    """Reported postflight timepoints only; points are not joined into a trajectory."""
    figure = go.Figure()
    days: list[float] = []
    for series in series_list:
        points = [
            point for point in series.points
            if point.plottable and point.percent_change is not None
            and point.recovery_day is not None
        ]
        if not points:
            continue
        days.extend(point.recovery_day for point in points)
    if not days:
        return None
    compress = max(days) > 60
    for series in series_list:
        points = [
            point for point in series.points
            if point.plottable and point.percent_change is not None
            and point.recovery_day is not None
        ]
        if not points:
            continue
        colour = STUDY_COLOURS[series.study_id]
        figure.add_trace(
            go.Scatter(
                x=[
                    _compressed_day(point.recovery_day) if compress else point.recovery_day
                    for point in points
                ],
                y=[point.percent_change for point in points],
                mode="markers",
                marker={
                    "color": colour,
                    "size": [14 if point.observation.id in selected_ids else 9 for point in points],
                    "symbol": [_SYMBOLS[point.value_type] for point in points],
                    "line": {"color": colour, "width": 2},
                },
                error_y={
                    "type": "data", "symmetric": False,
                    "array": [
                        0 if point.high is None else max(0.0, point.high - point.percent_change)
                        for point in points
                    ],
                    "arrayminus": [
                        0 if point.low is None else max(0.0, point.percent_change - point.low)
                        for point in points
                    ],
                    "thickness": 1.5, "width": 4,
                },
                name=series_label(series),
                customdata=[point.observation.id for point in points],
                hovertext=[point_hover(series, point) for point in points],
                hovertemplate="%{hovertext}<extra></extra>",
            )
        )
    figure.add_hline(y=0, line_color="#999999", line_width=1)
    _layout(
        figure, "Recovery over postflight days",
        "Days after landing (R+x)" + (" — compressed scale" if compress else ""),
        _Y_TITLE, 420 + 18 * len(figure.data),
    )
    if compress:
        ticks = [0, 1, 3, 7, 14, 30, 90, 365, 1095]
        ticks = [tick for tick in ticks if tick <= max(days) * 1.5]
        figure.update_xaxes(
            type="log",
            tickvals=[_compressed_day(tick) for tick in ticks],
            ticktext=[
                f"R+{tick}" if tick < 365 else f"{format_number(tick / 365)} yr"
                for tick in ticks
            ],
            range=[math.log10(0.8), math.log10(_compressed_day(max(days)) * 1.4)],
        )
    else:
        figure.update_xaxes(rangemode="tozero")
    return figure


def create_comparison_plot(
    entries: list[tuple[Series, HarmonizedPoint]],
    title: str,
) -> go.Figure | None:
    """Studies side by side on one axis, one row per series, never merged."""
    entries = [entry for entry in entries if entry[1].plottable]
    if not entries:
        return None
    figure = go.Figure()
    labels = [f"{series_label(series)} · {point.observation.timepoint.split(' (')[0]}" for series, point in entries]
    labels = [label if len(label) <= 78 else label[:75] + "…" for label in labels]
    seen: set[str] = set()
    for label, (series, point) in zip(labels, entries):
        colour = STUDY_COLOURS[series.study_id]
        study = study_label(series.study_id)
        hover = point_hover(series, point) + "<extra></extra>"
        if point.percent_change is None:
            figure.add_trace(
                go.Scatter(
                    x=[point.low, point.high], y=[label, label], mode="lines",
                    line={"color": colour, "width": 6},
                    name=study, legendgroup=study, showlegend=study not in seen,
                    customdata=[point.observation.id] * 2,
                    hovertemplate=hover,
                )
            )
        else:
            error = _errors(point.percent_change, point.low, point.high)
            figure.add_trace(
                go.Scatter(
                    x=[point.percent_change], y=[label], mode="markers",
                    marker={
                        "color": colour, "size": 11,
                        "symbol": _SYMBOLS[point.value_type],
                        "line": {"color": colour, "width": 2},
                    },
                    error_x=error,
                    name=study, legendgroup=study, showlegend=study not in seen,
                    customdata=[point.observation.id],
                    hovertemplate=hover,
                )
            )
        seen.add(study)
    figure.add_vline(x=0, line_color="#999999", line_width=1)
    _layout(figure, title, _Y_TITLE, "", 170 + 26 * len(entries))
    figure.update_yaxes(autorange="reversed", automargin=True, categoryorder="array", categoryarray=labels)
    return figure
