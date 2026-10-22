"""Streamlit entry point for the Atrophy Armour prototype."""

import sqlite3

import streamlit as st

from model import ScenarioResult, analyze_scenario
from plotting import (
    create_fibre_comparison_plot,
    create_recovery_plot,
    create_relative_change_plot,
)
from scenario_evidence import (
    seed_abstract_context_measurements,
    seed_reference_measurements,
    verified_english_recovery_observations,
)
from scenario_inputs import (
    MISSION_DURATION_DEFAULT_DAYS,
    MISSION_DURATION_MAX_DAYS,
    MISSION_DURATION_MIN_DAYS,
    ScenarioInputs,
    allowed_comparison_groups,
    allowed_outcomes,
    allowed_regions,
    allowed_timepoints,
)
from study_library import (
    MeasurementInput,
    add_measurement,
    get_study,
    initialize_database,
    list_measurements,
    list_studies,
    mark_measurement_source_verified,
)
from scenario_ui import show_scenario_explorer as show_refined_scenario_explorer


def _legacy_show_scenario_explorer(connection: sqlite3.Connection) -> None:
    studies = list_studies(connection)
    study_by_id = {str(study["id"]): study for study in studies}
    engine_study_ids = [
        study_id for study_id in ("english-2015", "fitts-2010")
        if study_id in study_by_id
    ]

    st.subheader("Scenario Explorer")
    st.write(
        "Explore source-reported postflight observations. Mission duration is "
        "context only; it is not used to scale or predict muscle change."
    )
    if st.button("Reset scenario to defaults", key="scenario_reset"):
        for widget_key in tuple(st.session_state):
            if (
                widget_key.startswith("scenario_")
                and widget_key != "scenario_reset"
            ):
                st.session_state.pop(widget_key, None)
        st.rerun()

    study_id = st.selectbox(
        "Study selection",
        options=[*study_by_id, "both"],
        format_func=lambda item: (
            "English et al. (2015) + Fitts et al. (2010) (separate panels)"
            if item == "both"
            else
            f'{study_by_id[item]["authors"].split(",")[0]} '
            f'({study_by_id[item]["year"]}) — {study_by_id[item]["title"]}'
        ),
        key="scenario_study",
    )
    analysis_view = st.selectbox(
        "Analysis view",
        options=("observed", "recovery"),
        format_func=lambda item: (
            "Observed-data comparison"
            if item == "observed"
            else "Postflight recovery (English et al. only)"
        ),
        key="scenario_analysis_view",
        help=(
            "Recovery is shown only for verified English et al. observations. "
            "It uses days after return, never mission duration."
        ),
    )
    if study_id == "both":
        mission_duration_days = _mission_duration_slider()
        st.caption(
            "The shared hypothetical duration is context only. Published group "
            "results are unchanged, and no duration-based estimate is available."
        )
        english_panel, fitts_panel = st.columns(2)
        with english_panel:
            _show_combined_panel(
                connection,
                study_by_id,
                "english-2015",
                mission_duration_days,
                analysis_view,
            )
        with fitts_panel:
            _show_combined_panel(
                connection,
                study_by_id,
                "fitts-2010",
                mission_duration_days,
                analysis_view,
            )
        return

    if study_id not in engine_study_ids:
        _show_context_only_study(study_by_id[study_id])
        return

    region_options = allowed_regions(study_id)
    if st.session_state.get("scenario_region") not in region_options:
        st.session_state.pop("scenario_region", None)
    region = st.selectbox(
        "Muscle or joint region",
        options=region_options,
        key="scenario_region",
    )
    outcome_options = allowed_outcomes(study_id, region)
    if st.session_state.get("scenario_outcome") not in outcome_options:
        st.session_state.pop("scenario_outcome", None)
    outcome_id = st.selectbox(
        "Measured outcome",
        options=list(outcome_options),
        format_func=lambda item: outcome_options[item],
        key="scenario_outcome",
    )
    group_options = allowed_comparison_groups(study_id)
    if st.session_state.get("scenario_group") not in group_options:
        st.session_state.pop("scenario_group", None)
    comparison_group = st.selectbox(
        "Comparison group",
        options=list(group_options),
        format_func=lambda item: group_options[item],
        key="scenario_group",
        help=(
            "English et al.: overall cohort, sex, or exercise-device era. "
            "Fitts et al.: fibre type."
        ),
    )
    timepoint_options = allowed_timepoints(
        study_id, region, comparison_group
    )
    if st.session_state.get("scenario_timepoint") not in timepoint_options:
        st.session_state.pop("scenario_timepoint", None)
    timepoint_labels = {
        "R+5": "R+5 — early postflight",
        "R+14": "R+14 — postflight recovery",
        "R+30": "R+30 — postflight recovery",
        "preflight_to_landing": (
            "L-55 ± 2 days preflight to R+0 landing day"
        ),
    }
    timepoint = st.selectbox(
        "Measurement timepoint",
        options=timepoint_options,
        format_func=lambda item: timepoint_labels[item],
        key="scenario_timepoint",
    )
    mission_duration_days = _mission_duration_slider()

    inputs = ScenarioInputs(
        study_id=study_id,
        region=region,
        outcome_id=outcome_id,
        comparison_group=comparison_group,
        timepoint=timepoint,
        mission_duration_days=mission_duration_days,
    )
    try:
        result = analyze_scenario(
            connection,
            inputs,
        )
    except ValueError as error:
        st.error(f"Scenario cannot be analyzed: {error}")
        return

    st.markdown("---")
    st.subheader("Scenario result")
    st.markdown(f"**Analysis mode: {result.analysis_mode}**")
    st.caption(
        f"Selected study: {result.study_title} · "
        f"Outcome: {result.outcome} · Unit: {result.unit}"
    )
    st.caption(f"Population: {result.population}")

    if result.mean_change is None:
        st.info(result.interpretation)
    elif result.study_id == "english-2015":
        value_column, ci_column, sample_column = st.columns(3)
        value_column.metric("Reported mean change", f"{result.mean_change:+.1f}%")
        if result.confidence_interval is not None:
            ci_column.metric(
                "Reported 95% CI",
                (
                    f"{result.confidence_interval[0]:+.1f}% to "
                    f"{result.confidence_interval[1]:+.1f}%"
                ),
            )
        else:
            ci_column.metric("Reported 95% CI", "Not available")
        sample_column.metric(
            "Sample size for this row",
            str(result.sample_size) if result.sample_size is not None else "Not reported",
        )
        st.write(result.interpretation)
    else:
        values_column, change_column, percent_column = st.columns(3)
        values_column.metric(
            "Published group means",
            f"{result.preflight_value:g} → {result.postflight_value:g} {result.unit.split()[0]}",
        )
        change_column.metric(
            "Post-minus-pre difference",
            f"{result.absolute_change:+g} {result.unit.split()[0]}",
        )
        percent_column.metric("Derived percent change", f"{result.mean_change:+.1f}%")
        st.write(result.interpretation)
        if (
            result.preflight_standard_error is not None
            and result.postflight_standard_error is not None
        ):
            st.caption(
                f"Reported mean ± SEM: preflight "
                f"{result.preflight_value:g} ± "
                f"{result.preflight_standard_error:g} {result.unit} "
                f"(n={result.preflight_sample_size} fibres); postflight "
                f"{result.postflight_value:g} ± "
                f"{result.postflight_standard_error:g} {result.unit} "
                f"(n={result.postflight_sample_size} fibres). "
                "The asterisk in the source marks a significant difference "
                "from preflight (P < 0.05); fibre counts are not crew counts."
            )

    for warning in result.warnings:
        st.warning(warning)

    _show_scenario_plot(
        connection,
        inputs,
        result,
        study_by_id,
        analysis_view,
    )

    with st.expander("Evidence, provenance, and timepoints", expanded=True):
        st.write(f"**Study:** {result.study_title}")
        st.write(f"**Population:** {result.population}")
        st.write(f"**Selected group:** {result.comparison_group}")
        st.write(f"**Measurement timepoint:** {timepoint_labels[result.timepoint]}")
        st.write(
            f"**Mission duration context:** {result.mission_duration_days} days"
        )
        if result.source_page is not None:
            st.write(
                f"**Source:** data/references/"
                f'{study_by_id[result.study_id]["source_file"]}, '
                f"PDF page {result.source_page}, {result.source_location}"
            )
            st.write(f"**Source cell transcription/context:** {result.source_wording}")
            st.write("**Verification status:** source-verified")
        else:
            st.write(
                "**Source:** the selected study's described measures and "
                "timepoints; no matching verified numerical record."
            )
        if result.study_id == "english-2015":
            st.write(
                "English et al. compare the L-60 preflight baseline with "
                "postflight testing. R+14 and R+30 are recovery timepoints, "
                "not additional days in flight."
            )
        else:
            st.write(
                "Fitts et al. compare preflight muscle-biopsy measures at "
                "L-55 ± 2 days with samples taken on landing day (R+0), "
                "approximately 6–8 hours after landing."
            )


