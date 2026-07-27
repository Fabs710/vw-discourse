"""
compare_batches.py - compare one condition across two batches.

Why this exists
---------------
Three checks in this study compare runs that cannot live in the same batch, because
they differ in a DESIGN CONSTANT rather than in a stakeholder parameter:

  * the round-cap robustness check   (4 rounds vs 6 rounds)
  * the cross-model comparison       (gpt-5.4-mini vs claude-sonnet-5)
  * any future session drift check   (same config, different day)

Pooling those into one batch index would be wrong - the runner tags their ids
(`main__r6`, `main__m-claudesonnet`) precisely so they cannot be pooled by accident -
so the comparison has to be made across batches, which is what this does.

Inference is the same exact two-sided permutation test used everywhere else in the
study, with the attainable floor stated explicitly: 2 / C(nA+nB, nA). At three runs
per side that floor is 0.10, so a round-cap or cross-model check at R = 3 can show a
direction and a magnitude but cannot reach conventional significance. That is a
property of the design and is printed with the result rather than left implicit.

Usage:
    python compare_batches.py BATCH_A COND_A BATCH_B COND_B [--label-a X --label-b Y]

Example (round cap):
    python compare_batches.py data/sensitivity_20260723_000046 main \\
                              data/sensitivity_<new> main__r6 \\
                              --label-a "4 rounds" --label-b "6 rounds"
"""
import argparse, csv, itertools, json, math, re
import statistics as st
from pathlib import Path
from collections import defaultdict

_REP = re.compile(r"_r\d+$")

METRICS = [
    ("dqi_respect",           "respect"),
    ("dqi_justif_content",    "justification content"),
    ("dqi_justif_level",      "justification level"),
    ("dqi_constructive",      "constructive politics"),
    ("dqi_individuation",     "individuation"),
    ("position_move",         "position movement"),
    ("red_line_declarations", "red-line declarations"),
    ("transcript_chars",      "transcript length"),
    ("rounds",                "rounds completed"),
    ("experts",               "experts summoned"),
    ("tokens",                "total tokens"),
    ("cost_usd",              "generation cost"),
]


def base_id(rid):
    return _REP.sub("", rid)


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load(batch, cond):
    rows = list(csv.DictReader(open(Path(batch) / "index.csv", encoding="utf-8")))
    sel = [r for r in rows if base_id(r["run_id"]) == cond]
    if not sel:
        raise SystemExit("condition %r not found in %s. Available: %s"
                         % (cond, batch, sorted({base_id(r["run_id"]) for r in rows})))
    return sel


def exact_p(a, b):
    """Exact two-sided permutation p. Works for unequal group sizes."""
    obs = abs(st.mean(a) - st.mean(b))
    pool = list(a) + list(b)
    n = len(a)
    hits = total = 0
    for idx in itertools.combinations(range(len(pool)), n):
        x = [pool[i] for i in idx]
        y = [pool[i] for i in range(len(pool)) if i not in idx]
        total += 1
        if abs(st.mean(x) - st.mean(y)) >= obs - 1e-12:
            hits += 1
    return hits / total


