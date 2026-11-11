"""Evidence catalog: schema/provenance rules, pinned source values, harmonization."""

import json
from pathlib import Path

import pytest

from evidence_catalog import (
    CATEGORIES,
    VALUE_TYPES,
    EvidenceSchemaError,
    all_series,
    build_observation,
    calculate_change,
    catalog,
    external_sources,
    format_value,
    load_observations,
)
from study_library import STUDIES


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STUDY_IDS = {str(study["id"]) for study in STUDIES}


def find(study_id, outcome_id, cohort_id="all", kind=None, timepoint=None, subgroup=None):
    matches = [
        item
        for item in catalog()
        if item.study_id == study_id
        and item.outcome_id == outcome_id
        and item.cohort_id == cohort_id
        and (kind is None or item.measure_kind == kind)
        and (timepoint is None or item.timepoint.startswith(timepoint))
        and (subgroup is None or item.subgroup == subgroup)
    ]
    assert len(matches) == 1, [item.id for item in matches]
    return matches[0]


def point(study_id, outcome_id, cohort_id="all", timepoint=None, subgroup="all"):
    for series in all_series():
        first = series.first
        if (
            series.study_id == study_id
            and series.outcome_id == outcome_id
            and first.cohort_id == cohort_id
            and first.subgroup == subgroup
        ):
            for item in series.points:
                if timepoint is None or item.observation.timepoint.startswith(timepoint):
                    return item
    raise AssertionError("point not found")


# --- Schema and provenance -----------------------------------------------------


def test_every_library_study_has_catalog_records():
    assert {item.study_id for item in catalog()} == STUDY_IDS


def test_every_observation_carries_provenance_and_a_value_type():
    for item in catalog():
        assert item.value_type in VALUE_TYPES
        assert item.source_file and (PROJECT_ROOT / "data" / "references" / item.source_file).is_file()
        assert item.pdf_page >= 1
        assert item.table_or_figure.strip()
        assert item.source_wording.strip()
        assert item.verification_status == "rendered_page_checked"
        assert item.outcome_category in CATEGORIES
        assert item.n_counts.strip()
        assert item.mission_duration["wording"] and item.mission_duration["pdf_page"]


def test_approximations_carry_a_formula_and_an_explanation():
    approximations = [item for item in catalog() if item.value_type == "approximation"]
    assert approximations
    for item in approximations:
        assert item.formula
        assert item.notes


def test_observation_ids_are_unique():
    ids = [item.id for item in catalog()]
    assert len(ids) == len(set(ids))


def _valid_record(**changes):
    record = {
        "study_id": "trappe-2009",
        "outcome_category": "muscle_size",
        "outcome_id": "test",
        "outcome_name": "Test outcome",
        "region": "calf_ankle",
        "muscle_or_joint": "soleus",
        "biological_level": "whole muscle",
        "measure_kind": "percent_change",
        "unit": "%",
        "statistic_type": "mean",
        "value": -1.0,
        "dispersion_type": "SE",
        "dispersion": [1.0],
        "n": 9,
        "n_counts": "crew members",
        "cohort_id": "all",
        "cohort": "test",
        "subgroup": "all",
        "sex": "not reported",
        "countermeasure_id": "x",
        "countermeasure": "x",
        "mission_duration": {"value": 177, "wording": "177 days", "pdf_page": 2},
        "baseline_timepoint": "Preflight",
        "timepoint": "R+4",
        "timepoint_kind": "postflight",
        "recovery_day": 4,
        "pdf_page": 5,
        "table_or_figure": "Table 5",
        "source_wording": "words",
        "value_type": "reported",
        "verification_status": "rendered_page_checked",
    }
    record.update(changes)
    return record


@pytest.mark.parametrize(
    "changes",
    [
        {"value_type": None},
        {"value_type": "guessed"},
        {"source_wording": ""},
        {"pdf_page": None},
        {"table_or_figure": ""},
        {"study_id": "new-study-2024"},
        {"value_type": "calculated"},  # needs a formula
        {"value_type": "approximation", "formula": "x"},  # needs notes
        {"dispersion_type": "95% CI", "dispersion": [1.0]},
        {"n": 0},
        {"mission_duration": {"value": 177}},
        {"timepoint_kind": "preflight", "recovery_day": 4},
    ],
)
def test_schema_rejects_records_without_required_provenance(changes):
    with pytest.raises(EvidenceSchemaError):
        build_observation(_valid_record(**changes))


def test_schema_accepts_a_complete_record():
    assert build_observation(_valid_record()).value == -1.0


def test_loader_rejects_a_file_with_an_unsourced_value(tmp_path):
    record = _valid_record(source_wording="")
    (tmp_path / "bad.json").write_text(
        json.dumps({"study_id": "trappe-2009", "blocks": [{"fields": list(record), "rows": [list(record.values())]}]}),
        encoding="utf-8",
    )
    with pytest.raises(EvidenceSchemaError):
        load_observations(tmp_path)


