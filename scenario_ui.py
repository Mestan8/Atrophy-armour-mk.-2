"""Scenario Explorer presentation and point-specific source dialogs."""

import sqlite3

import plotly.graph_objects as go
import streamlit as st

from interactive_evidence import (
    build_observation_details,
    observation_identifier,
    selected_observation_id,
)
from model import ScenarioResult, analyze_scenario
from plotting import (
    create_fibre_comparison_plot,
    create_recovery_plot,
    create_relative_change_plot,
)
from scenario_evidence import (
    find_verified_observation,
    verified_english_recovery_observations,
)
from scenario_inputs import (
    MISSION_DURATION_DEFAULT_DAYS,
    ScenarioInputs,
    allowed_comparison_groups,
    allowed_scenario_outcomes,
    allowed_timepoints,
)
from study_library import list_studies


_TIMEPOINT_LABELS = {
    "R+5": "R+5 — early postflight",
    "R+14": "R+14 — postflight",
    "R+30": "R+30 — postflight",
    "preflight_to_landing": "L-55 ± 2 days preflight to R+0 landing day",
}


@st.dialog("Selected observation", width="large", dismissible=False)
def _show_observation_dialog(details: dict[str, object]) -> None:
    st.markdown(f"### {details['outcome']}")
    st.markdown("**Observation**")
    st.write(f"**Anatomical target:** {details['anatomical_target']}")
    st.write(f"**Observed value:** {details['value']} {details['unit']}")
    st.write(
        f"**Timepoint/comparison:** {details['timepoint']} · "
        f"{details['comparison']}"
    )
    st.write(f"**Value type:** {details['value_status']}")
    st.write(f"**Statistic:** {details['statistic']}")

    st.markdown("**Scientific meaning**")
    st.write(details["scientific_meaning"])

    st.markdown("**Source and provenance**")
    st.write(f"**Study:** {details['authors_year']}")
    st.write(f"**Title:** {details['study_title']}")
    if details["doi"]:
        st.write(f'**DOI:** https://doi.org/{details["doi"]}')
    if details["source_pdf"]:
        st.write(f'**Source PDF:** data/references/{details["source_pdf"]}')
    if details["source_page"]:
        st.write(f'**PDF page:** {details["source_page"]}')
    if details["source_location"]:
        st.write(f'**Table/figure/location:** {details["source_location"]}')
    if details["sample_size"] is not None:
        st.write(f'**Sample size:** {details["sample_size"]}')
        st.write(details["sample_definition"])
    if details["source_wording"]:
        st.write(f'**Source wording:** {details["source_wording"]}')

    st.markdown("**Limitations and uncertainty**")
    if details["uncertainty"]:
        st.write(f'**Uncertainty:** {details["uncertainty"]}')
    st.write(details["limitations"])
    if st.button("Close details", key="scenario_close_observation"):
        st.session_state["scenario_chart_revision"] = (
            st.session_state.get("scenario_chart_revision", 0) + 1
        )
        st.session_state.pop("scenario_selected_observation", None)
        st.session_state.pop("scenario_dismissed_observation", None)
        st.rerun()


