"""SQLite storage and seeded source summaries for the Study Library."""

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from database import connect_database


DEFAULT_DATABASE_PATH = (
    Path(__file__).resolve().parent / "data" / "study_library.sqlite3"
)

STUDIES = (
    {
        "id": "english-2015",
        "authors": "Kirk L. English, Stuart M. C. Lee, James A. Loehr, "
        "Robert J. Ploutz-Snyder, Lori L. Ploutz-Snyder",
        "year": 2015,
        "title": "Isokinetic Strength Changes Following Long-Duration Spaceflight on the ISS",
        "journal": "Aerospace Medicine and Human Performance, 86(12, Suppl.), A68-A77",
        "doi": "10.3357/AMHP.EC09.2015",
        "source_file": "amhp-article-pA68.pdf",
        "research_question": (
            "How did isokinetic strength and endurance change after long-duration "
            "ISS missions, and were changes associated with sex, in-flight "
            "resistance-exercise hardware, or preflight strength?"
        ),
        "population": (
            "ISS crewmembers from Expeditions 1-25. The analyzed cohort included "
            "29 men and 8 women; three crew members contributed data from two "
            "flights, analyzed as independent datasets."
        ),
        "sample_size": 37,
        "sample_size_note": (
            "Thirty-nine crew members were eligible; one declined and one was "
            "excluded for inconsistent tests. Three of the 37 contributed two "
            "flight datasets."
        ),
        "study_design": (
            "Retrospective evaluation of standardized operational preflight and "
            "postflight testing; not a randomized countermeasure trial."
        ),
        "measurement_methods": (
            "Isokinetic dynamometry of knee, ankle, and trunk movements. "
            "Concentric testing predominated; a single ankle eccentric test was "
            "included. Outcomes included peak torque and, for 180-degree knee "
            "tests, total work."
        ),
        "outcomes": (
            "Movement-specific isokinetic strength and endurance, including "
            "peak torque and selected total-work measures."
        ),
        "timepoints": (
            "Tests scheduled at L-180 and L-60 before launch and R+5, R+14, and "
            "R+30 after return. L-180 was treated as familiarization; changes "
            "were referenced to L-60. Trunk tests were first performed after "
            "flight at R+14."
        ),
        "findings": (
            "Strength decreased after flight across the tested lower-body and "
            "trunk movements, then improved during the first month after return "
            "with some residual deficits. The paper reports no statistically "
            "significant sex difference. ARED-era results suggested, but did "
            "not establish, better preservation than iRED. Higher preflight "
            "strength was moderately associated with larger postflight changes."
        ),
        "limitations": (
            "In-flight exercise was not prescribed in a mandatory standardized "
            "way, limiting comparisons of iRED and ARED. Testing time and scope "
            "were limited; upper-body strength was not tested, most tests were "
            "concentric, and the study did not measure strength changes during "
            "flight. ARED loading was not routinely measured, and the authors "
            "note that astronaut task-performance thresholds were not established."
        ),
        "source_availability": "full_text",
        "extraction_status": "full_text_reviewed",
        "quantitative_verification_status": "source_verified",
    },
    {
        "id": "fitts-2010",
        "authors": "R. H. Fitts, S. W. Trappe, D. L. Costill, P. M. Gallagher, "
        "A. C. Creer, P. A. Colloton, J. R. Peters, J. G. Romatowski, "
        "J. L. Bain, D. A. Riley",
        "year": 2010,
        "title": (
            "Prolonged space flight-induced alterations in the structure and "
            "function of human skeletal muscle fibres"
        ),
        "journal": "The Journal of Physiology, 588(18), 3567-3592",
        "doi": "10.1113/jphysiol.2010.188508",
        "source_file": "tjp0588-3567.pdf",
        "research_question": (
            "What structural and functional changes occur in slow- and fast-type "
            "human skeletal muscle fibres after prolonged spaceflight?"
        ),
        "population": (
            "ISS crew members on Increments 5-11. Ten participated; postflight "
            "samples from one were damaged and excluded, leaving nine analyzed "
            "crew members. The ten participants included five American astronauts "
            "and five Russian cosmonauts."
        ),
        "sample_size": 9,
        "sample_size_note": (
            "Nine crew members analyzed; the article states that ten took part "
            "and one was excluded because postflight muscle samples were damaged."
        ),
        "study_design": (
            "Paired observational preflight/postflight muscle-biopsy study "
            "following approximately six-month ISS missions."
        ),
        "measurement_methods": (
            "Soleus and gastrocnemius biopsies were obtained before and after "
            "flight. Isolated slow type I and fast type II fibres were examined "
            "for size and contractile properties; microscopy and protein "
            "analyses assessed structural features."
        ),
        "outcomes": (
            "Individual muscle-fibre diameter and cross-sectional area; peak "
            "isometric force, maximal unloaded shortening velocity, peak power, "
            "force-velocity and force-calcium properties; myofilament structure "
            "and protein composition."
        ),
        "timepoints": (
            "Preflight biopsy at L-55 +/- 2 days and postflight biopsy on landing "
            "day (R+0), approximately 6-8 hours after landing. Flight duration "
            "for the analyzed crew averaged about 177 days."
        ),
        "findings": (
            "The authors report reductions in fibre size, force, and power after "
            "flight, with larger effects in soleus than gastrocnemius fibres and "
            "in slow type I than fast type II fibres. They attribute much of "
            "the force loss to fibre atrophy and describe structural changes "
            "associated with reduced shortening velocity. These are cellular "
            "fibre findings, not whole-joint strength measurements."
        ),
        "limitations": (
            "The authors identify a potential limitation that sampled biopsies "
            "and fibres may not fully represent changes in whole muscles. The "
            "analyzed crew cohort is small, responses varied between people, "
            "and results from individual fibres should not be generalized as "
            "whole-joint strength values."
        ),
        "source_availability": "full_text",
        "extraction_status": "full_text_reviewed",
        "quantitative_verification_status": "source_verified",
    },
    {
        "id": "scott-2023",
        "authors": (
            "Jessica M. Scott, Alan H. Feiveson, Kirk L. English, "
            "Elisabeth R. Spector, Jean D. Sibonga, E. Lichar Dillon, "
            "Lori Ploutz-Snyder, Meghan E. Everett"
        ),
        "year": 2023,
        "title": (
            "Effects of exercise countermeasures on multisystem function "
            "in long duration spaceflight astronauts"
        ),
        "journal": "npj Microgravity, 9 (2023)",
        "doi": "10.1038/s41526-023-00256-5",
        "source_file": (
            "Effects of exercise countermeasures on multisystem function "
            "in long duration spaceflight astronauts (2023).pdf"
        ),
        "research_question": (
            "How are exercise countermeasures associated with multisystem "
            "function during long-duration astronaut spaceflight?"
        ),
        "population": (
            "Forty-six astronauts with long-duration spaceflight data; mean "
            "flight duration 178 ± 48 days."
        ),
        "sample_size": 46,
        "sample_size_note": (
            "The abstract reports N=46. Endpoint-specific sample sizes vary; "
            "supplemental tables and figures are not locally available."
        ),
        "study_design": (
            "Observational analysis of preflight and postflight multisystem "
            "outcomes in astronauts."
        ),
        "measurement_methods": (
            "Exercise exposure and pre/postflight measures including strength, "
            "lower-leg cross-sectional area, cardiorespiratory fitness, body "
            "composition, and bone outcomes."
        ),
        "outcomes": (
            "Multisystem function and exercise exposure; outcomes require "
            "endpoint-specific compatibility review."
        ),
        "timepoints": (
            "Preflight and postflight; endpoint-specific times and sample "
            "sizes require full-text table review."
        ),
        "findings": (
            "The abstract reports about 600 min/week of aerobic and resistance "
            "exercise and heterogeneous pre/postflight multisystem changes. "
            "No new values have been verified for calculation."
        ),
        "limitations": (
            "Observational design and heterogeneous systems/outcomes. The "
            "ground-analogue-derived performance-risk threshold is not a "
            "direct flight measurement. No values are admitted to the engine."
        ),
        "source_availability": "full_text",
        "extraction_status": "text_accessible",
        "quantitative_verification_status": "not_assessed",
    },
    {
        "id": "trappe-2009",
        "authors": (
            "Scott Trappe, David Costill, Philip Gallagher, Andrew Creer, "
            "Jim R. Peters, Harlan Evans, Danny A. Riley, Robert H. Fitts"
        ),
        "year": 2009,
        "title": (
            "Exercise in space: human skeletal muscle after 6 months aboard "
            "the International Space Station"
        ),
        "journal": "Journal of Applied Physiology, 106, 1159-1168",
        "doi": "10.1152/japplphysiol.91578.2008",
        "source_file": (
            "Exercise in space human skeletal muscle after 6 months "
            "aboardthe International Space Station (2009.pdf"
        ),
        "research_question": (
            "How did skeletal-muscle volume and performance change after "
            "six months aboard the International Space Station?"
        ),
        "population": "Nine analyzed ISS crewmembers following six-month missions.",
        "sample_size": 9,
        "sample_size_note": (
            "Nine analyzed crew members; outcome-specific numerical results "
            "require manual review of the full article tables."
        ),
        "study_design": (
            "Observational preflight/postflight study of ISS crew, including "
            "postflight recovery measurements."
        ),
        "measurement_methods": (
            "Exercise exposure, calf muscle volume and performance, and "
            "muscle-fibre outcomes."
        ),
        "outcomes": (
            "Muscle volume, force/velocity, endurance, and fibre composition; "
            "these are distinct measurement levels."
        ),
        "timepoints": (
            "Preflight, postflight, and reported recovery timepoints including "
            "R+7, R+13, and R+19; outcome-specific timing needs review."
        ),
        "findings": (
            "The article examines skeletal-muscle outcomes after six-month "
            "ISS missions. No new values have been verified for calculation."
        ),
        "limitations": (
            "Small cohort and multiple biological measurement levels. No "
            "values are currently admitted to the engine."
        ),
        "source_availability": "full_text",
        "extraction_status": "text_accessible",
        "quantitative_verification_status": "not_assessed",
    },
    {
        "id": "sprint-2020",
        "authors": (
            "Kirk L. English, Meghan Downs, Elizabeth Goetchius, Roxanne "
            "Buxton, Jeffrey W. Ryder, Robert Ploutz-Snyder, Mark Guilliams, "
            "Jessica M. Scott, Lori L. Ploutz-Snyder"
        ),
        "year": 2020,
        "title": (
            "High intensity training during spaceflight: results from the "
            "NASA Sprint Study"
        ),
        "journal": "npj Microgravity (2020)",
        "doi": "10.1038/s41526-020-00111-x",
        "source_file": (
            "High intensity training during spaceflight results from the "
            "NASA Sprint Study (2020).pdf"
        ),
        "research_question": (
            "How did the NASA Sprint high-intensity, lower-volume exercise "
            "program compare with standard ISS exercise?"
        ),
        "population": (
            "ISS crew in the control group (n=17) and SPRINT group (n=9), "
            "26 participants total as reported in Table 5."
        ),
        "sample_size": 26,
        "sample_size_note": (
            "Table 5 reports control n=17 and SPRINT n=9. Endpoint-specific "
            "sample sizes and results have not been curated."
        ),
        "study_design": (
            "Comparison of exercise programs during ISS spaceflight; group "
            "allocation and outcome-specific methods require full-text review."
        ),
        "measurement_methods": (
            "Exercise exposure and pre/postflight physiological outcomes."
        ),
        "outcomes": (
            "Strength/function, bone density, lean/fat mass, and "
            "cardiorespiratory fitness."
        ),
        "timepoints": (
            "Preflight and postflight; outcome-specific timepoints require "
            "manual source review."
        ),
        "findings": (
            "The article compares SPRINT exercise with standard ISS exercise. "
            "No new values have been verified for calculation."
        ),
        "limitations": (
            "Outcomes are not limited to muscle atrophy, and exercise-program "
            "comparisons are not assumed to be causal. No values are admitted "
            "to the engine."
        ),
        "source_availability": "full_text",
        "extraction_status": "text_accessible",
        "quantitative_verification_status": "not_assessed",
    },
    {
        "id": "leblanc-2000",
        "authors": (
            "Adrian LeBlanc, Chen Lin, Linda Shackelford, Valentine Sinitsyn, "
            "Harlan Evans, Oleg Belichenko, Boris Schenkman, Inessa "
            "Kozlovskaya, Victor Oganov, Alexi Bakulin, Thomas Hedrick, "
            "Daniel Feeback"
        ),
        "year": 2000,
        "title": (
            "Muscle volume, MRI relaxation times (T2), and body composition "
            "after spaceflight"
        ),
        "journal": "Journal of Applied Physiology, 89, 2158-2164",
        "doi": "10.1152/jappl.2000.89.6.2158",
        "source_file": (
            "Muscle volume, MRI relaxation times (T2), and bodycomposition "
            "after spaceﬂight (2000).pdf"
        ),
        "research_question": (
            "How did muscle volume, calf MRI T2, and body composition change "
            "after spaceflight and during recovery?"
        ),
        "population": (
            "Separate cohorts, including four participants after a 17-day "
            "mission and 14-16 after shuttle/Mir missions lasting 16-28 weeks."
        ),
        "sample_size": None,
        "sample_size_note": (
            "Sample sizes differ by cohort and outcome; these groups are not "
            "collapsed into one sample."
        ),
        "study_design": (
            "Observational measurements after actual spaceflight, including "
            "short-duration and shuttle/Mir missions; not ISS data."
        ),
        "measurement_methods": (
            "Muscle volume, calf MRI T2, body composition, and recovery "
            "measurements."
        ),
        "outcomes": (
            "Muscle volume, MRI relaxation times, and body composition; "
            "cohorts and outcomes remain distinct."
        ),
        "timepoints": (
            "Postflight and recovery observations following missions of "
            "different durations; exact times require full-text review."
        ),
        "findings": (
            "The article reports muscle-volume, calf MRI T2, and body-"
            "composition outcomes after short and shuttle/Mir flights. No new "
            "values have been verified for calculation."
        ),
        "limitations": (
            "These are not ISS missions; cohorts and durations differ. Data "
            "are not pooled with ISS evidence and are not engine inputs."
        ),
        "source_availability": "full_text",
        "extraction_status": "text_accessible",
        "quantitative_verification_status": "not_assessed",
    },
    {
        "id": "gopalakrishnan-2010",
        "authors": (
            "Raghavan Gopalakrishnan, Kerim O. Genc, Andrea J. Rice, "
            "Stuart M. C. Lee, Harlan J. Evans, Christian C. Maender, "
            "Hakan Ilaslan, Peter R. Cavanagh"
        ),
        "year": 2010,
        "title": (
            "Muscle Volume, Strength, Endurance, and Exercise Loads During "
            "6-Month Missions in Space"
        ),
        "journal": (
            "Aviation, Space, and Environmental Medicine, 81(2), 91-104"
        ),
        "doi": "10.3357/asem.2583.2010",
        "source_file": (
            "Muscle volume, strength, endurance, and exercise loads during "
            "6-month missions in space (2010) PDF.pdf"
        ),
        "research_question": (
            "How did muscle volume, strength, endurance, and exercise loading "
            "change in ISS crewmembers during six-month missions?"
        ),
        "population": (
            "The one-page abstract reports four male ISS crewmembers, "
            "49.5 ± 4.7 years, with mean flight duration 181 ± 15 days."
        ),
        "sample_size": 4,
        "sample_size_note": (
            "n=4 is stated in the one-page abstract. No full article, tables, figures, "
            "or methods beyond the abstract are available locally."
        ),
        "study_design": (
            "Abstract-only report of preflight, in-flight, and postflight "
            "measures in four male ISS crewmembers."
        ),
        "measurement_methods": (
            "The abstract reports muscle volume and strength measurements, "
            "endurance testing, and preflight/in-flight foot-shoe force "
            "measurements during exercise."
        ),
        "outcomes": (
            "The abstract reports broad regional muscle-volume changes, "
            "ranges of knee/ankle/elbow strength changes, endurance, and "
            "relative in-shoe force differences for running and cycling."
        ),
        "timepoints": (
            "Preflight, in-flight loading, and postflight; exact outcome "
            "timepoints are not reported in the available abstract."
        ),
        "findings": (
            "Abstract only: calf volume change is printed as -10 to 16% "
            "(ambiguous/suspicious); thigh -4% to -7%; upper arm +0.4 to "
            "-0.8%; strength-change ranges are given for knee, ankle, and "
            "elbow; total work declined 14%; peak in-shoe forces during ISS "
            "running and cycling were approximately 46% and 50% lower than "
            "1-g values. These remain contextual evidence, not model inputs."
        ),
        "limitations": (
            "Only a one-page abstract is available; detailed methods, "
            "outcome-specific sample sizes, tables, and figures were not "
            "reviewed. The calf volume range is ambiguous, and other reported "
            "ranges do not map to a specific compatible engine outcome. No "
            "abstract value calibrates, validates, or predicts a model."
        ),
        "source_availability": "abstract_only",
        "extraction_status": "abstract_extracted",
        "quantitative_verification_status": "context_only",
    },
    {
        "id": "greene-2021",
        "authors": (
            "Katelyn A. Greene, Shanna S. Withers, Leon Lenchik, "
            "Janet A. Tooze, Ashley A. Weaver"
        ),
        "year": 2021,
        "title": "Trunk Skeletal Muscle Changes on CT with Long-Duration Spaceflight",
        "journal": "Annals of Biomedical Engineering, 49(4), 1257-1266",
        "doi": "10.1007/s10439-021-02745-8",
        "source_file": (
            "Trunk Skeletal Muscle Changes on CT with Long-Duration (2021).pdf"
        ),
        "research_question": (
            "How does CT-measured trunk skeletal muscle change following "
            "long-duration spaceflight and during recovery?"
        ),
        "population": (
            "Sixteen crewmembers on 4-6 month missions; sample size varies "
            "for some follow-up and index comparisons."
        ),
        "sample_size": 16,
        "sample_size_note": (
            "The abstract reports 16 crewmembers; some comparisons have "
            "smaller sample sizes."
        ),
        "study_design": (
            "Observational astronaut study using CT and DXA before and after "
            "long-duration spaceflight, with later follow-up."
        ),
        "measurement_methods": (
            "CT measurements of trunk muscle area and attenuation and DXA "
            "body-composition indices."
        ),
        "outcomes": (
            "Trunk muscle cross-sectional area and attenuation, plus DXA "
            "indices; CT area is morphology, not strength."
        ),
        "timepoints": (
            "Preflight, return, one-year, and 2-4-year postflight follow-up."
        ),
        "findings": (
            "The abstract reports decreased trunk muscle area at return and "
            "recovery at later follow-up. No new values have been verified "
            "for calculation."
        ),
        "limitations": (
            "Morphology is not direct strength or function. Follow-up "
            "intervals and sample sizes differ; no values are admitted to "
            "the engine."
        ),
        "source_availability": "full_text",
        "extraction_status": "text_accessible",
        "quantitative_verification_status": "not_assessed",
    },
)


