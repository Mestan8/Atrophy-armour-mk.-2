"""3D Simulator: provenance, endpoints, interpolation flags, clamping and cohort separation."""

import copy
import json

import pytest

import simulator_model as sim
from duration_model import normalized_shape
from evidence_catalog import VALUE_TYPES


def by_id(view: dict) -> dict:
    return {entry["id"]: entry for entry in view["parameters"]}


# ------------------------------------------------------------------- provenance


def test_every_value_has_a_source_and_value_type() -> None:
    document = sim.parameters()
    sources = document["sources"]
    for parameter in document["time_varying"]:
        for cohort, values in parameter["values"].items():
            for key in ("pre", "end", "recovery"):
                record = values.get(key)
                if record is None:
                    continue
                assert record["value_type"] in sim.SIM_VALUE_TYPES
                assert record["source"] in sources
                assert record["location"] and record["quote"]
                assert record["n_counts"]
    for record in document["static"]:
        assert record["value_type"] in sim.SIM_VALUE_TYPES
        assert record["source"] in sources and record["location"] and record["quote"]
    for category in document["fibre_type_distribution"]["categories"]:
        assert category["quote_pre"] and category["quote_end"]
    for source in sources.values():
        if source["kind"] == "external":
            assert source["citation"] and source["url"] and source["access"]


def test_illustrative_elements_are_labelled_illustrative() -> None:
    for record in sim.parameters()["illustrative"]:
        assert record["value_type"] == "illustrative"
        assert record["reason"]
    view = sim.evaluate(0)
    assert all(item["value_type"] == "illustrative" for item in view["illustrative"])
    assert "illustrative" in view["value_types"]


def test_simulator_types_do_not_change_the_shared_catalog() -> None:
    assert "illustrative" not in VALUE_TYPES
    assert set(VALUE_TYPES) <= set(sim.SIM_VALUE_TYPES)


@pytest.mark.parametrize(
    ("path", "change"),
    [
        (("time_varying", 0, "values", "all", "pre"), {"value_type": "guess"}),
        (("time_varying", 0, "values", "all", "pre"), {"quote": ""}),
        (("time_varying", 0, "values", "all", "end"), {"source": "nowhere"}),
        (("static", 0), {"location": None}),
        (("illustrative", 0), {"value_type": "reported"}),
        (("static", 2), {"assumed": None}),   # approximation without its assumption
    ],
)
def test_the_validator_rejects_missing_provenance(path, change) -> None:
    document = copy.deepcopy(sim.parameters())
    target = document
    for key in path:
        target = target[key]
    target.update(change)
    with pytest.raises(sim.SimulatorSchemaError):
        sim.validate(document)


# ------------------------------------------------------------- pinned endpoints

PINNED = {
    # id: (preflight, end of mission) for all crew, as printed
    "soleus_volume": (455, 383),            # Trappe Table 5, R+4
    "gastrocnemius_volume": (309, 274),     # Trappe Table 5, R+4
    "type_i_diameter": (98, 79),            # Fitts Table 2
    "type_i_csa": (7907, 4824),             # Fitts Table 2
    "type_ii_diameter": (95, 80),           # Fitts Table 5
    "type_ii_csa": (7358, 5245),            # Fitts Table 5
    "type_i_peak_force": (0.86, 0.56),      # Fitts Table 3
    "type_i_specific_tension": (115, 114),  # Fitts Table 3
    "type_i_vo": (0.85, 0.68),              # Fitts Table 3
    "type_i_peak_power": (14.20, 7.47),     # Fitts Table 8
    "type_ii_peak_power": (51.72, 28.52),   # Fitts Table 10
    "thin_filament_density": (2253, 2744),  # Fitts PDF page 14
    "thin_thick_ratio": (2.2, 2.9),         # Fitts PDF page 14
    "thick_filament_density": (999, 945),   # Fitts PDF page 5
}


def test_day_zero_returns_the_preflight_values_as_reported() -> None:
    view = sim.evaluate(0)
    entries = by_id(view)
    assert view["day"]["status"] == "preflight"
    for parameter_id, (pre, _) in PINNED.items():
        assert entries[parameter_id]["value"] == pytest.approx(pre)
        assert entries[parameter_id]["value_type"] == "reported"
        assert entries[parameter_id]["percent_change"] == pytest.approx(0)


def test_end_of_mission_returns_the_reported_postflight_values() -> None:
    view = sim.evaluate(177)
    entries = by_id(view)
    assert view["day"]["status"] == "end_of_mission"
    for parameter_id, (_, end) in PINNED.items():
        assert entries[parameter_id]["value"] == pytest.approx(end)
        assert entries[parameter_id]["value_type"] == "reported"
    assert entries["soleus_volume"]["timepoint"].startswith("R+4")
    assert entries["type_i_diameter"]["timepoint"].startswith("R+0")
    assert entries["soleus_volume"]["reported_change"]["value"] == -15
    shares = {c["id"]: c["value"] for c in view["fibre_types"]["categories"]}
    assert shares["I"] == 71 and sim.evaluate(0)["fibre_types"]["categories"][0]["value"] == 88


