"""
analyze_audit_judge.py - SCOPES B and C. Compare an independent audit judge against
the frozen two-model jury on runs both have scored.

The audit judge is run by evaluate.py with --suffix, so its scores land in
evaluation<SUFFIX>.json and the reported evaluation.json is never touched. This
script reads both and answers the two questions the audit exists to answer:

  SCOPE B - the cross-model batch. The jury is OpenAI + Anthropic and the two
  generators are OpenAI and Anthropic, so in Section 9.6 every judge has a family
  stake in one side of the comparison. An audit judge from a third lab has none.
  If it also scores the Sonnet runs higher on respect, the gap reported in 9.6
  cannot be a judge-family artefact under any reading.

  SCOPE C - the dead-item finding. Section 9.5.6 claims that three of five DQI items
  carried no variance because the CASE does not exercise them, not because the two
  raters share a convention. That claim currently rests on argument. If an
  independent rater also puts individuation and justification level at ceiling on the
  same contributions, it becomes a measurement.

Usage
-----
    python analyze_audit_judge.py <batch> --suffix _audit_gemini
    python analyze_audit_judge.py data/sensitivity_20260726_172041 --suffix _audit_gemini
"""
import argparse, json, glob, itertools
import statistics as st
from pathlib import Path

DIMS = ["justification_level", "justification_content", "respect",
        "constructive_politics", "individuation"]


def weighted_kappa(a, b, k=3):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(pairs) < 2:
        return None
    n = len(pairs)
    obs = [[0] * k for _ in range(k)]
    for x, y in pairs:
        xi, yi = int(round(x)), int(round(y))
        if 0 <= xi < k and 0 <= yi < k:
            obs[xi][yi] += 1
    ra = [sum(obs[i]) for i in range(k)]
    rb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = (i - j) ** 2
            num += w * obs[i][j]
            den += w * ra[i] * rb[j] / n
    return None if den == 0 else round(1 - num / den, 3)


def load(batch, suffix):
    """Return {rater_label: {dim: [scores aligned by contribution]}} plus the run list."""
    inc0, inc1, aud = {d: [] for d in DIMS}, {d: [] for d in DIMS}, {d: [] for d in DIMS}
    runs = []
    for folder in sorted(p for p in Path(batch).iterdir() if p.is_dir()):
        f1, f2 = folder / "evaluation.json", folder / ("evaluation%s.json" % suffix)
        if not (f1.exists() and f2.exists()):
            continue
        a = json.loads(f1.read_text(encoding="utf-8"))
        b = json.loads(f2.read_text(encoding="utf-8"))
        ca, cb = a.get("contribution_scores", []), b.get("contribution_scores", [])
        if len(ca) != len(cb):
            print("  ! %s: %d scored contributions vs %d in the audit pass - skipped"
                  % (folder.name, len(ca), len(cb)))
            continue
        runs.append(folder.name)
        for ra, rb in zip(ca, cb):
            ja, jb = ra.get("judges", []), rb.get("judges", [])
            if len(ja) < 2 or len(jb) < 1:
                continue
            for d in DIMS:
                inc0[d].append(ja[0].get(d))
                inc1[d].append(ja[1].get(d))
                aud[d].append(jb[0].get(d))
    return inc0, inc1, aud, runs


