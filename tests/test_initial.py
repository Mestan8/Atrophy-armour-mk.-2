import sqlite3
from pathlib import Path

import pandas as pd
import pytest
from plotly.graph_objects import Figure

from data_validation import find_missing_columns
from database import connect_database
from plotting import (
    create_fibre_comparison_plot,
    create_recovery_plot,
    create_relative_change_plot,
    create_scatter_plot,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_initial_project_files_exist() -> None:
    expected_files = [
        "app.py",
        "model.py",
        "data_validation.py",
        "database.py",
        "plotting.py",
        "requirements.txt",
        "README.md",
        ".gitignore",
        "data/README.md",
        "study_library.py",
        "inspect_references.py",
    ]

    assert all((PROJECT_ROOT / file_path).is_file() for file_path in expected_files)


def test_research_pdf_is_not_ignored() -> None:
    ignore_rules = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "*.pdf" not in ignore_rules.splitlines()


def test_find_missing_columns_preserves_required_column_order() -> None:
    data = pd.DataFrame({"subject": [1], "preflight": [10.0]})

    assert find_missing_columns(data, ["subject", "postflight", "recovery"]) == [
        "postflight",
        "recovery",
    ]


def test_connect_database_supports_in_memory_database() -> None:
    connection = connect_database(":memory:")
    try:
        assert isinstance(connection, sqlite3.Connection)
        assert connection.execute("SELECT 1").fetchone() == (1,)
    finally:
        connection.close()


def test_create_scatter_plot_uses_supplied_columns() -> None:
    data = pd.DataFrame({"preflight": [10.0, 12.0], "postflight": [8.0, 11.0]})

    figure = create_scatter_plot(data, "preflight", "postflight")

    assert isinstance(figure, Figure)
    assert list(figure.data[0].x) == [10.0, 12.0]
    assert list(figure.data[0].y) == [8.0, 11.0]


def test_create_scatter_plot_reports_missing_columns() -> None:
    data = pd.DataFrame({"preflight": [10.0]})

    with pytest.raises(ValueError, match="Missing required columns: postflight"):
        create_scatter_plot(data, "preflight", "postflight")


def test_recovery_plot_uses_days_after_return_and_reported_ci() -> None:
    figure = create_recovery_plot(
        [
            {
                "timepoint": "R+5",
                "days_after_return": 5,
                "mean_change": -11.0,
                "ci_lower": -14.8,
                "ci_upper": -7.2,
                "sample_size": 37,
            },
            {
                "timepoint": "R+14",
                "days_after_return": 14,
                "mean_change": -12.2,
                "ci_lower": -15.6,
                "ci_upper": -8.8,
                "sample_size": 34,
            },
        ],
        "Knee extension recovery",
    )

    assert figure is not None
    assert figure.layout.xaxis.title.text == "Days after return"
    assert list(figure.data[0].x) == [5, 14]
    assert list(figure.data[0].y) == [-11.0, -12.2]
    assert figure.data[0].mode == "markers"
    assert list(figure.data[0].error_y.array) == pytest.approx([3.8, 3.4])
    assert list(figure.data[0].error_y.arrayminus) == pytest.approx([3.8, 3.4])


def test_recovery_plot_requires_multiple_observations() -> None:
    assert create_recovery_plot([], "No recovery observations") is None
    assert create_recovery_plot(
        [
            {
                "timepoint": "R+5",
                "days_after_return": 5,
                "mean_change": -11.0,
                "ci_lower": -14.8,
                "ci_upper": -7.2,
                "sample_size": 37,
            }
        ],
        "Single observation",
    ) is None


def test_relative_change_plot_preserves_ci_asymmetric_error_lengths() -> None:
    figure = create_relative_change_plot(
        -11.0,
        "% mean change from L-60",
        "Observed R+5 group mean",
        confidence_interval=(-14.8, -7.2),
    )

    assert list(figure.data[0].y) == [-11.0]
    assert figure.layout.yaxis.title.text == "% mean change from L-60"
    assert list(figure.data[0].error_y.array) == pytest.approx([3.8])
    assert list(figure.data[0].error_y.arrayminus) == pytest.approx([3.8])


def test_fibre_plot_keeps_preflight_and_landing_day_means_separate() -> None:
    figure = create_fibre_comparison_plot(
        98.0,
        79.0,
        "μm",
        "Soleus fibre diameter",
    )

    assert list(figure.data[0].x) == [
        "Preflight (L-55 ± 2 days)",
        "Landing day (R+0)",
    ]
    assert list(figure.data[0].y) == [98.0, 79.0]
    assert figure.layout.yaxis.title.text == "Published group mean (μm)"