def _mission_duration_slider() -> int:
    mission_duration_days = st.slider(
        "Mission duration (days; context only)",
        min_value=MISSION_DURATION_MIN_DAYS,
        max_value=MISSION_DURATION_MAX_DAYS,
        value=MISSION_DURATION_DEFAULT_DAYS,
        step=1,
        key="scenario_duration",
        help=(
            "Context only. The papers do not support multiplying an observed "
            "postflight change by mission duration."
        ),
    )
    st.caption(
        "Duration slider: 90–240 days, rounded from the English cohort's "
        "approximately 2-SD duration span (163 ± 2×38 days); default 177 days "
        "is the Fitts cohort mean. Duration is never used to generate a curve."
    )
    return mission_duration_days


def _show_context_only_study(study: dict[str, object]) -> None:
    st.markdown("---")
    st.subheader("Evidence and model eligibility")
    st.caption(
        f'Source availability: {study["source_availability"]} · '
        f'Extraction: {study["extraction_status"]} · '
        "Quantitative status: "
        f'{study["quantitative_verification_status"]}'
    )
    st.info(
        "This study is available for evidence review, but it has no compatible "
        "quantitative observations curated for a prediction or calculation. "
        "No numerical model output is generated from this selection."
    )
    st.write(f'**Population:** {study["population"]}')
    st.write(f'**Outcomes:** {study["outcomes"]}')
    st.write(f'**Reported findings:** {study["findings"]}')
    st.write(f'**Limitations:** {study["limitations"]}')
    st.caption(
        f'Source file: data/references/{study["source_file"]}. '
        "Source availability does not imply that quantitative results have "
        "been validated for engine use."
    )


