"""Generic plotting helpers; these do not perform scientific inference."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from data_validation import find_missing_columns


def create_relative_change_plot(
    mean_change: float,
    unit: str,
    title: str,
    *,
    confidence_interval: tuple[float, float] | None = None,
    observation_id: str | None = None,
) -> go.Figure:
    """Plot one observed relative change and source-reported uncertainty."""
    figure = go.Figure()
    error_y: dict[str, object] = {"type": "data", "visible": False}
    if confidence_interval is not None:
        error_y = {
            "type": "data",
            "symmetric": False,
            "array": [max(0.0, confidence_interval[1] - mean_change)],
            "arrayminus": [max(0.0, mean_change - confidence_interval[0])],
            "visible": True,
        }
    figure.add_trace(
        go.Bar(
            x=[title],
            y=[mean_change],
            error_y=error_y,
            name="Observed group mean",
            customdata=[observation_id] if observation_id is not None else None,
            hovertemplate="%{y:.1f}%<extra>Observed group mean</extra>",
        )
    )
    figure.add_hline(y=0, line_color="gray", line_width=1)
    figure.update_layout(
        title=title,
        xaxis_title="Selected observation",
        yaxis_title=unit,
        showlegend=False,
    )
    return figure


def create_recovery_plot(
    observations: list[dict[str, object]],
    title: str,
) -> go.Figure | None:
    """Plot verified English et al. postflight means and reported 95% CIs."""
    if len(observations) < 2:
        return None
    observations = sorted(
        observations, key=lambda item: int(item["days_after_return"])
    )
    means = [float(item["mean_change"]) for item in observations]
    figure = go.Figure(
        go.Scatter(
            x=[int(item["days_after_return"]) for item in observations],
            y=means,
            mode="markers",
            name="Observed group mean",
            error_y={
                "type": "data",
                "symmetric": False,
                "array": [
                    max(0.0, float(item["ci_upper"]) - mean)
                    for item, mean in zip(observations, means)
                ],
                "arrayminus": [
                    max(0.0, mean - float(item["ci_lower"]))
                    for item, mean in zip(observations, means)
                ],
                "visible": True,
            },
            customdata=(
                [item.get("observation_id") for item in observations]
                if all(item.get("observation_id") for item in observations)
                else None
            ),
            text=[f"n={item['sample_size']}" for item in observations],
            hovertemplate=(
                "R+%{x}<br>Mean change: %{y:.1f}%"
                "<br>%{text}<extra></extra>"
            ),
        )
    )
    figure.add_hline(y=0, line_color="gray", line_width=1)
    figure.update_layout(
        title=title,
        xaxis_title="Days after return",
        yaxis_title="Mean change from L-60 (%)",
        showlegend=False,
    )
    return figure


def create_fibre_comparison_plot(
    preflight_value: float,
    postflight_value: float,
    unit: str,
    title: str,
    *,
    observation_ids: tuple[str, str] | None = None,
) -> go.Figure:
    """Compare published fibre-level preflight and landing-day group means."""
    figure = go.Figure(
        go.Bar(
            x=["Preflight (L-55 ± 2 days)", "Landing day (R+0)"],
            y=[preflight_value, postflight_value],
            name="Published group mean",
            marker={"color": ["#4C78A8", "#F58518"]},
            customdata=list(observation_ids) if observation_ids is not None else None,
            hovertemplate="%{x}<br>%{y:g} " + unit + "<extra></extra>",
        )
    )
    figure.update_layout(
        title=title,
        xaxis_title="Biopsy timepoint",
        yaxis_title=f"Published group mean ({unit})",
        showlegend=False,
    )
    return figure


def create_scatter_plot(
    data: pd.DataFrame, x_column: str, y_column: str
) -> go.Figure:
    """Create a scatter plot for two existing columns in a supplied dataset."""
    missing_columns = find_missing_columns(data, [x_column, y_column])
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    return px.scatter(data_frame=data, x=x_column, y=y_column)
