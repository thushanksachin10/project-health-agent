#!/usr/bin/env python3
"""
Project Health Reporting Agent -- CLI entry point.

Usage:
    python -m agent.run_agent data/Project_Plan_B.xlsx
    python -m agent.run_agent data/*.xlsx --outdir outputs/weekly
    python -m agent.run_agent data/Project_Plan_B.xlsx --as-of 2026-07-02

For each input file, writes:
    outputs/weekly/<Project Name>_<as_of>.json   (structured result)
    outputs/weekly/<Project Name>_<as_of>.md     (human-readable report)

Exits non-zero only on a genuinely unreadable file (bad path / not xlsx);
messy-but-readable data never crashes the run -- it's reported as a
data-quality warning inside the output instead.
"""

import argparse
import glob
import json
import os
import sys
from datetime import date, datetime

from .parser import load_project_plan
from .rag_engine import compute_rag
from .narrative import generate_narrative

RAG_EMOJI = {"Green": "\U0001F7E2", "Amber": "\U0001F7E1", "Red": "\U0001F534", "Unknown": "\u26AA"}


def render_markdown(result: dict, narrative: str) -> str:
    rag = result["overall_rag"]
    lines = []
    lines.append(f"# {result['project_name']} -- Weekly Health Report")
    lines.append("")
    lines.append(f"**Status: {RAG_EMOJI.get(rag,'')} {rag}**  |  As of {result['as_of']}  |  PM: {result.get('project_manager') or 'Unknown'}")
    lines.append("")
    lines.append("## Summary")
    lines.append(narrative)
    lines.append("")
    lines.append("## Dimension Detail")
    lines.append("")
    lines.append("| Dimension | Status | Key Evidence |")
    lines.append("|---|---|---|")
    for name, d in result["dimensions"].items():
        evid = " ".join(d["evidence"])
        lines.append(f"| {name.capitalize()} | {d['label']} | {evid} |")
    lines.append("")
    tc = result["task_counts"]
    lines.append(f"## Task Snapshot\nTotal: {tc['total']} | Completed: {tc['completed']} | In Progress: {tc['in_progress']} | Not Started: {tc['not_started']}")
    if result["data_quality_warnings"]:
        lines.append("")
        lines.append("## Data Quality Notes")
        for w in result["data_quality_warnings"]:
            lines.append(f"- {w}")
    return "\n".join(lines)


def run_one(path: str, outdir: str, as_of: date, budget_data: dict = None) -> dict:
    plan = load_project_plan(path, as_of=as_of)
    result = compute_rag(plan, budget_data=budget_data)
    narrative = generate_narrative(result)
    result["narrative"] = narrative

    os.makedirs(outdir, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in result["project_name"]).strip()
    base = f"{safe_name}_{result['as_of']}"

    json_path = os.path.join(outdir, base + ".json")
    md_path = os.path.join(outdir, base + ".md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(result, narrative))

    print(f"[{result['overall_rag']:>6}] {result['project_name']:<40} -> {md_path}")
    return result


def main():
    ap = argparse.ArgumentParser(description="Project Health Reporting Agent")
    ap.add_argument("inputs", nargs="+", help="Path(s) or glob(s) to project plan .xlsx files")
    ap.add_argument("--outdir", default="outputs/weekly", help="Output directory")
    ap.add_argument("--as-of", default=None, help="Override 'today' date, format YYYY-MM-DD (for backdated/demo runs)")
    args = ap.parse_args()

    as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date() if args.as_of else date.today()

    files = []
    for pattern in args.inputs:
        matched = glob.glob(pattern)
        files.extend(matched if matched else [pattern])

    if not files:
        print("No input files found.", file=sys.stderr)
        sys.exit(1)

    results = []
    had_error = False
    for f in files:
        try:
            results.append(run_one(f, args.outdir, as_of))
        except Exception as e:
            had_error = True
            print(f"[ ERROR ] Could not process {f}: {e}", file=sys.stderr)

    print(f"\nProcessed {len(results)}/{len(files)} file(s). Outputs in {args.outdir}/")
    sys.exit(1 if had_error and not results else 0)


if __name__ == "__main__":
    main()