def test_external_sources_are_separate_from_the_library():
    sources = external_sources()
    assert [source["id"] for source in sources] == ["E1", "E2", "E3", "E4"]
    assert not {source["id"] for source in sources} & STUDY_IDS
    assert len(STUDIES) == 8
    for source in sources:
        assert source["url"].startswith("https://")
        assert source["evidence_type"] in {"spaceflight", "analogue"}


# --- Pinned values (each checked against the rendered PDF page) ---------------


def test_english_2015_pins():
    knee = find("english-2015", "knee_extension_60", timepoint="R+5")
    assert (knee.value, knee.dispersion, knee.n, knee.pdf_page, knee.table_or_figure) == (
        -11.0, (-7.2, -14.8), 37, 4, "Table III",
    )
    women = find("english-2015", "knee_flexion_180", cohort_id="women")
    assert (women.value, women.dispersion, women.n, women.subgroup) == (-21.9, (-9.0, -34.8), 8, "women")
    ired = find("english-2015", "trunk_extension_60", cohort_id="ired")
    assert (ired.value, ired.dispersion, ired.n, ired.timepoint.startswith("R+14")) == (
        -7.4, (0.3, -15.2), 12, True,
    )
    assert len([item for item in catalog() if item.study_id == "english-2015"]) == 82


def test_fitts_2010_pins_keep_fibre_counts_separate_from_crew():
    pre = find("fitts-2010", "soleus_type_i_diameter", timepoint="Preflight")
    post = find("fitts-2010", "soleus_type_i_diameter", timepoint="R+0")
    assert (pre.value, pre.dispersion, pre.n, pre.pdf_page) == (98, (1,), 540, 6)
    assert (post.value, post.n) == (79, 458)
    assert "fibres" in pre.n_counts and "not participants" in pre.n_counts
    force = find("fitts-2010", "soleus_type_i_peak_force", timepoint="R+0")
    assert (force.value, force.pdf_page, force.table_or_figure) == (0.56, 7, "Table 3")
    vo = find("fitts-2010", "gastrocnemius_type_ii_shortening_velocity", "low_treadmill", timepoint="R+0")
    assert (vo.value, vo.n, vo.pdf_page) == (2.76, 81, 9)


def test_trappe_2009_pins():
    soleus = find("trappe-2009", "calf_soleus_volume", kind="percent_change", timepoint="R+4")
    assert (soleus.value, soleus.dispersion, soleus.dispersion_type, soleus.pdf_page) == (-15, (2,), "SE", 5)
    combined = find("trappe-2009", "calf_gastrocnemius_soleus_volume", kind="level", timepoint="Preflight")
    assert (combined.value, combined.dispersion, combined.unit) == (764, (47,), "cm³")
    mvc = find("trappe-2009", "calf_isometric_mvc", kind="level", timepoint="Preflight")
    assert (mvc.value, mvc.dispersion, mvc.pdf_page) == (144, (11,), 6)
    fast = find("trappe-2009", "calf_isokinetic_180", kind="percent_change", timepoint="R+13")
    assert (fast.value, fast.dispersion) == (-25, (10,))


def test_sprint_2020_pins_including_a_suspect_cell_kept_as_printed():
    knee = find("sprint-2020", "knee_extension_60", "con", timepoint="R+5")
    assert (knee.value, knee.dispersion, knee.unit, knee.pdf_page) == (194, (11,), "Nm", 3)
    lean = find("sprint-2020", "leg_lean_mass", "sprint", timepoint="R+7")
    assert (lean.value, lean.dispersion) == (18.28, (0.04,))
    assert "typographical error" in lean.notes
    vo2 = find("sprint-2020", "vo2peak_absolute", "sprint", timepoint="R+1")
    assert (vo2.value, vo2.recovery_day) == (2.91, 1)
    work = find("sprint-2020", "knee_extension_work_180", "con", timepoint="Preflight")
    assert (work.value, work.unit, work.outcome_category) == (2657, "J", "endurance")
    assert not [
        item for item in catalog()
        if item.study_id == "sprint-2020" and item.outcome_id.startswith("trunk") and item.timepoint == "R+5"
    ]


def test_leblanc_2000_pins_with_signs_from_the_rendered_page():
    gastroc = find("leblanc-2000", "gastrocnemius_volume", "mir_landing_day_subset", timepoint="R+0")
    assert (gastroc.value, gastroc.dispersion, gastroc.n, gastroc.dispersion_type) == (-23.8, (4.0,), 6, "SD")
    psoas = find("leblanc-2000", "psoas_volume", "spacelab", timepoint="R+2")
    assert psoas.value == 0.6
    soleus = find("leblanc-2000", "soleus_volume", "mir_all")
    assert (soleus.value, soleus.measure_kind, soleus.n) == (83.2, "percent_of_baseline", 16)
    lean = find("leblanc-2000", "lean_body_mass", "mir_dxa", kind="level", timepoint="Preflight")
    assert (lean.value, lean.dispersion, lean.pdf_page) == (59.42, (5.81,), 5)