def _show_combined_panel(
    connection: sqlite3.Connection,
    study_by_id: dict[str, dict[str, object]],
    study_id: str,
    mission_duration_days: int,
    analysis_view: str,
) -> None:
    study = study_by_id[study_id]
    st.subheader(
        f'{study["authors"].split(",")[0]} ({study["year"]})'
    )
    prefix = f"scenario_{study_id}"
    regions = allowed_regions(study_id)
    if st.session_state.get(f"{prefix}_region") not in regions:
        st.session_state.pop(f"{prefix}_region", None)
    region = st.selectbox(
        "Muscle or joint region",
        options=regions,
        key=f"{prefix}_region",
    )
    outcomes = allowed_outcomes(study_id, region)
    if st.session_state.get(f"{prefix}_outcome") not in outcomes:
        st.session_state.pop(f"{prefix}_outcome", None)
    outcome_id = st.selectbox(
        "Measured outcome",
        options=list(outcomes),
        format_func=lambda item: outcomes[item],
        key=f"{prefix}_outcome",
    )
    groups = allowed_comparison_groups(study_id)
    if st.session_state.get(f"{prefix}_group") not in groups:
        st.session_state.pop(f"{prefix}_group", None)
    comparison_group = st.selectbox(
        "Comparison group",
        options=list(groups),
        format_func=lambda item: groups[item],
        key=f"{prefix}_group",
    )
    timepoints = allowed_timepoints(study_id, region, comparison_group)
    if st.session_state.get(f"{prefix}_timepoint") not in timepoints:
        st.session_state.pop(f"{prefix}_timepoint", None)
    timepoint_labels = {
        "R+5": "R+5 — early postflight",
        "R+14": "R+14 — postflight recovery",
        "R+30": "R+30 — postflight recovery",
        "preflight_to_landing": (
            "L-55 ± 2 days preflight to R+0 landing day"
        ),
    }
    timepoint = st.selectbox(
        "Measurement timepoint",
        options=timepoints,
        format_func=lambda item: timepoint_labels[item],
        key=f"{prefix}_timepoint",
    )
    inputs = ScenarioInputs(
        study_id=study_id,
        region=region,
        outcome_id=outcome_id,
        comparison_group=comparison_group,
        timepoint=timepoint,
        mission_duration_days=mission_duration_days,
    )
    try:
        result = analyze_scenario(connection, inputs)
    except ValueError as error:
        st.error(f"Scenario cannot be analyzed: {error}")
        return

    st.markdown(f"**Analysis mode: {result.analysis_mode}**")
    st.caption(f"{result.outcome} · {result.unit}")
    if result.mean_change is None:
        st.info(result.interpretation)
    elif study_id == "english-2015":
        st.metric("Reported mean change", f"{result.mean_change:+.1f}%")
        if result.confidence_interval is not None:
            st.caption(
                "Reported 95% CI: "
                f"{result.confidence_interval[0]:+.1f}% to "
                f"{result.confidence_interval[1]:+.1f}% · "
                f"n={result.sample_size}"
            )
        st.write(result.interpretation)
    else:
        unit = result.unit.split()[0]
        st.metric(
            "Published group means",
            f"{result.preflight_value:g} → {result.postflight_value:g} {unit}",
        )
        st.metric("Derived percent change", f"{result.mean_change:+.1f}%")
        st.write(result.interpretation)
        if (
            result.preflight_standard_error is not None
            and result.postflight_standard_error is not None
        ):
            st.caption(
                f"SEM and fibre counts: preflight "
                f"{result.preflight_standard_error:g} "
                f"(n={result.preflight_sample_size}); landing day "
                f"{result.postflight_standard_error:g} "
                f"(n={result.postflight_sample_size}). Fibre counts are not "
                "crew counts; no uncertainty for the derived change is shown."
            )

    _show_scenario_plot(
        connection,
        inputs,
        result,
        study_by_id,
        analysis_view,
    )
    for warning in result.warnings:
        st.warning(warning)
    st.caption(
        f"Mission duration context: {mission_duration_days} days. "
        "It does not change the recorded study result."
    )
    with st.expander("Source and limitations"):
        st.write(f"**Population:** {result.population}")
        st.write(
            f"**Timepoint:** {timepoint_labels[result.timepoint]} · "
            f"**Source:** PDF page {result.source_page or 'not reported'}, "
            f"{result.source_location or 'location not reported'}"
        )
        st.write(result.source_wording or result.interpretation)
        st.write(
            "The two panels use different biological measurement levels and "
            "are not pooled or directly compared."
        )


