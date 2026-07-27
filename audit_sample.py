"""
audit_sample.py - SCOPE A. Score the 28-item human-anchored sample on all five DQI
dimensions with any set of judges, and report each judge's agreement with the human
coding and with every other judge.

Why this is the load-bearing scope
----------------------------------
A third or fourth rater that disagrees with the incumbent jury is uninterpretable on
its own: you have three opinions and no referee. The 28-contribution sample is the
only place in this study where machine scores can be checked against a human coder,
so it is what makes the audit passes in Sections 9.5 and 9.6 readable at all. Run
this FIRST; if a candidate judge cannot track the human coding roughly as well as the
incumbents do, it has not earned a place in the other scopes and the finding is
itself reportable.

What this does NOT do
---------------------
Nothing here touches evaluation.json, index.csv or any reported score. The frozen
two-model jury of Section 8.4 is unchanged. This writes one new file.

Prerequisites
-------------
data/human_coding_key.json          the 28 sampled contributions
data/human_codes.json               the author's blind codes, if available:
                                    [{"id":"C01","justification_level":2, ...}, ...]
                                    (absent -> judge-vs-judge statistics only)

Usage
-----
    python audit_sample.py --dry                                  # stubs, no API
    python audit_sample.py --judges gemini-3.1-pro
    python audit_sample.py --judges gpt-5.4-mini,claude-sonnet-5,gemini-3.1-pro
"""
import argparse, json, itertools
import statistics as st
from pathlib import Path

import yaml

from src.evaluation.core import parse_json, dqi_messages, StubJudge, JudgeMeter
from src.utils.llm import LLMClient

DIMS = ["justification_level", "justification_content", "respect",
        "constructive_politics", "individuation"]
BATCH = Path("data/sensitivity_20260723_000046")

# The audit judge must receive the IDENTICAL prompt the frozen jury received - the same
# system message, the same codebook, the same rationale-first instruction - because the
# quantity being measured is rater disagreement, not prompt sensitivity. dqi_messages is
# therefore imported from the evaluation module rather than rebuilt here: a locally
# written prompt would drift from it the moment the codebook changed, and every
# disagreement would then be confounded with that drift. Scopes B and C route through
# evaluate.py and so use dqi_messages by construction; scope A now matches them.


def weighted_kappa(a, b, k=3):
    """Quadratic weighted kappa on a 0..k-1 ordinal scale; None if undefined."""
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


def exact_agreement(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if not pairs:
        return None
    return round(sum(1 for x, y in pairs if int(round(x)) == int(round(y))) / len(pairs), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="stub judges, no API calls")
    ap.add_argument("--judges", default="gemini-3.1-pro", help="comma list of judge models")
    ap.add_argument("--out", default="data/audit_sample_scores.json")
    a = ap.parse_args()

    names = [m.strip() for m in a.judges.split(",") if m.strip()]
    if a.dry:
        judges = [StubJudge(n, i) for i, n in enumerate(names)]
    else:
        judges = [LLMClient(n, 0.0, 20260714, 1024) for n in names]
    meter = JudgeMeter()

    key = json.loads(Path("data/human_coding_key.json").read_text(encoding="utf-8"))
    human_path = Path("data/human_codes.json")
    human = {}
    if human_path.exists():
        for rec in json.loads(human_path.read_text(encoding="utf-8")):
            human[rec["id"]] = rec
    print("Scoring %d contributions with %d judge(s)%s%s\n"
          % (len(key), len(judges), " [DRY]" if a.dry else "",
             "" if human else "  (no human codes found - judge-vs-judge only)"))

    records = []
    for e in key:
        rf = BATCH / e["cond"]
        text = (rf / "outputs" / ("round%d_%s.txt" % (e["round"], e["stakeholder"]))).read_text(encoding="utf-8")
        cfg = yaml.safe_load((rf / "config_used.yaml").read_text(encoding="utf-8"))
        role = next("%s (%s)" % (s["name"], s["role"])
                    for s in cfg["stakeholders"] if s["key"] == e["stakeholder"])
        rec = {"id": e["id"], "scores": {}}
        for name, jd in zip(names, judges):
            r = jd.call(dqi_messages(role, text), "audit_%s" % e["id"])
            if not a.dry:
                meter.record(r)
            d = parse_json(r.text)
            rec["scores"][name] = {k: (d.get(k) if isinstance(d.get(k), (int, float)) else None)
                                   for k in DIMS}
        records.append(rec)
        print("  %s  %s" % (e["id"], {n: rec["scores"][n]["respect"] for n in names}), flush=True)

    # ---- statistics -------------------------------------------------------
    raters = list(names) + (["HUMAN"] if human else [])
    def series(rater, dim):
        if rater == "HUMAN":
            return [human.get(r["id"], {}).get(dim) for r in records]
        return [r["scores"][rater][dim] for r in records]

    # ---- usable output: an open-weight judge can fail to return JSON, and parse_json
    # turns that into a silent None. Report the rate before reporting any agreement.
    print("\nUsable-output rate (parseable score returned):")
    usable = {}
    for name in names:
        got = sum(1 for r in records for d in DIMS if r["scores"][name][d] is not None)
        usable[name] = round(got / (len(records) * len(DIMS)), 3)
        flag = "" if usable[name] >= 0.95 else "   <- below 95%, treat as a trial not a measurement"
        print("   %-28s %5.0f%%%s" % (name, 100 * usable[name], flag))

    stats = {"n_items": len(records), "judges": names, "human_codes": bool(human),
             "usable_output_rate": usable, "pairs": {}}
    print("\n%-46s %8s %8s" % ("pair / dimension", "kappa", "exact"))
    print("-" * 64)
    for x, y in itertools.combinations(raters, 2):
        pair = "%s vs %s" % (x, y)
        stats["pairs"][pair] = {}
        ks = []
        for dim in DIMS:
            kap = weighted_kappa(series(x, dim), series(y, dim))
            ex = exact_agreement(series(x, dim), series(y, dim))
            stats["pairs"][pair][dim] = {"kappa": kap, "exact": ex}
            if kap is not None:
                ks.append(kap)
            print("%-46s %8s %8s" % ((pair + " / " + dim)[:46],
                                     "-" if kap is None else "%.3f" % kap,
                                     "-" if ex is None else "%.0f%%" % (100 * ex)))
        stats["pairs"][pair]["mean_kappa"] = round(st.mean(ks), 3) if ks else None
        print("%-46s %8s\n" % ((pair + " / MEAN")[:46],
                               "-" if not ks else "%.3f" % st.mean(ks)))

    if not a.dry:
        stats["judging_cost"] = meter.summary()
        print("audit cost: $%.4f over %d calls"
              % (stats["judging_cost"]["cost_usd"], stats["judging_cost"]["total_calls"]))

    out = {"scores": records, "statistics": stats}
    Path(a.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\nwritten: %s" % a.out)
    print("Nothing in evaluation.json or index.csv was modified.")


if __name__ == "__main__":
    main()
