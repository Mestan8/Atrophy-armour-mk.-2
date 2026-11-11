"""Proof that restructuring the Explorer did not change any scientific output.

`fixtures/scenario_baseline.json` was captured from `build_scenario_view` before
the two-step Explorer work started (selections listed in the fixture). The
results endpoint must return exactly the same payload for each of them.
"""

import json
from pathlib import Path

import pytest

from api import build_scenario_view
from study_library import initialize_database


BASELINE = json.loads(
    (Path(__file__).parent / "fixtures" / "scenario_baseline.json").read_text(encoding="utf-8")
)


@pytest.fixture(scope="module")
def connection():
    database = initialize_database(":memory:")
    yield database
    database.close()


@pytest.mark.parametrize("case", BASELINE, ids=[json.dumps(case["selection"]) for case in BASELINE])
def test_results_payload_is_identical_to_the_baseline(connection, case):
    view = json.loads(json.dumps(build_scenario_view(connection, case["selection"])))
    assert view == case["view"]


def test_baseline_covers_the_required_model_cases():
    labels = [case["view"]["slider"]["model_label"] for case in BASELINE]
    warnings = [case["view"]["slider"]["warning"] for case in BASELINE]
    studies = {case["view"]["controls"][0]["value"] for case in BASELINE}
    categories = {case["view"]["controls"][1]["value"] for case in BASELINE}
    assert "Linear approximation (fallback)" in labels
    assert "Fitted to several cohorts (approximation)" in labels
    assert any(text and text.startswith("Extrapolation warning") for text in warnings)
    assert len(studies) >= 8 and len(categories) >= 5
