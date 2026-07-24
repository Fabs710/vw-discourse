"""
src/evaluation/reference.py - reference-based validation scoring (RQ3).

Scores a completed validation run against the documented record
(docs/reference_outcome_gm.md) on ten fidelity claims, each 0-2:
  0 = the simulation contradicts the documented record on this point
  1 = partially consistent
  2 = clearly consistent
Scored independently by each judge of the jury; per-claim profile + weighted
kappa reported. The reference text is NEVER shown to the generating agents.
"""
from __future__ import annotations
import json, re
from pathlib import Path
from src.evaluation.core import parse_json, weighted_kappa

CLAIMS = {
 "P1": "The funder (government task force) dominates the process and conditions everything on deep, fast, shared sacrifice.",
 "P2": "Management is weak and accommodating after the leadership change; it argues for the going concern and accepts previously unthinkable measures.",
 "P3": "Labour bargains hard but trades: concessions in exchange for a durable claim (equity/securities) for the retiree trust; it is not wiped out.",
 "P4": "Bondholders resist unequal treatment relative to labour's unsecured claim; the credible court threat moves them; they end with a small recovery plus upside instruments, not zero and not par.",
 "P5": "The co-funding government participates conditionally on production/footprint protection and obtains a proportionate minority position.",
 "C1": "A core conflict axis is creditors versus labour (equal-treatment fight over comparable unsecured claims).",
 "C2": "A core conflict axis is the funder versus all claimants (depth and speed of sacrifice).",
 "C3": "The consensual path fails or remains unresolved within the deadline; a court-supervised expedited process is the credible or chosen completion route.",
 "O1": "Outcome direction: government(s) end as majority owners; the labour trust becomes a large minority holder; creditors a small minority with upside instruments; original equity effectively wiped out.",
 "O2": "Outcome direction: deep operational cuts (plants/brands/dealers) are part of the deal.",
}

def _messages(reference_text, transcript, synthesis):
    sysp = ("You are a careful evaluator comparing a SIMULATED stakeholder deliberation against the "
            "DOCUMENTED historical record of the real episode. For each claim, judge whether the "
            "simulation is consistent with the record: 0 = contradicts it, 1 = partially consistent, "
            "2 = clearly consistent. Judge the simulation's behaviour and outcome, not its wording. "
            "Return ONLY valid JSON of the form "
            '{"P1":{"score":0,"rationale":"one SHORT sentence"}, ...} for ALL claim ids. Keep every rationale under 20 words.')
    claims = "\n".join(f"{k}: {v}" for k, v in CLAIMS.items())
    user = ("DOCUMENTED RECORD:\n%s\n\n=== SIMULATED TRANSCRIPT (may be trimmed) ===\n%s\n\n"
            "=== SIMULATED FINAL SYNTHESIS ===\n%s\n\n=== CLAIMS TO SCORE ===\n%s"
            % (reference_text[:8000], transcript[:220000], synthesis[:16000], claims))
    return [{"role": "system", "content": sysp}, {"role": "user", "content": user}]

def score_validation_run(run_folder, judges, reference_path):
    rf = Path(run_folder)
    reference_text = Path(reference_path).read_text(encoding="utf-8")
    transcript = (rf / "outputs" / "full_transcript.txt").read_text(encoding="utf-8")
    syn_f = rf / "outputs" / "final_synthesis.txt"
    synthesis = syn_f.read_text(encoding="utf-8") if syn_f.exists() else ""
    per_judge = []
    for jd in judges:
        r = jd.call(_messages(reference_text, transcript, synthesis), "reference_validation")
        d = parse_json(r.text)
        scores = {}
        for cid in CLAIMS:
            v = d.get(cid, {})
            s = v.get("score") if isinstance(v, dict) else v
            scores[cid] = {"score": s if isinstance(s, (int, float)) else None,
                           "rationale": (v.get("rationale", "") if isinstance(v, dict) else "")}
        per_judge.append(scores)
    profile = {}
    for cid in CLAIMS:
        vals = [j[cid]["score"] for j in per_judge if j[cid]["score"] is not None]
        profile[cid] = round(sum(vals) / len(vals), 2) if vals else None
    kappa = None
    if len(per_judge) >= 2:
        a = [per_judge[0][c]["score"] for c in CLAIMS]
        b = [per_judge[1][c]["score"] for c in CLAIMS]
        kappa = weighted_kappa(a, b, k=3)
    valid = [v for v in profile.values() if v is not None]
    out = {
        "run_folder": str(run_folder),
        "claims": CLAIMS,
        "per_judge": per_judge,
        "profile": profile,
        "fidelity_mean": round(sum(valid) / len(valid), 3) if valid else None,
        "inter_judge_kappa": kappa,
        "n_judges": len(judges),
    }
    (rf / "validation_scores.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