def show_scenario_explorer(connection: sqlite3.Connection) -> None:
    studies = {
        str(study["id"]): study for study in list_studies(connection)
    }
    supported_study_ids = [
        study_id
        for study_id in ("english-2015", "fitts-2010")
        if study_id in studies
    ]

    st.subheader("Scenario Explorer")
    st.caption(
        "The Study Library contains all eight sources. This explorer offers "
        "only outcomes with complete, curated numerical evidence."
    )
    if not supported_study_ids:
        st.error("No supported study is available in the Study Library.")
        return
    if st.button("Reset scenario to defaults", key="scenario_reset"):
        for widget_key in tuple(st.session_state):
            if widget_key.startswith("scenario_") and widget_key not in {
                "scenario_reset",
                "scenario_chart_revision",
            }:
                st.session_state.pop(widget_key, None)
        st.rerun()

    if st.session_state.get("scenario_study") not in supported_study_ids:
        st.session_state.pop("scenario_study", None)
    study_id = st.selectbox(
        "1. Select a supported study",
        options=supported_study_ids,
        format_func=lambda item: (
            f'{studies[item]["authors"].split(",")[0]} '
            f'({studies[item]["year"]})'
        ),
        key="scenario_study",
    )
    outcome_options = allowed_scenario_outcomes(study_id)
    if st.session_state.get("scenario_outcome") not in outcome_options:
        st.session_state.pop("scenario_outcome", None)
    outcome_id = st.selectbox(
        "2. Select an available outcome",
        options=list(outcome_options),
        format_func=lambda item: (
            f"{outcome_options[item][0]} — {outcome_options[item][1]}"
        ),
        key="scenario_outcome",
    )
    region, outcome_label = outcome_options[outcome_id]

    group_options = allowed_comparison_groups(study_id, region, outcome_id)
    if st.session_state.get("scenario_group") not in group_options:
        st.session_state.pop("scenario_group", None)
    comparison_group = st.selectbox(
        "3. Select the comparison",
        options=list(group_options),
        format_func=lambda item: group_options[item],
        key="scenario_group",
    )
    timepoint_options = allowed_timepoints(
        study_id, region, comparison_group, outcome_id
    )
    if st.session_state.get("scenario_timepoint") not in timepoint_options:
        st.session_state.pop("scenario_timepoint", None)
    timepoint = st.selectbox(
        "4. Select the timepoint",
        options=timepoint_options,
        format_func=lambda item: _TIMEPOINT_LABELS[item],
        key="scenario_timepoint",
    )

    record_key = (
        f"english::{region.lower()}::{outcome_id}::{comparison_group}"
        if study_id == "english-2015"
        else f"fitts::{region.lower()}::{outcome_id}::{comparison_group}"
    )
    recovery_observations: list[dict[str, object]] = []
    analysis_view = "observed"
    if study_id == "english-2015":
        recovery_observations = verified_english_recovery_observations(
            connection,
            record_key,
        )
        analysis_options = ["observed"]
        if len(recovery_observations) >= 2:
            analysis_options.append("recovery")
        if st.session_state.get("scenario_analysis_view") not in analysis_options:
            st.session_state.pop("scenario_analysis_view", None)
        analysis_view = st.selectbox(
            "5. Display",
            options=analysis_options,
            format_func=lambda item: (
                "Selected observation"
                if item == "observed"
                else "Postflight recovery series"
            ),
            key="scenario_analysis_view",
        )
    elif st.session_state.get("scenario_analysis_view") != "observed":
        st.session_state["scenario_analysis_view"] = "observed"

    st.caption("Results update automatically when a selection changes.")
    inputs = ScenarioInputs(
        study_id=study_id,
        region=region,
        outcome_id=outcome_id,
        comparison_group=comparison_group,
        timepoint=timepoint,
        mission_duration_days=MISSION_DURATION_DEFAULT_DAYS,
    )
    try:
        result = analyze_scenario(connection, inputs)
    except ValueError as error:
        st.error(f"Scenario cannot be analyzed: {error}")
        return

    st.markdown("---")
    st.subheader("Result")
    st.caption(f"{result.outcome} · {result.unit} · {result.population}")
    if result.mean_change is None:
        st.info(result.interpretation)
    elif study_id == "english-2015":
        metric_column, ci_column, sample_column = st.columns(3)
        metric_column.metric("Reported mean change", f"{result.mean_change:+.1f}%")
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
            "Table sample size",
            str(result.sample_size) if result.sample_size is not None else "Not reported",
        )
        st.write(result.interpretation)
    else:
        values_column, change_column, percent_column = st.columns(3)
        unit = result.unit.split()[0]
        values_column.metric(
            "Published fibre group means",
            f"{result.preflight_value:g} → {result.postflight_value:g} {unit}",
        )
        change_column.metric(
            "Derived post-minus-pre difference",
            f"{result.absolute_change:+g} {unit}",
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
                f"(n={result.postflight_sample_size} fibres). Fibre counts "
                "are not astronaut counts; uncertainty for the derived "
                "change is not available."
            )

    for warning in result.warnings:
        st.warning(warning)

    _show_scenario_plot(
        connection,
        inputs,
        result,
        studies,
        analysis_view,
        recovery_observations,
    )
    with st.expander("Evidence and method"):
        st.write(f"**Study:** {result.study_title}")
        st.write(f"**Outcome:** {outcome_label}")
        st.write(f"**Comparison:** {result.comparison_group}")
        st.write(f"**Timepoint:** {_TIMEPOINT_LABELS[result.timepoint]}")
        if result.source_page is not None:
            st.write(
                f'**Source:** data/references/{studies[result.study_id]["source_file"]}, '
                f"PDF page {result.source_page}, {result.source_location}"
            )
            st.write(f"**Source wording:** {result.source_wording}")
            st.write("**Verification:** source-verified")
        st.write(result.interpretation)


