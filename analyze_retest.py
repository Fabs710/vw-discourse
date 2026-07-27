"""
analyze_retest.py - judge test-retest: how much of the run-to-run spread is the
simulation, and how much is the scorer?

Why this matters
----------------
Every number this study reports as run-to-run variation is really the sum of two
things: the generator producing a different deliberation, and the jury scoring the
SAME deliberation differently on a second pass. Those are completely confounded in
the main results, so a sentence like "the pooled within-condition SD on respect is
0.061" cannot presently distinguish a noisy simulation from a noisy instrument -
which matters, because the screening thresholds are built out of exactly that number.

Re-scoring transcripts that already have scores separates them. Judging the same
frozen transcript twice holds the deliberation constant, so whatever differs is
judging variance alone. Subtracting it from the total gives the generation share.

  total within-condition variance  =  generation variance  +  judging variance

Because the retest re-uses frozen transcripts, it costs generation nothing.

Prerequisite
------------
    python evaluate.py <batch> --suffix _retest1 --limit 10
(--suffix writes evaluation_retest1.json and leaves index.csv and the original
evaluation.json untouched, so the results the thesis is built on cannot be disturbed.)

Usage:
    python analyze_retest.py data/sensitivity_20260723_000046 --suffix _retest1
"""
import argparse, csv, json, math, re
import statistics as st
from pathlib import Path
from collections import defaultdict

_REP = re.compile(r"_r\d+$")
DIMS = [("justification_level", "dqi_justif_level", "justification level"),
        ("justification_content", "dqi_justif_content", "justification content"),
        ("respect", "dqi_respect", "respect"),
        ("constructive_politics", "dqi_constructive", "constructive politics"),
        ("individuation", "dqi_individuation", "individuation")]


def base_id(rid):
    return _REP.sub("", rid)


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch")
    ap.add_argument("--suffix", default="_retest1")
    a = ap.parse_args()
    root = Path(a.batch)

    pairs = []          # (run_id, dim_key, original, retest)
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        f1, f2 = d / "evaluation.json", d / ("evaluation%s.json" % a.suffix)
        if not (f1.exists() and f2.exists()):
            continue
        o = json.loads(f1.read_text(encoding="utf-8"))
        r = json.loads(f2.read_text(encoding="utf-8"))
        for key, _, _ in DIMS:
            v1, v2 = o["dqi"].get(key), r["dqi"].get(key)
            if v1 is not None and v2 is not None:
                pairs.append((d.name, key, v1, v2))
        p1 = o["outcome"].get("position_move_mean"); p2 = r["outcome"].get("position_move_mean")
        if p1 is not None and p2 is not None:
            pairs.append((d.name, "position_move", p1, p2))

    if not pairs:
        raise SystemExit("no re-scored runs found. Run:  python evaluate.py %s --suffix %s --limit 10"
                         % (a.batch, a.suffix))
    runs = sorted({p[0] for p in pairs})
    print("Judge test-retest on %d re-scored run(s): %s\n" % (len(runs), ", ".join(runs)))

    # pooled within-condition SD from the main results, for the comparison
    rows = list(csv.DictReader(open(root / "index.csv", encoding="utf-8")))
    g = defaultdict(list)
    for r in rows:
        g[base_id(r["run_id"])].append(r)

    def pooled_sd(col):
        sds = []
        for c, rs in g.items():
            v = [fnum(r.get(col)) for r in rs if fnum(r.get(col)) is not None]
            if len(v) > 1:
                sds.append(st.stdev(v))
        return math.sqrt(sum(s * s for s in sds) / len(sds)) if sds else None

    out = {"batch": str(root), "suffix": a.suffix, "n_runs": len(runs), "dimensions": {}}
    hdr = "%-24s %9s %9s %11s %11s %9s" % ("dimension", "judge SD", "total SD", "judging %", "generation %", "n")
    print(hdr); print("-" * len(hdr))
    for key, col, lab in DIMS + [("position_move", "position_move", "position movement")]:
        sel = [(o, r) for (_, k, o, r) in pairs if k == key]
        if len(sel) < 2:
            continue
        diffs = [r - o for o, r in sel]
        # SD of a single measurement from paired differences: sd(diff)/sqrt(2)
        judge_sd = st.stdev(diffs) / math.sqrt(2) if len(diffs) > 1 else 0.0
        total_sd = pooled_sd(col)
        if not total_sd:
            continue
        share = min(1.0, (judge_sd ** 2) / (total_sd ** 2)) if total_sd else None
        gen_var = max(0.0, total_sd ** 2 - judge_sd ** 2)
        out["dimensions"][key] = {
            "label": lab, "judge_sd": round(judge_sd, 4), "total_within_condition_sd": round(total_sd, 4),
            "generation_sd": round(math.sqrt(gen_var), 4),
            "judging_variance_share": round(share, 3), "n_pairs": len(sel),
            "mean_abs_difference": round(st.mean([abs(d) for d in diffs]), 4),
            "mean_signed_difference": round(st.mean(diffs), 4)}
        print("%-24s %9.4f %9.4f %10.1f%% %10.1f%% %9d"
              % (lab, judge_sd, total_sd, 100 * share, 100 * (1 - share), len(sel)))

    print("\nJudging share is the fraction of within-condition VARIANCE attributable to the")
    print("scorer rather than the simulation. A high share on a measure means the screening")
    print("threshold built from it is mostly filtering judge noise, not deliberation noise.")
    signed = [out["dimensions"][k]["mean_signed_difference"] for k in out["dimensions"]]
    if signed:
        print("\nMean signed difference across dimensions: %+.4f" % st.mean(signed))
        print("(a systematic offset would indicate the jury drifts between passes rather than")
        print(" scattering around a stable value; near zero is the reassuring result)")

    dest = root / ("retest_analysis%s.json" % a.suffix)
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\nwritten: %s" % dest)


if __name__ == "__main__":
    main()