def test_interpolated_days_are_flagged_as_approximations() -> None:
    view = sim.evaluate(60)
    assert view["day"]["status"] == "interpolated"
    entries = by_id(view)
    volume = entries["soleus_volume"]
    assert volume["value_type"] == "approximation"
    assert 383 < volume["value"] < 455
    assert volume["assumption"] and volume["formula"]
    assert volume["dispersion"] == []
    assert all(c["value_type"] == "approximation" for c in view["fibre_types"]["categories"])
    assert any("approximation" in notice.lower() for notice in view["notices"])


def test_thin_filament_values_are_not_interpolated_between_endpoints() -> None:
    entries = by_id(sim.evaluate(100))
    thin = entries["thin_filament_density"]
    assert thin["status"] == "held_at_preflight"
    assert thin["value"] == 2253 and thin["value_type"] == "approximation"
    assert "17-day" in thin["assumption"]


def test_out_of_range_days_are_clamped_and_flagged() -> None:
    for requested, shown in ((250, 177), (-5, 0)):
        view = sim.evaluate(requested)
        assert view["day"]["clamped"] is True
        assert view["day"]["value"] == shown
        assert any(notice.startswith("Clamped") for notice in view["notices"])
    assert sim.evaluate(120)["day"]["clamped"] is False
    assert sim.evaluate("not a number")["day"]["value"] == 0


def test_the_spaceflight_shape_reuses_the_leblanc_multi_cohort_curve() -> None:
    curve = normalized_shape("soleus_volume", 177)
    assert curve is not None
    assert sim.shape_fraction("spaceflight_cohorts", 8) == pytest.approx(6.3 / 16.8)
    assert sim.shape_fraction("spaceflight_cohorts", 17) == pytest.approx(9.8 / 16.8)
    assert sim.shape_fraction("spaceflight_cohorts", 115) == pytest.approx(1.0)
    assert sim.shape_fraction("linear", 88.5) == pytest.approx(0.5)
    linear = by_id(sim.evaluate(88.5, shape="linear"))["soleus_volume"]["value"]
    assert linear == pytest.approx((455 + 383) / 2)


def test_recovery_snaps_to_r19_for_volume_only() -> None:
    view = sim.evaluate(177, phase="recovery")
    entries = by_id(view)
    assert entries["soleus_volume"]["value"] == 408
    assert entries["soleus_volume"]["timepoint"].startswith("R+19")
    assert entries["soleus_volume"]["reported_change"]["value"] == -9
    assert entries["type_i_diameter"]["value"] == 79
    assert "Not measured at R+19" in entries["type_i_diameter"]["recovery_note"]


# ------------------------------------------------------------------- cohorts


def test_subgroups_use_their_own_values_and_n() -> None:
    high = by_id(sim.evaluate(177, cohort="high_treadmill"))
    low = by_id(sim.evaluate(0, cohort="low_treadmill"))
    assert high["type_i_diameter"]["value"] == 82 and high["type_i_diameter"]["n"] == 220
    assert low["type_i_diameter"]["value"] == 104
    volume = high["soleus_volume"]
    assert volume["value_type"] == "calculated" and volume["n"] == 4
    assert volume["pre"]["value"] == pytest.approx(421.8)
    assert volume["value"] == pytest.approx(380.0)
    assert low["soleus_volume"]["value"] == pytest.approx(482.2)


def test_subgroups_never_borrow_all_crew_values() -> None:
    for cohort in ("high_treadmill", "low_treadmill"):
        view = sim.evaluate(177, cohort=cohort)
        entries = by_id(view)
        for parameter_id in ("thin_filament_density", "thin_thick_ratio", "type_ii_peak_power"):
            assert entries[parameter_id]["available"] is False
            assert entries[parameter_id]["value"] is None
        assert all(c["value_type"] == "calculated" for c in view["fibre_types"]["categories"])
        assert not any(d["id"] == "thin_reach_fraction" for d in view["derived"])
    mhc = sim.evaluate(177, cohort="high_treadmill")["fibre_types"]
    assert mhc["n"] == 3   # E, G and H; subject B has no fibre-type data
    assert mhc["categories"][0]["value"] == pytest.approx(79.7)


def test_derived_drawing_quantities_state_their_formula() -> None:
    view = sim.evaluate(177)
    derived = {item["id"]: item for item in view["derived"]}
    assert derived["soleus_transverse_scale"]["value"] == pytest.approx((383 / 455) ** 0.5)
    assert derived["thin_reach_fraction"]["value"] == pytest.approx(2744 / 3251)
    assert derived["thin_reach_fraction"]["pre_value"] == pytest.approx(2253 / 3251)
    assert derived["thick_lattice_spacing"]["value"] == pytest.approx(34.0, abs=0.1)
    for item in view["derived"]:
        assert item["formula"] and item["value_type"] in sim.SIM_VALUE_TYPES


def test_the_view_is_json_serialisable_and_carries_the_notices() -> None:
    view = sim.evaluate(30, cohort="low_treadmill", shape="linear")
    json.dumps(view)
    assert view["notice"].startswith("This page visualizes published group averages")
    assert any("R+0" in notice and "R+4" in notice for notice in view["notices"])
