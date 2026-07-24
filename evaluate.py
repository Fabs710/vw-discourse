"""
evaluate.py - score completed runs with the adapted DQI + outcome measures.

Reads a sensitivity_<ts> folder (or a single run folder), scores each run with a
two-judge jury, writes a per-run evaluation.json, and merges the evaluation
columns into index.csv.

Usage:
    python evaluate.py data/sensitivity_20260101_120000 --dry        # stub judges, no API
    python evaluate.py data/sensitivity_20260101_120000 --judges gpt-5.4-mini,claude-sonnet-5
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from src.evaluation.core import evaluate_run, StubJudge

EVAL_COLS = ["agreement", "position_move", "dqi_justif_level", "dqi_justif_content",
             "dqi_respect", "dqi_constructive", "dqi_individuation", "kappa_mean"]

def build_judges(spec, dry):
    if dry:
        return [StubJudge("stubA", 0), StubJudge("stubB", 1)]
    from src.utils.llm import LLMClient
    models = [m.strip() for m in spec.split(",") if m.strip()]
    if len(models) < 2:
        print("WARNING: fewer than two judge families; inter-judge agreement will be unavailable.")
    return [LLMClient(m, 0.0, 20260714, 4096) for m in models]

def run_folders(target):
    p = Path(target)
    if (p / "run_summary.json").exists():
        return [p]
    return sorted([d for d in p.iterdir() if d.is_dir() and (d / "run_summary.json").exists()])

def flatten(prof):
    o, d = prof["outcome"], prof["dqi"]
    k = prof.get("inter_judge_kappa", {})
    return {
        "agreement": o.get("agreement"),
        "position_move": o.get("position_move_mean"),
        "dqi_justif_level": d.get("justification_level"),
        "dqi_justif_content": d.get("justification_content"),
        "dqi_respect": d.get("respect"),
        "dqi_constructive": d.get("constructive_politics"),
        "dqi_individuation": d.get("individuation"),
        "kappa_mean": k.get("mean"),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="a sensitivity_<ts> folder or a single run folder")
    ap.add_argument("--dry", action="store_true", help="stub judges, no API")
    ap.add_argument("--judges", default="gpt-5.4-mini,claude-sonnet-5", help="comma list of judge models")
    ap.add_argument("--reference", default="", help="path to a reference-outcome file: score fidelity claims instead of the DQI")
    ap.add_argument("--skip-evaluated", action="store_true", help="skip run folders that already contain evaluation.json")
    a = ap.parse_args()
    judges = build_judges(a.judges, a.dry)
    folders = run_folders(a.target)
    if a.skip_evaluated:
        before = len(folders)
        folders = [f for f in folders if not (f / "evaluation.json").exists()]
        print("skipping %d already-evaluated run(s)" % (before - len(folders)))
    if a.reference:
        from src.evaluation.reference import score_validation_run
        print("Reference-based validation of %d run(s) with %d judge(s)%s" % (len(folders), len(judges), " [DRY]" if a.dry else ""))
        for rf in folders:
            out = score_validation_run(str(rf), judges, a.reference)
            prof = " ".join("%s=%s" % (k, v) for k, v in out["profile"].items())
            print("  %-24s fidelity=%s kappa=%s\n    %s" % (rf.name, out["fidelity_mean"], out["inter_judge_kappa"], prof))
        return
    print("Evaluating %d run(s) with %d judge(s)%s" % (len(folders), len(judges), " [DRY]" if a.dry else ""))
    evals = {}
    for rf in folders:
        prof = evaluate_run(str(rf), judges)
        (rf / "evaluation.json").write_text(json.dumps(prof, indent=2, ensure_ascii=False), encoding="utf-8")
        evals[rf.name] = flatten(prof)
        print("  %-22s agreement=%s pos_move=%s dqi[justif=%s respect=%s constr=%s indiv=%s] kappa=%s" % (
            rf.name, prof["outcome"]["agreement"], prof["outcome"]["position_move_mean"],
            prof["dqi"]["justification_level"], prof["dqi"]["respect"],
            prof["dqi"]["constructive_politics"], prof["dqi"]["individuation"],
            prof.get("inter_judge_kappa", {}).get("mean")))
    idx = Path(a.target) / "index.csv"
    if idx.exists():
        rows = list(csv.DictReader(open(idx, encoding="utf-8")))
        for r in rows:
            e = evals.get(r.get("run_id", ""), {})
            for c in EVAL_COLS:
                r[c] = e.get(c, "")
        fields = list(rows[0].keys())
        for c in EVAL_COLS:
            if c not in fields:
                fields.append(c)
        with open(idx, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
        print("index.csv updated with evaluation columns")

if __name__ == "__main__":
    main()
