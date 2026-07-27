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
             "dqi_respect", "dqi_constructive", "dqi_individuation", "kappa_mean",
             "eval_cost_usd", "eval_calls"]

def build_judges(spec, dry):
    """One client per model in `spec`. In dry mode, one STUB per model.

    --dry used to return two stubs regardless of what --judges asked for, which made a
    dry run of a single-judge audit pass silently exercise the two-judge path instead:
    the rehearsal produced twice the calls and a populated kappa block, neither of which
    the live command would produce. A dry run has to have the same shape as the real one
    or it is not a rehearsal.
    """
    models = [m.strip() for m in spec.split(",") if m.strip()]
    if dry:
        return [StubJudge("stub_%s" % m, i) for i, m in enumerate(models)] or [StubJudge("stubA", 0)]
    from src.utils.llm import LLMClient
    if len(models) < 2:
        print("NOTE: a single judge - inter-judge agreement is unavailable by construction. "
              "Correct for an independent audit pass; wrong for the reported jury.")
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
        "eval_cost_usd": (prof.get("judging_cost") or {}).get("cost_usd"),
        "eval_calls": (prof.get("judging_cost") or {}).get("total_calls"),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="a sensitivity_<ts> folder or a single run folder")
    ap.add_argument("--dry", action="store_true", help="stub judges, no API")
    ap.add_argument("--judges", default="gpt-5.4-mini,claude-sonnet-5", help="comma list of judge models")
    ap.add_argument("--reference", default="", help="path to a reference-outcome file: score fidelity claims instead of the DQI")
    ap.add_argument("--skip-evaluated", action="store_true", help="skip run folders that already contain evaluation.json")
    ap.add_argument("--suffix", default="",
                    help="write evaluation<SUFFIX>.json instead of evaluation.json and DO NOT touch index.csv. "
                         "Used for the judge test-retest: re-scoring the same transcripts must never overwrite "
                         "the scores the results are built on.")
    ap.add_argument("--limit", type=int, default=0,
                    help="score at most N run folders. NOTE: this takes a contiguous alphabetical "
                         "PREFIX, so on a batch sorted by condition name it draws every run from the "
                         "first one or two conditions. Fine for a smoke test, wrong for a sample "
                         "meant to represent the corpus - use --only for that.")
    ap.add_argument("--only", default="",
                    help="comma list of run ids to score, e.g. main,order_random_r2,belief_high_r4. "
                         "Use this to draw a stratified test-retest sample across conditions rather "
                         "than an alphabetical prefix.")
    a = ap.parse_args()
    judges = build_judges(a.judges, a.dry)
    folders = run_folders(a.target)
    if a.only:
        want = [s.strip() for s in a.only.split(",") if s.strip()]
        by_name = {f.name: f for f in folders}
        missing = [w for w in want if w not in by_name]
        if missing:
            raise SystemExit("run id(s) not found in %s: %s" % (a.target, ", ".join(missing)))
        folders = [by_name[w] for w in want]
    if a.limit:
        folders = folders[:a.limit]
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
            jc = (out.get("judging_cost") or {}).get("cost_usd")
            print("  %-24s fidelity=%s kappa=%s cost=%s\n    %s" % (
                rf.name, out["fidelity_mean"], out["inter_judge_kappa"],
                ("$%.4f" % jc) if jc is not None else "n/a", prof))
        return
    print("Evaluating %d run(s) with %d judge(s)%s" % (len(folders), len(judges), " [DRY]" if a.dry else ""))
    evals = {}
    batch_cost, batch_calls, unpriced = 0.0, 0, False
    for rf in folders:
        prof = evaluate_run(str(rf), judges)
        jc = prof.get("judging_cost") or {}
        batch_calls += jc.get("total_calls") or 0
        if jc.get("cost_usd") is None:
            unpriced = True
        else:
            batch_cost += jc["cost_usd"]
        (rf / ("evaluation%s.json" % a.suffix)).write_text(json.dumps(prof, indent=2, ensure_ascii=False),
                                                           encoding="utf-8")
        evals[rf.name] = flatten(prof)
        print("  %-22s agreement=%s pos_move=%s dqi[justif=%s respect=%s constr=%s indiv=%s] kappa=%s $%s (run total $%.2f)" % (
            rf.name, prof["outcome"]["agreement"], prof["outcome"]["position_move_mean"],
            prof["dqi"]["justification_level"], prof["dqi"]["respect"],
            prof["dqi"]["constructive_politics"], prof["dqi"]["individuation"],
            prof.get("inter_judge_kappa", {}).get("mean"),
            ("%.4f" % jc["cost_usd"]) if jc.get("cost_usd") is not None else "n/a", batch_cost))
    print("judging cost: %s over %d calls" % (
        ("unpriced model present - see evaluation.json" if unpriced else "$%.2f" % batch_cost), batch_calls))
    idx = Path(a.target) / "index.csv"
    if a.suffix:
        print("suffix mode: index.csv left untouched (scores written to evaluation%s.json)" % a.suffix)
        return
    if idx.exists():
        rows = list(csv.DictReader(open(idx, encoding="utf-8")))
        for r in rows:
            e = evals.get(r.get("run_id", ""))
            if e is None:
                continue                      # not evaluated in this invocation: leave row untouched
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
