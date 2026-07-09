"""
Configuration for the Project Health Reporting Agent.

Column mapping is fuzzy/alias-based so the agent can read project plan
exports that don't all use identical headers (a common reality across
PMs/tools). If a required signal is genuinely missing from a file, the
engine degrades gracefully (documented in RAG_Methodology.md) rather
than crashing or guessing.
"""

# Canonical field -> list of header aliases we'll accept (case-insensitive,
# whitespace-insensitive). First match wins.
COLUMN_ALIASES = {
    "task_name": ["task name", "task", "activity", "activity name"],
    "status": ["status", "task status"],
    "pct_complete": ["% complete", "percent complete", "pct complete", "% done"],
    "start_date": ["start date", "start"],
    "end_date": ["end date", "end", "finish", "finish date"],
    "baseline_start": ["baseline start", "baseline start date", "baseline start2"],
    "baseline_end": ["baseline finish", "baseline end date", "baseline finish2",
                      "baseline end"],
    "variance": ["variance", "variance2"],
    "schedule_health": ["schedule health", "health"],
    "priority": ["priority"],
    "critical": ["critical ?", "critical", "critical?"],
    "total_float": ["total float", "float"],
    "on_hold": ["on hold?", "on hold"],
    "not_applicable": ["not applicable?", "not applicable", "na"],
    "predecessors": ["predecessors", "predecessor"],
    "ancestors": ["ancestors", "indent", "level", "outline level"],
    "owner": ["owner", "assigned to", "assignee"],
    "project_manager": ["project manager", "pm"],
    "project_name": ["project name", "project"],
    "status_comment": ["status comment"],
    "comments_text": ["comments", "comment", "notes"],
    "task_rag": ["rag"],
    "area": ["area", "workstream"],
    "phase_milestone": ["phase/milestone", "phase", "milestone"],
    "at_risk": ["at risk?", "at risk"],
}

# --- RAG scoring thresholds -------------------------------------------------
# Each dimension is scored 0 (Green-like), 1 (Amber-like) or 2 (Red-like).
# See RAG_Methodology.md for the full rationale behind these numbers.

THRESHOLDS = {
    # Share of in-flight/overdue tasks that are late vs. their planned end date
    "schedule_slippage_amber_pct": 0.10,   # >10% of active tasks overdue -> Amber
    "schedule_slippage_red_pct": 0.25,     # >25% overdue -> Red

    # Share of tasks explicitly flagged Red/Yellow by the PM in-tool
    "flagged_red_amber_pct": 0.05,
    "flagged_red_red_pct": 0.15,

    # Overdue CRITICAL-path tasks (any one is a big deal)
    "critical_overdue_amber_count": 1,
    "critical_overdue_red_count": 3,

    # Milestone (top-level phase) lateness - phases whose window has closed
    # but which aren't complete
    "milestone_late_amber_count": 1,
    "milestone_late_red_count": 2,

    # % complete vs. % of timeline elapsed (schedule performance ratio, SPI-lite)
    "spi_amber": 0.85,   # actual/expected < 0.85 -> Amber
    "spi_red": 0.65,     # actual/expected < 0.65 -> Red

    # Blockers: tasks whose predecessors are done but they haven't started,
    # despite being past their planned start date
    "blocker_amber_count": 2,
    "blocker_red_count": 5,
}

# Weights used to combine per-dimension scores (0/1/2) into one composite.
# Budget and Sentiment default to weight 0 automatically when data is not
# present in the source file (see rag_engine.available_dimensions).
DIMENSION_WEIGHTS = {
    "schedule": 1.0,
    "milestones": 1.0,
    "blockers": 0.8,
    "budget": 1.0,
    "sentiment": 0.6,
}

# Composite score -> overall RAG. Composite is weighted average of available
# dimensions, each in [0, 2].
COMPOSITE_AMBER = 0.6
COMPOSITE_RED = 1.2