def test_gopalakrishnan_2010_is_abstract_level_and_the_calf_range_is_not_charted():
    calf = find("gopalakrishnan-2010", "calf_volume")
    assert calf.value is None and calf.dispersion == (-10, 16)
    assert calf.exclude_from_charts and "ambiguous" in calf.exclude_from_charts
    knee = find("gopalakrishnan-2010", "knee_strength")
    assert (knee.dispersion, knee.dispersion_type, knee.pdf_page) == ((-10.4, -24.1), "range", 1)
    work = find("gopalakrishnan-2010", "endurance_total_work")
    assert (work.value, work.dispersion_type) == (-14, "none")
    for item in catalog():
        if item.study_id == "gopalakrishnan-2010":
            assert "Abstract" in item.table_or_figure and "Abstract-level" in item.notes


def test_greene_2021_pins():
    csa = find("greene-2021", "trunk_csa_ct", kind="percent_change", timepoint="Post-flight return")
    assert (csa.value, csa.dispersion, csa.n, csa.pdf_page) == (-4.7, (1.1,), 16, 17)
    late = find("greene-2021", "trunk_csa_ct", kind="percent_change", timepoint="2–4 years")
    assert (late.value, late.n, late.recovery_day) == (0.8, 8, 1095)
    smi = find("greene-2021", "skeletal_muscle_index_ct")
    assert (smi.value, smi.n) == (-5.2, 6)


def test_scott_2023_ci_midpoint_is_flagged_as_an_approximation():
    calf = find("scott-2023", "calf_csa")
    assert calf.dispersion == (-15.75, -7.82)
    assert calf.value == pytest.approx(-11.79, abs=0.01)
    assert calf.value_type == "approximation"
    assert calf.formula == "(lower CI bound + upper CI bound) / 2"
    assert "approximation" in format_value(calf)
    vo2 = find("scott-2023", "vo2peak", timepoint="First postflight")
    assert (vo2.value, vo2.value_type, vo2.pdf_page) == (-7.4, "reported", 2)


# --- Percent-change arithmetic and harmonization -------------------------------


def test_calculate_change_signs_and_values():
    loss = calculate_change(98, 79, "μm")
    assert loss.absolute_change == -19
    assert loss.percent_change == pytest.approx(-19.387755, rel=1e-6)
    gain = calculate_change(88, 94, "kg")
    assert gain.percent_change == pytest.approx(6.818182, rel=1e-6)
    with pytest.raises(ValueError):
        calculate_change(0, 1, "kg")
    with pytest.raises(ValueError):
        calculate_change(1, 2, "")


def test_printed_percent_change_is_preferred_over_a_calculated_one():
    trappe = point("trappe-2009", "calf_soleus_volume", timepoint="R+4")
    assert trappe.percent_change == -15 and trappe.value_type == "reported"


def test_level_only_series_are_calculated_with_the_formula_shown():
    fitts = point("fitts-2010", "soleus_type_i_peak_force")
    assert fitts.percent_change == pytest.approx(-34.88, abs=0.01)
    assert fitts.value_type == "calculated"
    assert "(0.56 − 0.86) / 0.86 × 100" in fitts.formula
    assert fitts.low is None and "not reported" in fitts.dispersion_text


def test_percent_of_baseline_is_converted_with_its_sd_kept():
    mir = point("leblanc-2000", "soleus_volume", "mir_all")
    assert mir.percent_change == pytest.approx(-16.8)
    assert (mir.low, mir.high) == pytest.approx((-21.2, -12.4))
    assert mir.value_type == "calculated"


def test_ci_bounds_are_ordered_whatever_order_they_were_printed_in():
    english = point("english-2015", "knee_extension_60", timepoint="R+5")
    assert (english.low, english.high) == (-14.8, -7.2)


def test_series_never_mix_studies_or_cohorts():
    for series in all_series():
        keys = {(item.observation.study_id, item.observation.cohort_id) for item in series.points}
        assert len(keys) == 1


def test_fibre_type_share_is_listed_but_not_on_the_percent_axis():
    share = point("trappe-2009", "soleus_mhc_i_share")
    assert share.percent_change is None and not share.plottable


def test_committed_evidence_matrix_matches_the_catalog():
    from build_evidence_matrix import MATRIX_PATH, render

    assert MATRIX_PATH.read_text(encoding="utf-8") == render()
