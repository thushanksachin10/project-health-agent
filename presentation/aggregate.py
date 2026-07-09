"""
Aggregates outputs/weekly/*.json into a single portfolio_summary.json that
the deck builder (build_deck.js) consumes. This is the "monthly synthesis"
logic: instead of restating each project, it looks ACROSS projects for
trends, common failure modes, and emerging risk.
"""
import json
import glob
import os
from collections import defaultdict

WEEKLY_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "weekly")

RAG_RANK = {"Green": 0, "Amber": 1, "Red": 2, "Unknown": 0}


def load_all():
    by_project = defaultdict(list)
    for path in glob.glob(os.path.join(WEEKLY_DIR, "*.json")):
        with open(path) as f:
            r = json.load(f)
        by_project[r["project_name"]].append(r)
    for name in by_project:
        by_project[name].sort(key=lambda r: r["as_of"])
    return by_project


def main():
    by_project = load_all()
    latest_snapshot_date = max(r["as_of"] for runs in by_project.values() for r in runs)

    projects = []
    dimension_red_amber_counts = defaultdict(int)
    deteriorating = []
    improving = []
    stable_red = []

    for name, runs in by_project.items():
        latest = runs[-1]
        first = runs[0]
        trend = "flat"
        if RAG_RANK[latest["overall_rag"]] > RAG_RANK[first["overall_rag"]]:
            trend = "worsening"
            deteriorating.append(name)
        elif RAG_RANK[latest["overall_rag"]] < RAG_RANK[first["overall_rag"]]:
            trend = "improving"
            improving.append(name)
        elif latest["overall_rag"] == "Red":
            stable_red.append(name)

        for dim_name, d in latest["dimensions"].items():
            if d["score"] in (1, 2):
                dimension_red_amber_counts[dim_name] += 1

        projects.append({
            "name": name,
            "pm": latest.get("project_manager"),
            "history": [{"as_of": r["as_of"], "rag": r["overall_rag"]} for r in runs],
            "latest_rag": latest["overall_rag"],
            "trend": trend,
            "narrative": latest["narrative"],
            "dimensions": {k: {"label": v["label"], "score": v["score"]} for k, v in latest["dimensions"].items()},
            "task_counts": latest["task_counts"],
        })

    projects.sort(key=lambda p: RAG_RANK.get(p["latest_rag"], 0), reverse=True)

    rag_counts = defaultdict(int)
    for p in projects:
        rag_counts[p["latest_rag"]] += 1

    top_risk_dimension = max(dimension_red_amber_counts.items(), key=lambda kv: kv[1]) if dimension_red_amber_counts else (None, 0)

    summary = {
        "as_of": latest_snapshot_date,
        "portfolio_size": len(projects),
        "rag_counts": dict(rag_counts),
        "projects": projects,
        "deteriorating": deteriorating,
        "improving": improving,
        "stable_red": stable_red,
        "dimension_red_amber_counts": dict(dimension_red_amber_counts),
        "top_risk_dimension": top_risk_dimension[0],
    }

    out_path = os.path.join(os.path.dirname(__file__), "portfolio_summary.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print("wrote", out_path)
    print(json.dumps({k: v for k, v in summary.items() if k != "projects"}, indent=2))


if __name__ == "__main__":
    main()
