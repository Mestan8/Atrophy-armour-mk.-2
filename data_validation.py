"""Basic structural checks for tabular data."""

from collections.abc import Sequence

import pandas as pd


def find_missing_columns(
    data: pd.DataFrame, required_columns: Sequence[str]
) -> list[str]:
    """Return required column names that are absent, preserving input order."""
    return [column for column in required_columns if column not in data.columns]
