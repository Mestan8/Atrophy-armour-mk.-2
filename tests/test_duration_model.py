"""Duration model: anchors, supported range, extrapolation flags and fallback flagging."""

import pytest

from duration_model import (
    LINEAR_FALLBACK,
    LINEAR_NOTICE,
    MULTI_COHORT,
    duration_support,
    model_for,
)
from evidence_catalog import all_series


def series(study_id, outcome_id, cohort_id="all", subgroup="all"):
    for item in all_series():
        if (
            item.study_id == study_id
            and item.outcome_id == outcome_id
            and item.first.cohort_id == cohort_id
            and item.first.subgroup == subgroup
        ):
            return item
    raise AssertionError("series not found")


def test_linear_fallback_passes_through_zero_and_the_measured_value():
    trunk = series("greene-2021", "trunk_csa_ct")
    model = model_for(trunk)
    assert model.kind == LINEAR_FALLBACK
    assert model.notice == LINEAR_NOTICE
    zero, measured = model.anchors
    assert zero.is_defined_zero and (zero.day, zero.value) == (0, 0)
    assert (measured.day, measured.value) == (150, -4.7)
    assert model.value_at(0) == 0
    assert model.value_at(150) == pytest.approx(-4.7)
    assert model.value_at(75) == pytest.approx(-2.35)


def test_supported_range_uses_reported_min_max_when_printed():
    model = model_for(series("fitts-2010", "soleus_type_i_diameter"))
    assert (model.supported_low, model.supported_high, model.default_day) == (161, 192, 177)
    assert "minimum and maximum" in model.range_basis


def test_supported_range_from_mean_and_sd_says_it_is_not_a_min_max():
    model = model_for(series("english-2015", "knee_extension_60", subgroup="all"))
    assert (model.supported_low, model.supported_high) == (125, 201)
    assert "not an observed minimum and maximum" in model.range_basis


def test_every_output_is_an_approximation_and_extrapolation_is_flagged():
    model = model_for(series("trappe-2009", "calf_soleus_volume"))
    inside = model.evaluate(177)
    assert inside["value_type"] == "approximation"
    assert inside["status"] == "supported" and inside["warning"] is None
    for day in (60, 230):
        outside = model.evaluate(day)
        assert outside["status"] == "extrapolated"
        assert outside["value_type"] == "approximation"
        assert "Extrapolation" in outside["warning"]


def test_extrapolated_segments_are_drawn_separately():
    model = model_for(series("trappe-2009", "calf_soleus_volume"))
    kinds = [segment.kind for segment in model.segments()]
    assert kinds == ["extrapolated", "supported", "extrapolated"]
    supported = model.segments()[1]
    assert supported.days == (161, 192)


def test_multi_cohort_model_uses_real_cohort_means():
    soleus = series("leblanc-2000", "soleus_volume", "mir_all")
    model = model_for(soleus)
    assert model.kind == MULTI_COHORT
    days = [anchor.day for anchor in model.anchors]
    values = [anchor.value for anchor in model.anchors]
    assert days == [0, 8, 17, 161]
    assert values[1] == -6.3  # External source E1, 8-day STS-47
    assert values[2] == -9.8  # LeBlanc Table 1, Spacelab landing day
    assert values[3] == pytest.approx(-16.8)  # LeBlanc text, 83.2% of baseline
    assert "External source E1" in model.sources[1]


def test_multi_cohort_model_is_flat_across_the_long_duration_span():
    model = model_for(series("leblanc-2000", "soleus_volume", "mir_all"))
    assert model.value_at(115) == pytest.approx(model.value_at(197))
    assert model.status_at(150) == "supported"
    assert model.status_at(60) == "interpolated"
    assert model.value_at(60) == pytest.approx(-9.8 + (60 - 17) / (115 - 17) * (-16.8 + 9.8))
    late = model.evaluate(250)
    assert late["status"] == "extrapolated" and "longer than the longest flight" in late["warning"]


def test_multi_cohort_without_an_e1_point_still_uses_both_leblanc_cohorts():
    model = model_for(series("leblanc-2000", "quadriceps_volume", "mir_all"))
    assert [anchor.day for anchor in model.anchors] == [0, 17, 161]


def test_the_multi_cohort_curve_is_attached_once_per_muscle():
    assert model_for(series("leblanc-2000", "soleus_volume", "spacelab")) is None
    assert model_for(series("leblanc-2000", "soleus_volume", "mir_landing_day_subset")) is None


def test_no_model_is_built_on_an_abstract_range():
    assert model_for(series("gopalakrishnan-2010", "thigh_volume")) is None
    assert model_for(series("gopalakrishnan-2010", "calf_volume")) is None


def test_approximate_month_ranges_are_labelled_as_converted():
    observation = series("greene-2021", "trunk_csa_ct").first
    reference, low, high, basis = duration_support(observation)
    assert (reference, low, high) == (150, 120, 180)
    assert "approximate" in basis and "no mean is reported" in basis
