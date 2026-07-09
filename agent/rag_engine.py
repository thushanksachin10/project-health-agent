"""
Core RAG determination logic.

Every dimension function returns a dict:
    {
        "score": 0 | 1 | 2 | None,   # None = not evaluable (data missing)
        "label": "Green" | "Amber" | "Red" | "Unknown",
        "evidence": [ ...human-readable facts... ],
        "metrics": { ...raw numbers for the JSON output... },
    }

This keeps every dimension self-documenting: the "why" travels with the
score, which is what lets narrative.py build plain-English reasoning
without an LLM if needed, and gives an LLM good grounding when used.
"""

from datetime import date
from .config import THRESHOLDS, DIMENSION_WEIGHTS, COMPOSITE_AMBER, COMPOSITE_RED
from .parser import ProjectPlan

LABELS = {0: "Green", 1: "Amber", 2: "Red"}


def _label(score):
    return LABELS.get(score, "Unknown")


def _active_tasks(plan: ProjectPlan):
    return [t for t in plan.tasks
            if not (t.not_applicable or t.on_hold)
            and (t.status or "").strip().lower() != "completed"]


def score_schedule(plan: ProjectPlan) -> dict:
    as_of = plan.as_of
    active = _active_tasks(plan)
    tasks_with_enddate = [t for t in active if t.end_date]
    overdue = [t for t in tasks_with_enddate if t.end_date < as_of]

    flagged = [t for t in plan.tasks if (t.schedule_health or "").strip().lower() in ("red",)]
    flagged_amber = [t for t in plan.tasks if (t.schedule_health or "").strip().lower() in ("yellow", "amber")]

    critical_overdue = [t for t in overdue if t.critical]

    total_dated = len(tasks_with_enddate) or 1
    overdue_pct = len(overdue) / total_dated
    flagged_pct = len(flagged) / (len(plan.tasks) or 1)

    # SPI-lite: expected % complete (by elapsed time across project window)
    # vs actual overall % complete, using earliest start / latest end as the
    # project window when baseline project dates aren't separately given.
    starts = [t.start_date for t in plan.tasks if t.start_date]
    ends = [t.end_date for t in plan.tasks if t.end_date]
    spi = None
    if starts and ends:
        proj_start, proj_end = min(starts), max(ends)
        total_days = (proj_end - proj_start).days or 1
        elapsed_days = max(0, min((as_of - proj_start).days, total_days))
        expected_pct = elapsed_days / total_days
        pct_vals = [t.pct_complete for t in plan.tasks if t.pct_complete is not None]
        actual_pct = sum(pct_vals) / len(pct_vals) if pct_vals else None
        if actual_pct is not None and expected_pct > 0:
            spi = actual_pct / expected_pct if expected_pct else None

    score = 0
    evidence = []

    if overdue_pct > THRESHOLDS["schedule_slippage_red_pct"]:
        score = max(score, 2)
        evidence.append(f"{len(overdue)} of {total_dated} active tasks ({overdue_pct:.0%}) are past their planned end date.")
    elif overdue_pct > THRESHOLDS["schedule_slippage_amber_pct"]:
        score = max(score, 1)
        evidence.append(f"{len(overdue)} of {total_dated} active tasks ({overdue_pct:.0%}) are past their planned end date.")
    elif overdue:
        evidence.append(f"{len(overdue)} active task(s) are past their planned end date, within tolerance.")

    if flagged_pct > THRESHOLDS["flagged_red_red_pct"]:
        score = max(score, 2)
        evidence.append(f"{len(flagged)} tasks ({flagged_pct:.0%}) are self-flagged Red in the plan.")
    elif flagged_pct > THRESHOLDS["flagged_red_amber_pct"]:
        score = max(score, 1)
        evidence.append(f"{len(flagged)} tasks ({flagged_pct:.0%}) are self-flagged Red in the plan.")
    elif flagged:
        evidence.append(f"{len(flagged)} task(s) flagged Red in the plan, within tolerance.")

    if len(critical_overdue) >= THRESHOLDS["critical_overdue_red_count"]:
        score = max(score, 2)
        evidence.append(f"{len(critical_overdue)} critical-path tasks are overdue.")
    elif len(critical_overdue) >= THRESHOLDS["critical_overdue_amber_count"]:
        score = max(score, 1)
        evidence.append(f"{len(critical_overdue)} critical-path task(s) overdue.")

    if spi is not None:
        if spi < THRESHOLDS["spi_red"]:
            score = max(score, 2)
            evidence.append(f"Actual progress is running at {spi:.0%} of the pace needed for the elapsed timeline.")
        elif spi < THRESHOLDS["spi_amber"]:
            score = max(score, 1)
            evidence.append(f"Actual progress is running at {spi:.0%} of the pace needed for the elapsed timeline.")

    if not evidence:
        evidence.append("No meaningful schedule slippage detected in active tasks.")

    return {
        "score": score,
        "label": _label(score),
        "evidence": evidence,
        "metrics": {
            "overdue_count": len(overdue),
            "overdue_pct": round(overdue_pct, 3),
            "flagged_red_count": len(flagged),
            "flagged_amber_count": len(flagged_amber),
            "critical_overdue_count": len(critical_overdue),
            "spi_lite": round(spi, 3) if spi is not None else None,
        },
    }