def _show_scenario_plot(
    connection: sqlite3.Connection,
    inputs: ScenarioInputs,
    result: ScenarioResult,
    study_by_id: dict[str, dict[str, object]],
    analysis_view: str,
) -> None:
    if result.mean_change is None:
        return
    if result.study_id == "english-2015":
        record_key = (
            f"english::{inputs.region.lower()}::{inputs.outcome_id}::"
            f"{inputs.comparison_group}"
        )
        if analysis_view == "recovery":
            observations = verified_english_recovery_observations(
                connection,
                record_key,
            )
            figure = create_recovery_plot(
                observations,
                f"{result.outcome}: observed postflight recovery",
            )
            if figure is None:
                st.info(
                    "A recovery plot needs at least two matching, verified "
                    "postflight timepoints. This selection has fewer."
                )
            else:
                st.plotly_chart(figure, width="stretch")
                st.caption(
                    "Each point is a reported group mean; error bars are the "
                    "published 95% CIs. This is days after return, not an "
                    "in-flight or mission-duration trajectory."
                )
        else:
            figure = create_relative_change_plot(
                result.mean_change,
                "% mean change from L-60",
                f"Observed {inputs.timepoint} group mean",
                confidence_interval=result.confidence_interval,
            )
            st.plotly_chart(figure, width="stretch")
    else:
        if analysis_view == "recovery":
            st.info(
                "Fitts et al. measured preflight and landing-day biopsies, not "
                "multiple postflight recovery timepoints. Showing its observed "
                "preflight-to-landing comparison instead."
            )
        figure = create_fibre_comparison_plot(
            result.preflight_value,
            result.postflight_value,
            result.unit,
            f"{result.region} {result.outcome}: published group means",
        )
        st.plotly_chart(figure, width="stretch")