@dataclass(frozen=True)
class MeasurementInput:
    study_id: str
    muscle_or_outcome: str
    measurement_name: str
    value: str | None = None
    value_status: str = "unreported"
    unit: str | None = None
    timepoint: str | None = None
    comparison_baseline: str | None = None
    sample_size: int | None = None
    sample_size_status: str = "unreported"
    source_page: str | None = None
    source_location: str | None = None
    source_wording: str | None = None
    verification_status: str = "unverified"
    uncertainty_notes: str | None = None


def initialize_database(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> sqlite3.Connection:
    """Create the library schema, seed source summaries, and return a connection."""
    connection = connect_database(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS studies (
            id TEXT PRIMARY KEY,
            authors TEXT NOT NULL,
            year INTEGER NOT NULL,
            title TEXT NOT NULL,
            journal TEXT NOT NULL,
            doi TEXT NOT NULL,
            source_file TEXT NOT NULL,
            research_question TEXT NOT NULL,
            population TEXT NOT NULL,
            sample_size INTEGER,
            sample_size_note TEXT NOT NULL,
            study_design TEXT NOT NULL,
            measurement_methods TEXT NOT NULL,
            outcomes TEXT NOT NULL,
            timepoints TEXT NOT NULL,
            findings TEXT NOT NULL,
            limitations TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY,
            study_id TEXT NOT NULL REFERENCES studies(id),
            muscle_or_outcome TEXT NOT NULL,
            measurement_name TEXT NOT NULL,
            value TEXT,
            value_status TEXT NOT NULL
                CHECK (value_status IN ('reported', 'unreported', 'unknown')),
            unit TEXT,
            timepoint TEXT,
            comparison_baseline TEXT,
            sample_size INTEGER,
            sample_size_status TEXT NOT NULL
                CHECK (sample_size_status IN ('reported', 'unreported', 'unknown')),
            source_page TEXT,
            source_location TEXT,
            source_wording TEXT,
            verification_status TEXT NOT NULL DEFAULT 'unverified'
                CHECK (verification_status IN ('unverified', 'source_verified')),
            uncertainty_notes TEXT,
            CHECK (
                (value_status = 'reported' AND value IS NOT NULL AND trim(value) <> '')
                OR (value_status <> 'reported' AND value IS NULL)
            ),
            CHECK (
                (sample_size_status = 'reported' AND sample_size IS NOT NULL)
                OR (sample_size_status <> 'reported' AND sample_size IS NULL)
            ),
            CHECK (
                verification_status <> 'source_verified'
                OR (
                    source_page IS NOT NULL AND trim(source_page) <> ''
                    AND source_wording IS NOT NULL AND trim(source_wording) <> ''
                )
            )
        );
        """
    )
    _migrate_study_source_status(connection)
    connection.executemany(
        """
        INSERT OR IGNORE INTO studies (
            id, authors, year, title, journal, doi, source_file,
            research_question, population, sample_size, sample_size_note,
            study_design, measurement_methods, outcomes, timepoints,
            findings, limitations, source_availability, extraction_status,
            quantitative_verification_status
        ) VALUES (
            :id, :authors, :year, :title, :journal, :doi, :source_file,
            :research_question, :population, :sample_size, :sample_size_note,
            :study_design, :measurement_methods, :outcomes, :timepoints,
            :findings, :limitations, :source_availability, :extraction_status,
            :quantitative_verification_status
        )
        """,
        STUDIES,
    )
    connection.executemany(
        """
        UPDATE studies
        SET source_availability = :source_availability,
            extraction_status = :extraction_status,
            quantitative_verification_status =
                :quantitative_verification_status
        WHERE id = :id
        """,
        (
            {
                "id": study["id"],
                "source_availability": study["source_availability"],
                "extraction_status": study["extraction_status"],
                "quantitative_verification_status": study[
                    "quantitative_verification_status"
                ],
            }
            for study in STUDIES
        ),
    )
    connection.commit()
    return connection


def _migrate_study_source_status(connection: sqlite3.Connection) -> None:
    """Add source/evidence states without replacing existing library records."""
    existing_columns = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info(studies)").fetchall()
    }
    new_columns = {
        "source_availability": (
            "TEXT NOT NULL DEFAULT 'full_text' "
            "CHECK (source_availability IN ('full_text', 'abstract_only'))"
        ),
        "extraction_status": (
            "TEXT NOT NULL DEFAULT 'not_extracted' CHECK (extraction_status IN "
            "('not_extracted', 'abstract_extracted', 'text_accessible', "
            "'full_text_reviewed'))"
        ),
        "quantitative_verification_status": (
            "TEXT NOT NULL DEFAULT 'not_assessed' CHECK "
            "(quantitative_verification_status IN "
            "('not_assessed', 'context_only', 'source_verified'))"
        ),
    }
    for column, definition in new_columns.items():
        if column not in existing_columns:
            connection.execute(
                f"ALTER TABLE studies ADD COLUMN {column} {definition}"
            )
    connection.commit()


def list_studies(connection: sqlite3.Connection) -> list[dict[str, object]]:
    """Return studies ordered by publication year and title."""
    rows = connection.execute(
        "SELECT * FROM studies ORDER BY year DESC, title"
    ).fetchall()
    return [dict(row) for row in rows]


def get_study(
    connection: sqlite3.Connection, study_id: str
) -> dict[str, object] | None:
    """Retrieve one study or return ``None`` when the identifier is absent."""
    row = connection.execute(
        "SELECT * FROM studies WHERE id = ?", (study_id,)
    ).fetchone()
    return dict(row) if row is not None else None


def list_measurements(
    connection: sqlite3.Connection, study_id: str
) -> list[dict[str, object]]:
    """Return manually curated measurements for a study."""
    rows = connection.execute(
        "SELECT * FROM measurements WHERE study_id = ? ORDER BY id",
        (study_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def add_measurement(
    connection: sqlite3.Connection, measurement: MeasurementInput
) -> int:
    """Store one measurement record without promoting unverified values."""
    if not measurement.muscle_or_outcome.strip():
        raise ValueError("A muscle, muscle group, or outcome is required")
    if not measurement.measurement_name.strip():
        raise ValueError("A measurement name is required")
    if measurement.value_status not in {"reported", "unreported", "unknown"}:
        raise ValueError("value_status must be reported, unreported, or unknown")
    if measurement.sample_size_status not in {
        "reported",
        "unreported",
        "unknown",
    }:
        raise ValueError(
            "sample_size_status must be reported, unreported, or unknown"
        )
    if measurement.verification_status not in {"unverified", "source_verified"}:
        raise ValueError(
            "verification_status must be unverified or source_verified"
        )

    value = _clean(measurement.value)
    if measurement.value_status == "reported" and value is None:
        raise ValueError("A reported measurement value is required")
    if measurement.value_status != "reported" and value is not None:
        raise ValueError("Only reported measurements can have a value")
    if measurement.sample_size_status == "reported" and measurement.sample_size is None:
        raise ValueError("A reported sample size is required")
    if measurement.sample_size is not None and measurement.sample_size < 1:
        raise ValueError("A reported sample size must be positive")
    if measurement.sample_size_status != "reported" and measurement.sample_size is not None:
        raise ValueError("Only reported sample sizes can have a value")
    if measurement.verification_status == "source_verified":
        _require_verification_evidence(
            measurement.source_page, measurement.source_wording
        )

    cursor = connection.execute(
        """
        INSERT INTO measurements (
            study_id, muscle_or_outcome, measurement_name, value, value_status,
            unit, timepoint, comparison_baseline, sample_size, sample_size_status,
            source_page, source_location, source_wording, verification_status,
            uncertainty_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            measurement.study_id,
            measurement.muscle_or_outcome.strip(),
            measurement.measurement_name.strip(),
            value,
            measurement.value_status,
            _clean(measurement.unit),
            _clean(measurement.timepoint),
            _clean(measurement.comparison_baseline),
            measurement.sample_size,
            measurement.sample_size_status,
            _clean(measurement.source_page),
            _clean(measurement.source_location),
            _clean(measurement.source_wording),
            measurement.verification_status,
            _clean(measurement.uncertainty_notes),
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def mark_measurement_source_verified(
    connection: sqlite3.Connection,
    measurement_id: int,
    *,
    source_page: str,
    source_wording: str,
    source_location: str | None = None,
    uncertainty_notes: str | None = None,
) -> None:
    """Mark a measurement verified only when source page and wording are supplied."""
    _require_verification_evidence(source_page, source_wording)
    cursor = connection.execute(
        """
        UPDATE measurements
        SET verification_status = 'source_verified',
            source_page = ?,
            source_location = COALESCE(?, source_location),
            source_wording = ?,
            uncertainty_notes = COALESCE(?, uncertainty_notes)
        WHERE id = ?
        """,
        (
            source_page.strip(),
            _clean(source_location),
            source_wording.strip(),
            _clean(uncertainty_notes),
            measurement_id,
        ),
    )
    if cursor.rowcount == 0:
        raise ValueError(f"Measurement {measurement_id} was not found")
    connection.commit()


def _require_verification_evidence(
    source_page: str | None, source_wording: str | None
) -> None:
    if not _clean(source_page) or not _clean(source_wording):
        raise ValueError(
            "Source verification requires a source page and exact source wording"
        )


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
