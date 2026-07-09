# RAG Methodology -- Project Health Reporting

## Purpose
Give leadership a fast, consistent, defensible Red/Amber/Green read on every
project without waiting on a PM to write a status deck -- while still
producing a plain-English explanation of *why*, not just a color.

## The five signals

| Signal | What it measures | How it's scored |
|---|---|---|
| **Schedule** | % of active tasks past their planned end date; % of tasks self-flagged Red/Amber by the PM tool; count of overdue critical-path tasks; overall progress-vs-elapsed-time ratio (a lightweight Schedule Performance Index). | Green if all sub-checks are within tolerance. Amber if one check breaches its first threshold (e.g. >10% of tasks overdue, SPI < 0.85). Red if any check breaches its second threshold (e.g. >25% overdue, SPI < 0.65, 3+ overdue critical tasks). |
| **Milestones** | Top-level phases whose planned end date has passed while the phase is still incomplete. | Green = none late. Amber = 1 late phase. Red = 2+ late phases. |
| **Blockers** | Tasks whose dependencies are done and whose planned start date has passed, but which still haven't started; tasks explicitly marked On Hold. | Green = none stuck. Amber = 2-4 stuck tasks or any On Hold. Red = 5+ stuck tasks. |
| **Budget** | Actual spend vs. planned budget (burn rate). | Green ≤100% burn for time elapsed. Amber 100-110%. Red >110%. |
| **Stakeholder sentiment** | Risk/delay language in PM status comments (keyword proxy) -- a placeholder for a real sentiment signal (survey score, CSAT, or a proper NLP model) once that data exists. | Green <15% negative comments. Amber 15-40%. Red >40%. |

## From signals to one overall status
1. Each signal gets a score of 0 (Green), 1 (Amber), 2 (Red), or **null** if the
   underlying data isn't in the source file.
2. Overall status = weighted average of the *available* signals (Schedule and
   Milestones weighted highest; Sentiment lowest, since it's the least
   reliable proxy), mapped to Green/Amber/Red bands.
3. **Escalation override:** if any single signal is Red, the project cannot
   report as Green overall, even if the weighted average would suggest it --
   a healthy average shouldn't be allowed to hide one severe problem. Two or
   more Red signals force an overall Red.
4. Every score carries its evidence (the actual counts/percentages behind
   it), so the narrative is generated *from* the math, not invented
   separately from it.

## Assumptions and known gaps (stated plainly, not hidden)
- **Budget and stakeholder sentiment are usually not present** in a standard
  task-plan export. Rather than fabricate numbers, the agent marks these
  Unknown, excludes them from the composite, and says so in the report. If a
  finance feed or survey feed is wired in later, they activate automatically.
- **Sentiment is a keyword proxy on PM free-text comments**, not real NLP --
  it will occasionally mis-flag phrasing (e.g. "no open issues") as negative.
  It's presented as a directional signal, not a verdict.
- **"Milestone" = a top-level row in the plan's outline hierarchy** (the
  `Ancestors`/indent-level column). If a source file has no hierarchy data,
  this dimension is marked Unknown rather than guessed.
- **A task counts as "overdue"** only if it's not Completed/On Hold/Not
  Applicable and its planned end date is before the report's "as of" date.
- Thresholds (e.g. 10%/25% overdue) are a reasonable starting point calibrated
  against the sample data, not a universal constant -- they live in one config
  file (`agent/config.py`) so Professional Services can retune them per
  practice or client without touching the scoring logic.