def _show_scenario_plot(
    connection: sqlite3.Connection,
    inputs: ScenarioInputs,
    result: ScenarioResult,
    studies: dict[str, dict[str, object]],
    analysis_view: str,
    recovery_observations: list[dict[str, object]],
) -> None:
    if result.mean_change is None:
        return
    details_by_id: dict[str, dict[str, object]] = {}
    if result.study_id == "english-2015":
        record_key = (
            f"english::{inputs.region.lower()}::{inputs.outcome_id}::"
            f"{inputs.comparison_group}"
        )
        if analysis_view == "recovery":
            details_by_id = _details_for_recovery_points(
                studies[result.study_id],
                recovery_observations,
                result.region,
                result.outcome,
                result.comparison_group,
                result.unit,
            )
            figure = create_recovery_plot(
                recovery_observations,
                f"{result.outcome}: observed postflight recovery",
            )
            if figure is None:
                st.info("No verified multi-timepoint recovery series is available.")
                return
            st.caption(
                "Select a point for its source details. Points show reported "
                "group means and 95% CIs in days after return."
            )
        else:
            record = find_verified_observation(
                connection,
                result.study_id,
                record_key,
                "Mean percent change from L-60",
                inputs.timepoint,
            )
            if record is None:
                st.info("No matching source-verified point is available to plot.")
                return
            details = build_observation_details(
                studies[result.study_id],
                record,
                region=result.region,
                outcome=result.outcome,
                comparison=result.comparison_group,
                unit=result.unit,
            )
            identifier = observation_identifier(record)
            details_by_id[identifier] = details
            figure = create_relative_change_plot(
                result.mean_change,
                result.unit,
                f"Observed {inputs.timepoint} group mean",
                confidence_interval=result.confidence_interval,
                observation_id=identifier,
            )
            st.caption("Select the point to inspect its observation and source.")
    else:
        record_key = (
            f"fitts::{inputs.region.lower()}::{inputs.outcome_id}::"
            f"{inputs.comparison_group}"
        )
        preflight = find_verified_observation(
            connection,
            result.study_id,
            record_key,
            "Preflight value",
            "L-55 ± 2 days",
        )
        postflight = find_verified_observation(
            connection,
            result.study_id,
            record_key,
            "Postflight value",
            "R+0, landing day",
        )
        if preflight is None or postflight is None:
            st.info("A complete pair of source-verified points is not available.")
            return
        group_label = allowed_comparison_groups(
            result.study_id, result.region, inputs.outcome_id
        )[inputs.comparison_group]
        for record in (preflight, postflight):
            details = build_observation_details(
                studies[result.study_id],
                record,
                region=result.region,
                outcome=result.outcome,
                comparison=group_label,
                unit=result.unit,
            )
            details_by_id[observation_identifier(record)] = details
        figure = create_fibre_comparison_plot(
            float(preflight["value"]),
            float(postflight["value"]),
            result.unit,
            f"{result.region} fibre {result.outcome}: published group means",
            observation_ids=(
                observation_identifier(preflight),
                observation_identifier(postflight),
            ),
        )
        st.caption("Select either bar for that timepoint's fibre-level source record.")

    context = (
        f"{inputs.study_id}_{inputs.region}_{inputs.outcome_id}_"
        f"{inputs.comparison_group}_{inputs.timepoint}_{analysis_view}"
    )
    _show_selectable_plot(figure, details_by_id, context)


def _details_for_recovery_points(
    study: dict[str, object],
    observations: list[dict[str, object]],
    region: str,
    outcome: str,
    comparison: str,
    unit: str,
) -> dict[str, dict[str, object]]:
    details_by_id = {}
    for observation in observations:
        record = dict(observation)
        record["value"] = observation["mean_change"]
        record["unit"] = unit
        details = build_observation_details(
            study,
            record,
            region=region,
            outcome=outcome,
            comparison=comparison,
            unit=unit,
        )
        details_by_id[str(details["observation_id"])] = details
    return details_by_id


def _show_selectable_plot(
    figure: go.Figure,
    details_by_id: dict[str, dict[str, object]],
    context: str,
) -> None:
    if st.session_state.get("scenario_selection_context") != context:
        st.session_state["scenario_selection_context"] = context
        st.session_state.pop("scenario_selected_observation", None)
        st.session_state.pop("scenario_dismissed_observation", None)
        st.session_state["scenario_chart_revision"] = (
            st.session_state.get("scenario_chart_revision", 0) + 1
        )
    chart_revision = st.session_state.get("scenario_chart_revision", 0)
    chart_state = st.plotly_chart(
        figure,
        width="stretch",
        key=f"scenario_chart_{context}_{chart_revision}",
        on_select="rerun",
        selection_mode="points",
    )
    identifier = selected_observation_id(chart_state.selection)
    if identifier is None:
        st.session_state.pop("scenario_selected_observation", None)
        st.session_state.pop("scenario_dismissed_observation", None)
        return
    details = details_by_id.get(identifier)
    if details is None:
        st.session_state.pop("scenario_selected_observation", None)
        return
    if identifier != st.session_state.get("scenario_dismissed_observation"):
        st.session_state["scenario_selected_observation"] = identifier
        _show_observation_dialog(details)