show_scenario_explorer = show_refined_scenario_explorer


def show_study_library(connection: sqlite3.Connection) -> None:
    studies = list_studies(connection)
    study_by_id = {str(study["id"]): study for study in studies}
    selected_id = st.selectbox(
        "Select a study",
        options=list(study_by_id),
        format_func=lambda study_id: (
            f'{study_by_id[study_id]["authors"].split(",")[0]} '
            f'({study_by_id[study_id]["year"]}) — '
            f'{study_by_id[study_id]["title"]}'
        ),
    )
    study = get_study(connection, selected_id)
    if study is None:
        st.error("The selected study could not be found in the library.")
        return

    st.subheader(str(study["title"]))
    st.caption(
        f'{study["authors"]} ({study["year"]}). {study["journal"]}. '
        f'DOI: {study["doi"]}'
    )
    st.caption(
        f'Source file: data/references/{study["source_file"]} · '
        f'Availability: {study["source_availability"]}'
    )
    st.caption(
        f'Extraction status: {study["extraction_status"]} · '
        "Quantitative verification status: "
        f'{study["quantitative_verification_status"]}'
    )

    sections = (
        ("Research question", "research_question"),
        ("Population and sample", "population"),
        ("Sample-size notes", "sample_size_note"),
        ("Study design", "study_design"),
        ("Measurement methods", "measurement_methods"),
        ("Outcomes", "outcomes"),
        ("Timepoints", "timepoints"),
        ("Main findings", "findings"),
        ("Limitations", "limitations"),
    )
    for heading, field in sections:
        st.markdown(f"**{heading}**")
        st.write(study[field])