def score_milestones(plan: ProjectPlan) -> dict:
    """Top-level phases (Ancestors depth 1, or Phase/Milestone rows) that have
    passed their end date but aren't complete."""
    as_of = plan.as_of
    if not plan.tasks or all(t.ancestors is None for t in plan.tasks):
        return {"score": None, "label": "Unknown", "evidence": [
            "No hierarchy/outline-level data available to identify milestones/phases."
        ], "metrics": {}}

    top_level = [t for t in plan.tasks if t.ancestors == 1]
    if not top_level:
        return {"score": None, "label": "Unknown", "evidence": [
            "Could not identify top-level phase/milestone rows in this file."
        ], "metrics": {}}

    late = [t for t in top_level
            if t.end_date and t.end_date < as_of
            and (t.status or "").strip().lower() != "completed"]

    score = 0
    evidence = []
    if len(late) >= THRESHOLDS["milestone_late_red_count"]:
        score = 2
    elif len(late) >= THRESHOLDS["milestone_late_amber_count"]:
        score = 1

    if late:
        names = ", ".join(t.task_name or "Unnamed phase" for t in late[:3])
        evidence.append(f"{len(late)} of {len(top_level)} major phase(s) are past their planned end date and not yet complete (e.g. {names}).")
    else:
        evidence.append(f"All {len(top_level)} major phases are on or ahead of their planned end dates (or already complete).")

    return {
        "score": score,
        "label": _label(score),
        "evidence": evidence,
        "metrics": {"phases_total": len(top_level), "phases_late": len(late)},
    }


def score_blockers(plan: ProjectPlan) -> dict:
    """Tasks that look stuck: predecessor work is done, this task's planned
    start has passed, but it still hasn't started."""
    as_of = plan.as_of
    candidates = [t for t in plan.tasks if t.predecessors and (t.status or "").lower() == "not started"]
    stuck = [t for t in candidates if t.start_date and t.start_date < as_of]

    on_hold = [t for t in plan.tasks if t.on_hold]

    score = 0
    evidence = []
    count = len(stuck)
    if count >= THRESHOLDS["blocker_red_count"]:
        score = 2
    elif count >= THRESHOLDS["blocker_amber_count"]:
        score = 1

    if stuck:
        evidence.append(f"{count} dependent task(s) have a passed start date but haven't started (possible blockers).")
    else:
        evidence.append("No tasks identified as stuck behind unmet dependencies.")
    if on_hold:
        evidence.append(f"{len(on_hold)} task(s) explicitly marked On Hold.")
        score = max(score, 1)

    return {
        "score": score,
        "label": _label(score),
        "evidence": evidence,
        "metrics": {"stuck_count": count, "on_hold_count": len(on_hold)},
    }


