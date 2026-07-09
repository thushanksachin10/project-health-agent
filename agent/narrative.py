"""
Turns the structured RAG result into plain-English reasoning.

Two modes:
  1. LLM mode (default if ANTHROPIC_API_KEY is set): sends the structured
     scoring result (never raw task-level PII beyond names already in the
     plan) to Claude and asks for a tight executive-style paragraph. The
     model is instructed to use ONLY the facts in the payload -- it's a
     writer, not an analyst, so the RAG math never depends on model output.
  2. Template mode (fallback, always available, no API key needed): builds
     the same style of paragraph directly from the evidence strings already
     produced by rag_engine.py. This is what runs in CI / scheduled jobs
     unless a key is configured, and guarantees the agent works out of the box.
"""

import os
import json


def _template_narrative(result: dict) -> str:
    overall = result["overall_rag"]
    name = result["project_name"]
    dims = result["dimensions"]

    lead = {
        "Green": f"{name} is healthy and on track.",
        "Amber": f"{name} is showing early warning signs that need PM/leadership attention.",
        "Red": f"{name} is off track and needs immediate leadership intervention.",
        "Unknown": f"{name}'s health could not be fully determined from the data available.",
    }[overall]

    lines = [lead]
    for dim_name in ("schedule", "milestones", "blockers", "budget", "sentiment"):
        d = dims[dim_name]
        if d["score"] is None:
            continue
        if d["score"] == 0:
            continue  # keep the narrative focused on what's driving the status
        pretty = dim_name.replace("_", " ").capitalize()
        lines.append(f"{pretty}: {' '.join(d['evidence'])}")

    if len(lines) == 1:
        lines.append("No dimension is currently flagged Amber or Red; all tracked signals are within tolerance.")

    unknowns = [n.replace("_", " ") for n, d in dims.items() if d["score"] is None]
    if unknowns:
        lines.append(f"Note: {', '.join(unknowns)} could not be assessed (data not available in source file) and were excluded from the composite score.")

    return " ".join(lines)


def _llm_narrative(result: dict) -> str:
    import urllib.request

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    prompt = (
        "You are writing a short, plain-English project health summary for a "
        "Professional Services leadership audience. You will be given a JSON "
        "object with a RAG status and per-dimension scores/evidence for one "
        "project. Rules:\n"
        "- Use ONLY facts present in the JSON. Do not invent numbers, dates, or causes.\n"
        "- 3-5 sentences, plain English, no color-name-as-adjective cliches.\n"
        "- Lead with the overall status and the single biggest driver.\n"
        "- If a dimension is Unknown/excluded, mention it only briefly at the end.\n"
        "- No markdown, no bullet points, just a short paragraph.\n\n"
        f"DATA:\n{json.dumps(result, default=str)}"
    )

    body = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 400,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    return " ".join(text_blocks).strip()


def generate_narrative(result: dict) -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _llm_narrative(result)
        except Exception as e:
            fallback = _template_narrative(result)
            return fallback + f"\n\n[Note: LLM narrative generation failed ({e}); showing rule-based summary instead.]"
    return _template_narrative(result)