def welch_t(a, b):
    if len(a) < 2 or len(b) < 2:
        return None
    se = math.sqrt(st.variance(a) / len(a) + st.variance(b) / len(b))
    return (st.mean(b) - st.mean(a)) / se if se else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch_a"); ap.add_argument("cond_a")
    ap.add_argument("batch_b"); ap.add_argument("cond_b")
    ap.add_argument("--label-a", default=""); ap.add_argument("--label-b", default="")
    ap.add_argument("--out", default="", help="write JSON here (default: alongside batch B)")
    a = ap.parse_args()

    A, B = load(a.batch_a, a.cond_a), load(a.batch_b, a.cond_b)
    la = a.label_a or a.cond_a
    lb = a.label_b or a.cond_b
    # Attainable floor of the two-sided exact permutation test.
    # Equal group sizes: the observed assignment AND its label-swapped complement are
    # both enumerated and give the same |mean difference|, so the minimum is 2 hits.
    # Unequal group sizes: the complement is not a group of the same size, so it is not
    # in the enumeration and the minimum is 1 hit. Using 2/C(.) for unequal groups
    # overstates the floor by a factor of two and can make a real result look unreachable.
    floor = (2 if len(A) == len(B) else 1) / math.comb(len(A) + len(B), len(A))

    print("Comparing %s (n=%d) against %s (n=%d)" % (la, len(A), lb, len(B)))
    print("Exact permutation floor for this pair: p = %.4f%s\n"
          % (floor, "  -> significance at 0.05 is NOT attainable" if floor > 0.05 else ""))

    # provenance: these should differ only in the design constant under test
    def prov(rows, batch):
        # run_folder is not written consistently across batches: older ones store it
        # relative to data/ with forward slashes, newer ones store it from the project
        # root with backslashes. Try every plausible reading rather than silently
        # reporting an empty provenance, which is what made the round-cap comparison
        # print "provenance A: {}".
        out = {}
        for r in rows[:1]:
            raw = (r.get("run_folder") or "").replace("\\", "/").strip()
            cands = []
            if raw:
                cands += [Path(raw), Path("data") / raw]
            cands.append(Path(batch) / r["run_id"])
            for p in cands:
                s = p / "run_summary.json"
                if s.exists():
                    d = json.loads(s.read_text(encoding="utf-8"))
                    out = {"model": d["model"].get("resolved"), "seed": d["model"].get("seed"),
                           "rounds": d.get("rounds_completed")}
                    break
        return out
    pa, pb = prov(A, a.batch_a), prov(B, a.batch_b)
    print("provenance A: %s" % pa)
    print("provenance B: %s\n" % pb)
    if pa and pb:
        diffs = [k for k in pa if pa[k] != pb.get(k)]
        print("differs on: %s\n" % (", ".join(diffs) if diffs else "nothing - check you compared the right things"))

    rows_out = []
    hdr = "%-24s %12s %12s %11s %8s %9s" % ("metric", la[:12], lb[:12], "delta", "Welch t", "p exact")
    print(hdr); print("-" * len(hdr))
    for m, lab in METRICS:
        x = [fnum(r.get(m)) for r in A if fnum(r.get(m)) is not None]
        y = [fnum(r.get(m)) for r in B if fnum(r.get(m)) is not None]
        if len(x) < 2 or len(y) < 2:
            continue
        d = st.mean(y) - st.mean(x)
        t = welch_t(x, y)
        p = exact_p(x, y)
        rows_out.append({"metric": m, "label": lab, "a_mean": round(st.mean(x), 4),
                         "b_mean": round(st.mean(y), 4), "delta": round(d, 4),
                         "welch_t": round(t, 2) if t is not None else None,
                         "p_exact": round(p, 4), "n_a": len(x), "n_b": len(y)})
        big = abs(d) > 1000
        fmt = "%-24s %12.0f %12.0f %+11.0f %8s %9.4f" if big else "%-24s %12.4f %12.4f %+11.4f %8s %9.4f"
        print(fmt % (lab, st.mean(x), st.mean(y), d, ("%+.2f" % t) if t is not None else "-", p))

    out = {"a": {"batch": a.batch_a, "condition": a.cond_a, "label": la, "n": len(A), "provenance": pa},
           "b": {"batch": a.batch_b, "condition": a.cond_b, "label": lb, "n": len(B), "provenance": pb},
           "p_floor": round(floor, 5),
           "significance_attainable_at_05": floor <= 0.05,
           "comparisons": rows_out}
    dest = Path(a.out) if a.out else Path(a.batch_b) / ("comparison_%s_vs_%s.json" % (a.cond_a, a.cond_b))
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\nwritten: %s" % dest)


if __name__ == "__main__":
    main()