def show_measurements(connection: sqlite3.Connection) -> None:
    studies = list_studies(connection)
    study_by_id = {str(study["id"]): study for study in studies}
    study_id = st.selectbox(
        "Study for measurement records",
        options=list(study_by_id),
        format_func=lambda selected_id: (
            f'{study_by_id[selected_id]["authors"].split(",")[0]} '
            f'({study_by_id[selected_id]["year"]}) — '
            f'{study_by_id[selected_id]["title"]}'
        ),
        key="measurement_study",
    )
    selected_study = study_by_id[study_id]
    st.caption(
        f'Source availability: {selected_study["source_availability"]} · '
        "Quantitative status: "
        f'{selected_study["quantitative_verification_status"]}. '
        "Source-verified records are not automatically eligible for model use."
    )
    measurements = list_measurements(connection, study_id)
    if not measurements:
        st.info(
            "No measurement records are currently available for this study. "
            "The Scenario Explorer uses only explicitly curated, source-verified "
            "values; arbitrary PDF-extracted values are not used."
        )
    else:
        for measurement in measurements:
            value_status = str(measurement["value_status"])
            sample_status = str(measurement["sample_size_status"])
            with st.expander(
                f'{measurement["measurement_name"]} · '
                f'{measurement["verification_status"]}'
            ):
                st.write(
                    f'**Muscle/outcome:** {measurement["muscle_or_outcome"]}'
                )
                st.write(
                    f'**Value:** {measurement["value"] or value_status}'
                    f' {measurement["unit"] or ""}'
                )
                st.write(f'**Timepoint:** {measurement["timepoint"] or "Unreported"}')
                st.write(
                    "**Comparison baseline:** "
                    f'{measurement["comparison_baseline"] or "Unreported"}'
                )
                sample_size = (
                    str(measurement["sample_size"])
                    if measurement["sample_size"] is not None
                    else sample_status
                )
                st.write(f"**Sample size:** {sample_size}")
                st.write(
                    f'**Source:** data/references/{selected_study["source_file"]}, '
                    f'PDF page {measurement["source_page"] or "unreported"}'
                    f' · {measurement["source_location"] or "location unreported"}'
                )
                st.write(
                    f'**Source wording/context:** '
                    f'{measurement["source_wording"] or "Unreported"}'
                )
                st.write(
                    f'**Uncertainty/extraction notes:** '
                    f'{measurement["uncertainty_notes"] or "None recorded"}'
                )

    with st.expander("Add an unverified measurement record"):
        st.caption(
            "Enter values only after manually checking the source PDF. New "
            "records remain unverified until their page and wording are reviewed."
        )
        with st.form("add_measurement"):
            muscle_or_outcome = st.text_input("Muscle, muscle group, or outcome")
            measurement_name = st.text_input("Measurement name")
            value_status = st.selectbox(
                "Value status",
                options=["unreported", "reported", "unknown"],
                help="Use unreported if the source does not state a value.",
            )
            value = st.text_input("Value (as printed; do not normalize formatting)")
            unit = st.text_input("Unit")
            timepoint = st.text_input("Timepoint")
            comparison_baseline = st.text_input("Comparison baseline")
            sample_size_status = st.selectbox(
                "Sample-size status",
                options=["unreported", "reported", "unknown"],
            )
            sample_size_value = st.number_input(
                "Sample size (when reported)", min_value=1, step=1, value=1
            )
            source_page = st.text_input("Source PDF page")
            source_location = st.text_input("Table or figure")
            source_wording = st.text_area("Exact source wording or relevant context")
            uncertainty_notes = st.text_area("Uncertainty or extraction notes")
            submitted = st.form_submit_button("Save as unverified")
        if submitted:
            try:
                add_measurement(
                    connection,
                    MeasurementInput(
                        study_id=study_id,
                        muscle_or_outcome=muscle_or_outcome,
                        measurement_name=measurement_name,
                        value=value if value_status == "reported" else None,
                        value_status=value_status,
                        unit=unit or None,
                        timepoint=timepoint or None,
                        comparison_baseline=comparison_baseline or None,
                        sample_size=(
                            int(sample_size_value)
                            if sample_size_status == "reported"
                            else None
                        ),
                        sample_size_status=sample_size_status,
                        source_page=source_page or None,
                        source_location=source_location or None,
                        source_wording=source_wording or None,
                        uncertainty_notes=uncertainty_notes or None,
                    ),
                )
            except (ValueError, sqlite3.Error) as error:
                st.error(f"Could not save measurement: {error}")
            else:
                st.success("Measurement saved with unverified status.")
                st.rerun()

    unverified = [
        measurement
        for measurement in measurements
        if measurement["verification_status"] == "unverified"
    ]
    if unverified:
        with st.expander("Mark a measurement as source-verified"):
            st.caption(
                "Confirm the exact value and its context against the rendered "
                "PDF. A PDF page and exact source wording are required."
            )
            measurement_by_id = {
                int(measurement["id"]): measurement for measurement in unverified
            }
            with st.form("verify_measurement"):
                measurement_id = st.selectbox(
                    "Unverified measurement",
                    options=list(measurement_by_id),
                    format_func=lambda item_id: (
                        f'{measurement_by_id[item_id]["measurement_name"]} '
                        f'({measurement_by_id[item_id]["muscle_or_outcome"]})'
                    ),
                )
                verified_page = st.text_input("Verified source PDF page")
                verified_location = st.text_input("Verified table or figure")
                verified_wording = st.text_area(
                    "Exact source wording confirming this record"
                )
                verification_notes = st.text_area(
                    "Notes about remaining uncertainty"
                )
                verify_submitted = st.form_submit_button("Mark source-verified")
            if verify_submitted:
                try:
                    mark_measurement_source_verified(
                        connection,
                        measurement_id,
                        source_page=verified_page,
                        source_location=verified_location or None,
                        source_wording=verified_wording,
                        uncertainty_notes=verification_notes or None,
                    )
                except (ValueError, sqlite3.Error) as error:
                    st.error(f"Could not verify measurement: {error}")
                else:
                    st.success("Measurement marked source-verified.")
                    st.rerun()


def main() -> None:
    st.set_page_config(page_title="Atrophy Armour", layout="wide")
    st.title("Atrophy Armour")
    st.caption("Evidence-based scenario exploration · Study Library")
    st.info(
        "Scenario results are descriptive comparisons of source-verified "
        "observations, not estimates of in-flight muscle loss or mission outcomes."
    )

    connection = initialize_database()
    try:
        seed_reference_measurements(connection)
        seed_abstract_context_measurements(connection)
        scenario_tab, library_tab, measurement_tab = st.tabs(
            ["Scenario Explorer", "Study Library", "Measurements"]
        )
        with scenario_tab:
            show_scenario_explorer(connection)
        with library_tab:
            show_study_library(connection)
        with measurement_tab:
            show_measurements(connection)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
