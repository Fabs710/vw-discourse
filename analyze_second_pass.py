"""
analyze_second_pass.py - re-test the confirmed parameter effects against a
measurement with less judge noise.

What this is
------------
The test-retest (Section 8.5.1) established that roughly two-thirds of the
within-condition variance on respect and position movement is the jury re-reading the
same transcript differently. Judging variance falls with the square root of the number
of scoring passes, so averaging two passes cuts the judge SD on respect from 0.050 to
0.035 and the total from 0.062 to 0.051 - about 18% less noise, bought for the price of
re-scoring frozen transcripts.

This script recomputes every within-sweep contrast on the AVERAGED score and reports it
beside the single-pass result, so the question "do the confirmed effects survive better
measurement?" gets a number rather than an assurance.

What this is NOT
----------------
It is not a replication. The runs are the same runs; the deliberations are identical.
Averaging reduces measurement error, it does not add independent evidence about the
simulation. An effect that strengthens here has been measured more precisely, not
observed a second time - and the write-up must say so.

Prerequisite
------------
    python evaluate.py <batch> --suffix _pass2 --only <the 48 confirmatory run ids>

Usage
-----
    python analyze_second_pass.py data/sensitivity_20260723_000046 --suffix _pass2
"""
import argparse, csv, itertools, json, math, re
import statistics as st
from pathlib import Path
from collections import defaultdict

DIMS = [("dqi_respect", "respect", "respect"),
        ("dqi_justif_content", "justification content", "justification_content"),
        ("dqi_justif_level", "justification level", "justification_level"),
        ("dqi_constructive", "constructive politics", "constructive_politics"),
        ("dqi_individuation", "individuation", "individuation")]


_REP = re.compile(r"_r\d+$")   # any repetition width - _r10 broke the old slice

def base_id(rid):
    rid = _REP.sub("", rid)
    return rid.split("__", 1)[0]


def exact_p(a, b):
    """Exact two-sided permutation p for equal or unequal arms."""
    obs = abs(st.mean(a) - st.mean(b))
    pool = list(a) + list(b)
    n = len(a)
    hits = tot = 0
    for idx in itertools.combinations(range(len(pool)), n):
        x = [pool[i] for i in idx]
        y = [pool[i] for i in range(len(pool)) if i not in idx]
        tot += 1
        if abs(st.mean(x) - st.mean(y)) >= obs - 1e-12:
            hits += 1
    return hits / tot


def run_scores(folder, suffix=""):
    """Mean DQI per dimension for one run, from evaluation<suffix>.json."""
    f = folder / ("evaluation%s.json" % suffix)
    if not f.exists():
        return None
    d = json.loads(f.read_text(encoding="utf-8"))
    return {k: d["dqi"].get(k) for _, _, k in DIMS}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch")
    ap.add_argument("--suffix", default="_pass2")
    a = ap.parse_args()
    root = Path(a.batch)

    p1, p2 = {}, {}
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        s2 = run_scores(folder, a.suffix)
        if s2 is None:
            continue
        s1 = run_scores(folder, "")
        if s1 is None:
            continue
        p1[folder.name], p2[folder.name] = s1, s2
    if not p1:
        raise SystemExit("no run carries both evaluation.json and evaluation%s.json.\n"
                         "Run:  python evaluate.py %s --suffix %s --only <run ids>"
                         % (a.suffix, a.batch, a.suffix))

    conds = defaultdict(list)
    for rid in p1:
        conds[base_id(rid)].append(rid)
    sweeps = defaultdict(dict)
    for c in conds:
        m = re.match(r"^(.*)_(high|low)$", c)
        if m:
            sweeps[m.group(1)][m.group(2)] = c
    sweeps = {k: v for k, v in sweeps.items() if len(v) == 2}

    print("Second-pass re-test on %d runs across %d sweep(s)\n" % (len(p1), len(sweeps)))
    print("Averaging two independent scoring passes of the SAME transcripts. This reduces")
    print("measurement error; it does not add evidence about the simulation.\n")

    out = {"batch": str(root), "suffix": a.suffix, "n_runs": len(p1), "sweeps": {}}
    hdr = "%-32s %-22s %9s %9s %9s %9s" % ("sweep", "metric", "1-pass", "2-pass", "p 1-pass", "p 2-pass")
    print(hdr); print("-" * len(hdr))
    for sweep, poles in sorted(sweeps.items()):
        out["sweeps"][sweep] = {}
        for _, label, key in DIMS:
            def vals(pole, src):
                v = [src[r][key] for r in sorted(conds[poles[pole]]) if src[r][key] is not None]
                return v
            hi1, lo1 = vals("high", p1), vals("low", p1)
            hi2 = [ (p1[r][key] + p2[r][key]) / 2 for r in sorted(conds[poles["high"]])
                    if p1[r][key] is not None and p2[r][key] is not None ]
            lo2 = [ (p1[r][key] + p2[r][key]) / 2 for r in sorted(conds[poles["low"]])
                    if p1[r][key] is not None and p2[r][key] is not None ]
            if min(len(hi1), len(lo1), len(hi2), len(lo2)) < 2:
                continue
            c1 = st.mean(hi1) - st.mean(lo1)
            c2 = st.mean(hi2) - st.mean(lo2)
            q1, q2 = exact_p(hi1, lo1), exact_p(hi2, lo2)
            sd1 = st.pstdev(hi1 + lo1)
            sd2 = st.pstdev(hi2 + lo2)
            out["sweeps"][sweep][key] = {
                "contrast_1pass": round(c1, 4), "contrast_2pass": round(c2, 4),
                "p_1pass": round(q1, 4), "p_2pass": round(q2, 4),
                "pooled_sd_1pass": round(sd1, 4), "pooled_sd_2pass": round(sd2, 4),
                "noise_reduction": round(1 - sd2 / sd1, 3) if sd1 else None,
                "verdict": ("holds" if q2 <= 0.05 and q1 <= 0.05 else
                            "gained" if q2 <= 0.05 < q1 else
                            "lost" if q1 <= 0.05 < q2 else "not significant either way")}
            mark = ""
            if q1 <= 0.05 or q2 <= 0.05:
                mark = {"holds": "  HOLDS", "gained": "  GAINED", "lost": "  LOST"}.get(
                    out["sweeps"][sweep][key]["verdict"], "")
            print("%-32s %-22s %+9.4f %+9.4f %9.4f %9.4f%s"
                  % (sweep[:32], label, c1, c2, q1, q2, mark))

    # how much noise did the second pass actually remove?
    reds = [v["noise_reduction"] for s in out["sweeps"].values() for v in s.values()
            if v["noise_reduction"] is not None]
    if reds:
        print("\nPooled SD change from averaging two passes: median %.1f%% (expected ~18%% on respect)"
              % (100 * st.median(reds)))
    print("\nVerdicts: HOLDS = significant under both measurements. GAINED = significant only")
    print("after averaging, i.e. the single pass was too noisy to resolve it. LOST = significant")
    print("only before, which would mean the single-pass result rested on judging noise.")

    dest = root / ("second_pass_analysis%s.json" % a.suffix)
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\nwritten: %s" % dest)
    print("index.csv and the reported scores are untouched.")


if __name__ == "__main__":
    main()