def mean(v):
    x = [s for s in v if s is not None]
    return st.mean(x) if x else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch")
    ap.add_argument("--suffix", default="_audit_gemini")
    ap.add_argument("--label", default="audit judge")
    a = ap.parse_args()

    inc0, inc1, aud, runs = load(a.batch, a.suffix)
    if not runs:
        raise SystemExit("no runs carry both evaluation.json and evaluation%s.json. Run:\n"
                         "  python evaluate.py %s --judges <model> --suffix %s"
                         % (a.suffix, a.batch, a.suffix))
    n = len(aud["respect"])
    print("Audit comparison on %d run(s), %d contribution-level records\n" % (len(runs), n))

    # ---- 1. level: does the audit judge score higher or lower overall? ----
    hdr = "%-24s %11s %11s %11s %13s" % ("dimension", "judge 1", "judge 2", a.label[:11], "audit - jury")
    print(hdr); print("-" * len(hdr))
    out = {"batch": a.batch, "suffix": a.suffix, "n_runs": len(runs), "n_records": n, "dimensions": {}}
    for d in DIMS:
        m0, m1, ma = mean(inc0[d]), mean(inc1[d]), mean(aud[d])
        jury = None if (m0 is None or m1 is None) else (m0 + m1) / 2
        delta = None if (ma is None or jury is None) else ma - jury
        out["dimensions"][d] = {"judge1": m0, "judge2": m1, "audit": ma,
                                "jury_mean": jury, "audit_minus_jury": delta}
        print("%-24s %11s %11s %11s %13s" % (
            d,
            "-" if m0 is None else "%.3f" % m0,
            "-" if m1 is None else "%.3f" % m1,
            "-" if ma is None else "%.3f" % ma,
            "-" if delta is None else "%+.3f" % delta))

    # ---- 2. agreement: kappa of the audit judge with each incumbent ----
    print("\n%-24s %12s %12s %12s" % ("dimension", "k(aud,j1)", "k(aud,j2)", "k(j1,j2)"))
    print("-" * 64)
    for d in DIMS:
        k01 = weighted_kappa(inc0[d], inc1[d])
        ka0 = weighted_kappa(aud[d], inc0[d])
        ka1 = weighted_kappa(aud[d], inc1[d])
        out["dimensions"][d].update({"kappa_audit_j1": ka0, "kappa_audit_j2": ka1,
                                     "kappa_j1_j2": k01})
        f = lambda v: "-" if v is None else "%.3f" % v
        print("%-24s %12s %12s %12s" % (d, f(ka0), f(ka1), f(k01)))
    print("\nA judge that sits no further from each incumbent than they sit from each other is")
    print("applying a comparable standard. One that sits much further is measuring something else.")

    # ---- 3. SCOPE C: does the ceiling replicate on an independent rater? ----
    print("\nCeiling check - the Section 9.5.6 claim that three items are dead because the CASE")
    print("does not exercise them, not because the two raters share a convention:\n")
    print("%-24s %14s %14s %14s" % ("dimension", "jury SD", "audit SD", "audit % at 2"))
    print("-" * 70)
    for d in DIMS:
        jury_vals = [x for pair in zip(inc0[d], inc1[d]) for x in pair if x is not None]
        aud_vals = [x for x in aud[d] if x is not None]
        sd_j = st.pstdev(jury_vals) if len(jury_vals) > 1 else None
        sd_a = st.pstdev(aud_vals) if len(aud_vals) > 1 else None
        at2 = (sum(1 for x in aud_vals if int(round(x)) == 2) / len(aud_vals)) if aud_vals else None
        out["dimensions"][d].update({"jury_sd": sd_j, "audit_sd": sd_a, "audit_share_at_ceiling": at2})
        print("%-24s %14s %14s %14s" % (
            d,
            "-" if sd_j is None else "%.3f" % sd_j,
            "-" if sd_a is None else "%.3f" % sd_a,
            "-" if at2 is None else "%.0f%%" % (100 * at2)))

    # ---- 4. USABLE OUTPUT: the failure mode that matters for an open-weight judge ----
    # parse_json returns {} when a judge produces something that is not valid JSON, and
    # the resulting score is silently None. On the incumbent models that essentially
    # never happens; on a smaller open-weight model it can happen often enough to leave a
    # quietly biased subsample. Report it rather than discovering it in the numbers.
    print("\nUsable-output check - how often did each rater return a parseable score?\n")
    print("%-24s %14s %14s %14s" % ("dimension", "judge 1", "judge 2", a.label[:14]))
    print("-" * 70)
    worst = 1.0
    for d in DIMS:
        r0 = sum(1 for x in inc0[d] if x is not None) / max(1, len(inc0[d]))
        r1 = sum(1 for x in inc1[d] if x is not None) / max(1, len(inc1[d]))
        ra = sum(1 for x in aud[d] if x is not None) / max(1, len(aud[d]))
        worst = min(worst, ra)
        out["dimensions"][d].update({"usable_j1": round(r0, 3), "usable_j2": round(r1, 3),
                                     "usable_audit": round(ra, 3)})
        print("%-24s %13.0f%% %13.0f%% %13.0f%%" % (d, 100 * r0, 100 * r1, 100 * ra))
    out["audit_min_usable_rate"] = round(worst, 3)
    if worst < 0.95:
        print("\n  WARNING: the audit judge returned unparseable output on more than 5% of records for at")
        print("  least one dimension. Treat its scores as a trial, not a measurement, and say so in 8.4.")
    else:
        print("\n  Output was parseable throughout; the comparison rests on a complete set of records.")

    dest = Path(a.batch) / ("audit_judge_analysis%s.json" % a.suffix)
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\nwritten: %s" % dest)
    print("The reported jury scores in evaluation.json and index.csv are untouched.")


if __name__ == "__main__":
    main()
