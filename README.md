# Project Health Reporting Agent

Automated RAG (Red/Amber/Green) status reporting for Professional Services
projects -- reads a project plan export, scores five health dimensions,
writes a plain-English reasoning paragraph, and rolls everything up into a
monthly executive deck. Built so a non-technical PM or leader can run it
from the command line with zero setup beyond `pip install`.

## What's in here

```
agent/                  Core Python package (parser, scoring, narrative, CLI)
data/                   Input project plans
  Project_Plan_B.xlsx          <- the real file provided with this assignment
  Project_Plan_C_Sample.xlsx   <- SYNTHETIC, healthy project (for portfolio demo)
  Project_Plan_D_Sample.xlsx   <- SYNTHETIC, at-risk project (for portfolio demo)
  make_synthetic_samples.py    <- script that generated the two synthetic files
outputs/weekly/          Generated JSON + Markdown reports (3 simulated weeks x 3 projects)
presentation/            Script that builds the monthly executive .pptx from outputs/weekly
.github/workflows/       GitHub Actions workflow to run the agent weekly on a schedule
RAG_Methodology.md        One-page scoring methodology (Phase 1 deliverable)
```

## Why three projects, and why three dates, when only one file was provided?

Only `Project_Plan_B.xlsx` is real. Phase 3 asks for *trend* analysis across
a portfolio, which needs more than one project to be meaningful, so I
generated two clearly-labeled synthetic sample plans (`_Sample` suffix, and
called out again in the Summary tab and everywhere they're referenced) using
the same column schema as the real file -- one representative of a healthy
project, one of a deteriorating one.

I also ran the agent with three different `--as-of` dates against the same
three files, two weeks apart, to simulate three weekly runs without
fabricating different underlying task data. In production this isn't
needed -- each real weekly run naturally produces a new snapshot as the
underlying plan changes.

**To use this for real:** drop your real project plan `.xlsx` files into
`data/`, delete the two `_Sample` files, and run the agent normally each
week -- the outputs directory will accumulate genuine week-over-week history
on its own.

## Quick start

```bash
pip install -r requirements.txt

# Run on one file
python -m agent.run_agent data/Project_Plan_B.xlsx

# Run on everything in data/
python -m agent.run_agent "data/*.xlsx" --outdir outputs/weekly

# Backdate a run (for demos / backfilling history)
python -m agent.run_agent data/Project_Plan_B.xlsx --as-of 2026-06-18
```

Each run writes, per project, both:
- `outputs/weekly/<Project Name>_<date>.json` -- structured result, meant for
  feeding the presentation builder or a BI tool
- `outputs/weekly/<Project Name>_<date>.md` -- a human-readable report

### Optional: LLM-written narratives

By default the agent writes its plain-English reasoning with a rule-based
template built directly from the same evidence used to compute the score
(reliable, deterministic, no API key needed -- this is what runs in CI).

If you export `ANTHROPIC_API_KEY`, the agent instead asks Claude to turn the
same structured evidence into a tighter, more natural paragraph. The RAG math
is never delegated to the model -- it only rewrites the evidence that the
rule engine already produced, and falls back to the template automatically
if the API call fails for any reason.

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python -m agent.run_agent data/Project_Plan_B.xlsx
```

### Running on a weekly schedule

`.github/workflows/weekly-report.yml` runs the agent every Monday via GitHub
Actions and commits the new reports back to the repo. Add `ANTHROPIC_API_KEY`
as a repo secret if you want LLM narratives in the scheduled run; otherwise
leave it unset and it'll use the rule-based narrative automatically. A cron
job or Task Scheduler entry calling the same CLI command works identically
outside of GitHub.

### Building the monthly executive presentation

```bash
cd presentation
npm install                 # installs pptxgenjs (only needed once)
python3 aggregate.py        # reads ../outputs/weekly/*.json -> portfolio_summary.json
node build_deck.js          # writes Monthly_Executive_Update.pptx
```

## Design decisions

**Why rules first, LLM second (not the other way around)?** A RAG status
feeding client-facing reporting needs to be reproducible and defensible --
the same input should always produce the same status. All scoring and
thresholding is deterministic Python in `agent/rag_engine.py`. The LLM is
used *only* as a writer to phrase the already-computed evidence more
naturally, never as the judge of status. This also means the agent works
identically with or without an API key, which matters for a scheduled CI job.

**Why "Unknown" instead of guessing when data is missing?** Budget and
stakeholder sentiment are not present in the standard task-plan export this
assignment provided. Silently defaulting them to Green would flatter every
project; guessing a color from nothing would be dishonest. The agent reports
them as excluded and says so, so a reviewer knows exactly what the RAG status
is (and isn't) accounting for. See `RAG_Methodology.md` for the full list of
assumptions.

**Why an escalation override on top of a weighted average?** A weighted
composite can average out one severe, single-dimension problem (e.g.
milestones fine, budget on fire) into a falsely comfortable Amber. Any single
Red-scored dimension puts a floor under the overall status.

**Why column aliasing instead of hardcoded header names?** Real PM tool
exports (Smartsheet, MS Project, Asana, Jira) don't share one schema. Column
aliases live in `agent/config.py` so onboarding a new client's export format
is a config change, not a code change.

**What "handles messy data gracefully" means concretely here:** the parser
(`agent/parser.py`) treats `#UNPARSEABLE`, blank cells, wrong types, and
missing columns as "signal unavailable," never as a crash -- every data
problem becomes a line in `data_quality_warnings` in the output instead of an
exception. This was tested directly against the real file's own
`#UNPARSEABLE` cells and empty columns (Priority, Owner, Area,
Phase/Milestone were all completely blank in the provided export).

## Known limitations (see also RAG_Methodology.md)
- Sentiment scoring is a keyword proxy on free-text comments, not real NLP.
- Budget scoring requires a separate cost feed; it's stubbed and ready to
  wire in but not exercised on the real file (no cost data was provided).
- Thresholds are a starting point, meant to be retuned per practice/client.