def score_budget(plan: ProjectPlan, budget_data: dict = None) -> dict:
    """Budget is not present in the standard task-plan export. If the caller
    supplies budget_data (e.g. from a separate finance feed), we score it;
    otherwise we report this dimension as Unknown and exclude it from the
    composite (documented assumption -- see RAG_Methodology.md)."""
    if not budget_data:
        return {
            "score": None,
            "label": "Unknown",
            "evidence": ["No budget/cost-actuals data was available in this file; "
                         "budget health excluded from this report (see methodology doc)."],
            "metrics": {},
        }
    planned = budget_data.get("planned_cost")
    actual = budget_data.get("actual_cost")
    pct_complete = budget_data.get("pct_complete_time")  # optional
    if not planned or actual is None:
        return {"score": None, "label": "Unknown",
                "evidence": ["Budget data incomplete; excluded from composite."], "metrics": budget_data}

    burn_pct = actual / planned
    score = 0
    evidence = [f"Burn is {burn_pct:.0%} of total planned budget."]
    if burn_pct > 1.10:
        score = 2
    elif burn_pct > 1.0:
        score = 1
    return {"score": score, "label": _label(score), "evidence": evidence,
            "metrics": {"burn_pct": round(burn_pct, 3)}}


def score_sentiment(plan: ProjectPlan) -> dict:
    """Stakeholder sentiment is not captured as structured data in this
    export (no PM status-comment free text present). We surface any
    status/PM comments we do find as a light-touch proxy, and otherwise
    mark Unknown rather than fabricate a sentiment reading."""
    comments = [t.status_comment for t in plan.tasks if t.status_comment]
    if not comments:
        return {
            "score": None,
            "label": "Unknown",
            "evidence": ["No PM status comments / stakeholder notes found in this file; "
                         "sentiment excluded from this report (see methodology doc)."],
            "metrics": {},
        }
    # Very light keyword proxy -- flagged as a proxy, not a real sentiment model.
    negative_kw = ("delay", "risk", "issue", "blocked", "concern", "escalat", "slip")
    neg_hits = sum(1 for c in comments if any(k in c.lower() for k in negative_kw))
    neg_pct = neg_hits / len(comments)
    score = 2 if neg_pct > 0.4 else 1 if neg_pct > 0.15 else 0
    return {
        "score": score,
        "label": _label(score),
        "evidence": [f"{neg_hits} of {len(comments)} status comments contain risk/delay language (keyword proxy, not true sentiment analysis)."],
        "metrics": {"comment_count": len(comments), "negative_pct": round(neg_pct, 3)},
    }


def compute_rag(plan: ProjectPlan, budget_data: dict = None) -> dict:
    dims = {
        "schedule": score_schedule(plan),
        "milestones": score_milestones(plan),
        "blockers": score_blockers(plan),
        "budget": score_budget(plan, budget_data),
        "sentiment": score_sentiment(plan),
    }

    weighted_sum = 0.0
    weight_total = 0.0
    for name, d in dims.items():
        if d["score"] is None:
            continue
        w = DIMENSION_WEIGHTS[name]
        weighted_sum += w * d["score"]
        weight_total += w

    if weight_total == 0:
        composite = None
        overall = "Unknown"
    else:
        composite = weighted_sum / weight_total
        if composite >= COMPOSITE_RED:
            overall = "Red"
        elif composite >= COMPOSITE_AMBER:
            overall = "Amber"
        else:
            overall = "Green"

    # Escalation override: any single Red-scored dimension with real weight
    # pulls the whole project to at least Amber, regardless of composite math.
    # (A perfect composite average can hide one severe problem.)
    if overall != "Red":
        reds = [n for n, d in dims.items() if d["score"] == 2]
        if reds:
            overall = "Amber" if overall == "Green" else overall
            if len(reds) >= 2:
                overall = "Red"

    return {
        "project_name": plan.project_name,
        "project_manager": plan.project_manager,
        "as_of": plan.as_of.isoformat(),
        "source_file": plan.source_file,
        "overall_rag": overall,
        "composite_score": round(composite, 2) if composite is not None else None,
        "dimensions": dims,
        "data_quality_warnings": plan.warnings,
        "task_counts": {
            "total": len(plan.tasks),
            "completed": sum(1 for t in plan.tasks if (t.status or "").lower() == "completed"),
            "in_progress": sum(1 for t in plan.tasks if (t.status or "").lower() == "in progress"),
            "not_started": sum(1 for t in plan.tasks if (t.status or "").lower() == "not started"),
        },
    }
