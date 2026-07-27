"""
analyze_drill.py - the parameter-level drill-down analysis (Section 9.5).

Why this exists alongside analyze_sensitivity.py
------------------------------------------------
analyze_sensitivity.py reads every condition against the BASELINE (`main`). That is
the right reading for the layer screen, where baseline and conditions were produced
in the same batch. It is NOT a safe reading for the drill-down, for two reasons:

  1. Baseline displacement. Every perturbed condition - both poles of every sweep -
     scores higher on respect than the calibrated configuration. An effect measured
     against `main` therefore contains a constant offset that has nothing to do with
     the parameter being swept.
  2. Batch confounding. The drill conditions were produced in a later batch than
     `main`. Manipulation type (single stakeholder, moderate) and batch are perfectly
     confounded with each other, so a drill-vs-main difference cannot be attributed.

This script therefore reports the WITHIN-SWEEP CONTRAST (high minus low), in which
both arms come from the same batch and the baseline offset cancels exactly.

Inference
---------
With R = 3 per arm there are only C(6,3) = 20 distinct relabellings, so an EXACT
two-sided permutation test is cheap - and its smallest attainable p-value is 0.10.
No contrast in this design can reach conventional significance; that is a property
of the design, not of the data, and the output states it explicitly. The number of
contrasts reaching the floor is compared against the number chance alone would
produce, which is the only honest summary available at this sample size.

Usage:  python analyze_drill.py data/sensitivity_20260723_000046
"""
import json, csv, argparse, itertools, math, re
import statistics as st
from pathlib import Path
from collections import defaultdict

_REP = re.compile(r"_r\d+$")     # repetition suffix of ANY width - see base_id()

# sweep prefix -> (display name, framework layer)
SWEEPS = [
    ("mgmt_flexibility",       "Management flexibility",      "position"),
    ("igmetall_flexibility",   "IG Metall flexibility",       "position"),
    ("mgmt_dependency",        "Management dependency",       "position"),
    ("works_dependency",       "Works council dependency",    "position"),
    ("saxony_assertiveness",   "Saxony assertiveness",        "interaction"),
    ("works_cooperativeness",  "Works council cooperativeness", "interaction"),
    ("owners_social_pref",     "Owners social preference",    "motivation"),
    ("investors_power",        "Investors power",             "salience"),
    ("mgmt_relational_prior",  "Management relational prior", "belief"),
]
# All-stakeholder single-parameter sweeps (the rung between layer and drill).
PARAM_ALL = [
    ("pall_flexibility",      "Flexibility, all stakeholders",      "position"),
    ("pall_dependency",       "Dependency, all stakeholders",       "position"),
    ("pall_cooperativeness",  "Cooperativeness, all stakeholders",  "interaction"),
    ("pall_relational_prior", "Relational prior, all stakeholders", "belief"),
    ("pall_risk_preference",  "Risk preference, all stakeholders",  "motivation"),
]
LAYERS = [
    ("layer_position",    "Position layer (all stakeholders)",    "position"),
    ("layer_interaction", "Interaction layer (all stakeholders)", "interaction"),
    ("layer_motivation",  "Motivation layer (all stakeholders)",  "motivation"),
    ("layer_salience",    "Salience layer (all stakeholders)",    "salience"),
]
METRICS = [
    ("dqi_justif_content",  "justification content"),
    ("dqi_respect",         "respect"),
    ("position_move",       "position movement"),
    ("red_line_declarations", "red-line declarations"),
    ("transcript_chars",    "transcript length"),
]
CALIBRATED = {"main", "main_recheck", "order_reversed", "order_random"}


def base_id(run_id):
    """Condition name, with the repetition suffix and any design-constant tag removed.

    run_sensitivity.py tags runs that differ in a DESIGN CONSTANT rather than in a
    stakeholder parameter - '__m-claudesonnet' for the cross-model batch, '__r6' for
    the round-cap batch - and it places that tag BEFORE the repetition suffix:

        layer_position_high__m-claudesonnet_r3

    Stripping only '_r3' leaves 'layer_position_high__m-claudesonnet', which never
    matches the 'layer_position_high' this module builds when it pairs the poles of a
    sweep. The whole batch then yields zero contrasts and reads as a null result rather
    than as an unparsed one. No condition in an untagged batch contains '__', so
    removing the tag is a no-op there and the main-batch output is unchanged.

    The suffix is stripped by REGEX, not by a fixed-width slice. The previous version
    used run_id[:-3] guarded on run_id[-3:-1] == '_r', which handles _r1.._r9 and
    silently fails on _r10: the tenth baseline replicate formed its own singleton
    condition, so 'main' aggregated nine runs here while analyze_sensitivity.py - which
    already used the regex - aggregated ten. The two modules reported different baselines
    for the same batch (1.560 +/- 0.066 against 1.575 +/- 0.078), and because the second
    screening criterion is twice the baseline SD, the discrepancy moved that threshold
    from 0.132 to 0.156. Both modules now strip identically.
    """
    rid = _REP.sub("", run_id)
    return rid.split("__", 1)[0]


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def exact_perm_p(a, b):
    """Exact two-sided permutation p for a difference of means, equal group sizes."""
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
    ap.add_argument("batch")
    a = ap.parse_args()
    root = Path(a.batch)
    rows = list(csv.DictReader(open(root / "index.csv", encoding="utf-8")))

    g = defaultdict(list)
    for r in rows:
        g[base_id(r["run_id"])].append(r)

    def vals(cond, m):
        return [fnum(r.get(m)) for r in g.get(cond, []) if fnum(r.get(m)) is not None]

    # ---- pooled within-condition SD, and the noise band it should be compared to
    pooled = {}
    for m, _ in METRICS:
        sds = [st.stdev(v) for v in (vals(c, m) for c in g) if len(v) > 1]
        pooled[m] = math.sqrt(sum(s * s for s in sds) / len(sds)) if sds else None

    band = {}
    for m, _ in METRICS:
        mm = vals("main", m)
        if not mm:
            continue
        diffs = [abs(st.mean(vals(o, m)) - st.mean(mm)) for o in ("order_reversed", "order_random") if vals(o, m)]
        band[m] = max(diffs) if diffs else None

    diagnostics = {}
    for m, _ in METRICS:
        if pooled.get(m) and band.get(m):
            se3 = pooled[m] / math.sqrt(3)
            diagnostics[m] = {"pooled_within_sd": round(pooled[m], 4),
                              "se_of_3run_mean": round(se3, 4),
                              "order_noise_band": round(band[m], 4),
                              "band_over_se": round(band[m] / se3, 2)}

    # ---- within-sweep contrasts with exact permutation p
    contrasts = []
    for family, SET in (("drill", SWEEPS), ("param_all", PARAM_ALL), ("layer", LAYERS)):
        for pre, name, lay in SET:
            for m, mlabel in METRICS:
                hi, lo = vals(pre + "_high", m), vals(pre + "_low", m)
                if len(hi) != len(lo) or len(hi) < 2:
                    continue
                contrasts.append({
                    "family": family, "sweep": name, "layer": lay,
                    "metric": m, "metric_label": mlabel,
                    "high_mean": round(st.mean(hi), 4), "low_mean": round(st.mean(lo), 4),
                    "contrast": round(st.mean(hi) - st.mean(lo), 4),
                    "p_exact": round(exact_perm_p(hi, lo), 4),
                    "n_per_arm": len(hi),
                })

    # Inference must be STRATIFIED BY ARM SIZE. The exact permutation floor is
    # 2 / C(2n, n): 0.10 at n=3, 0.029 at n=4, 0.0079 at n=5, 0.0022 at n=6. Once a
    # batch mixes arm sizes - as it does after a confirmatory top-up - a single global
    # floor is meaningless, because only the largest arms can reach it and the
    # chance expectation would be computed against contrasts that never could.
    strata = {}
    for c in contrasts:
        strata.setdefault(c["n_per_arm"], []).append(c)
    inference = {}
    for n, group in sorted(strata.items()):
        floor = 2 / math.comb(2 * n, n)
        at_floor = [c for c in group if c["p_exact"] <= floor + 1e-9]
        at_05 = [c for c in group if c["p_exact"] <= 0.05 + 1e-9]
        inference[n] = {
            "n_per_arm": n, "n_contrasts": len(group),
            "p_floor": round(floor, 5),
            "n_at_floor": len(at_floor),
            "expected_at_floor_by_chance": round(floor * len(group), 2),
            "significance_attainable_at_05": floor <= 0.05,
            "n_below_05": len(at_05) if floor <= 0.05 else None,
            "expected_below_05_by_chance": round(0.05 * len(group), 2) if floor <= 0.05 else None,
            "contrasts_at_floor": [{"sweep": c["sweep"], "metric": c["metric_label"],
                                    "contrast": c["contrast"], "p_exact": c["p_exact"]} for c in at_floor],
        }
    p_floor = min(v["p_floor"] for v in inference.values()) if inference else None

    # ---- baseline displacement: calibrated config vs every perturbed condition
    cal = [r for r in rows if base_id(r["run_id"]) in CALIBRATED]
    lay_pert = [r for r in rows if base_id(r["run_id"]).startswith("layer_")]
    drill_pert = [r for r in rows if base_id(r["run_id"]) not in CALIBRATED
                  and not base_id(r["run_id"]).startswith("layer_")]

    def cmp(setA, setB, m):
        A = [fnum(r.get(m)) for r in setA if fnum(r.get(m)) is not None]
        B = [fnum(r.get(m)) for r in setB if fnum(r.get(m)) is not None]
        if len(A) < 2 or len(B) < 2:
            return None
        return {"a_mean": round(st.mean(A), 4), "b_mean": round(st.mean(B), 4),
                "delta": round(st.mean(B) - st.mean(A), 4),
                "welch_t": round(welch_t(A, B), 2), "n_a": len(A), "n_b": len(B)}

    displacement = {
        # the clean test: same batch, so neither judging format nor batch can explain it
        "within_screen_batch": {m: cmp(cal, lay_pert, m) for m, _ in METRICS},
        # confounded: manipulation type and batch move together here
        "calibrated_vs_drill_CONFOUNDED": {m: cmp(cal, drill_pert, m) for m, _ in METRICS},
        "layer_vs_drill_CONFOUNDED": {m: cmp(lay_pert, drill_pert, m) for m, _ in METRICS},
    }

    # direction symmetry: do the two poles displace the baseline the same way?
    hi_all = [r for r in rows if base_id(r["run_id"]).endswith("_high")]
    lo_all = [r for r in rows if base_id(r["run_id"]).endswith("_low")]
    symmetry = {}
    for m, _ in METRICS:
        c = [fnum(r.get(m)) for r in cal if fnum(r.get(m)) is not None]
        h = [fnum(r.get(m)) for r in hi_all if fnum(r.get(m)) is not None]
        l = [fnum(r.get(m)) for r in lo_all if fnum(r.get(m)) is not None]
        if c and h and l:
            symmetry[m] = {"calibrated": round(st.mean(c), 4),
                           "high_poles": round(st.mean(h), 4),
                           "low_poles": round(st.mean(l), 4)}

    # ---- session test on the calibrated configuration
    #
    # This used to compare condition 'main' against condition 'main_recheck'. That was a
    # session test only while 'main' was a single-session group. The confirmatory top-up
    # added main_r6..main_r10 to 'main' itself, so 'main' now SPANS both sessions and the
    # contrast compares a mixed group against a single-session one - it no longer
    # estimates what it names. The split below is therefore by run id, not by condition.
    #
    # Two contrasts are reported. The session test proper pools every calibrated run made
    # in the confirmatory session (top-up AND replicate) against the original draw. The
    # internal control then compares the two confirmatory groups with each other: if a
    # session effect drives the first contrast, the second must be null, and if the second
    # is NOT null the first is measuring something other than session.
    #
    # Membership is explicit because run_summary.json records a run LABEL in its
    # 'timestamp' field rather than a clock time, so there is no timestamp in the data to
    # split on, and folder mtime does not survive copying or cloud sync. The lists below
    # are the commissioning record from the run sheet (doc 18).
    SESSIONS = {
        "original":  ["main", "main_r2", "main_r3", "main_r4", "main_r5"],
        "topup":     ["main_r6", "main_r7", "main_r8", "main_r9", "main_r10"],
        "replicate": ["main_recheck_r%d" % i for i in range(1, 6)],
    }
    by_id = {r["run_id"]: r for r in rows}

    def svals(ids, m):
        return [fnum(by_id[i].get(m)) for i in ids
                if i in by_id and fnum(by_id[i].get(m)) is not None]

    def contrast(ids_a, ids_b, m):
        a, b = svals(ids_a, m), svals(ids_b, m)
        if len(a) < 2 or len(b) < 2:
            return None
        return {"a_mean": round(st.mean(a), 4), "b_mean": round(st.mean(b), 4),
                "delta": round(st.mean(b) - st.mean(a), 4),
                "welch_t": round(welch_t(a, b), 2),
                "p_exact": round(exact_perm_p(a, b), 4),
                "floor": round((2 if len(a) == len(b) else 1)
                               / math.comb(len(a) + len(b), len(a)), 4),
                "n_a": len(a), "n_b": len(b)}

    drift = None
    if any(i in by_id for i in SESSIONS["replicate"]):
        conf = SESSIONS["topup"] + SESSIONS["replicate"]
        drift = {"_design": {
                    "session_test": "original (n=%d) vs all confirmatory calibrated runs (n=%d)"
                                    % (len(SESSIONS["original"]), len(conf)),
                    "internal_control": "top-up vs replicate, both confirmatory - expected null"},
                 "session": {}, "control": {}}
        for m, lab in METRICS:
            c = contrast(SESSIONS["original"], conf, m)
            if c:
                drift["session"][m] = c
            c = contrast(SESSIONS["topup"], SESSIONS["replicate"], m)
            if c:
                drift["control"][m] = c

    # ---- variance census: which dependent variables carry usable information
    census = {}
    for m in [x for x, _ in METRICS] + ["dqi_justif_level", "dqi_constructive",
                                        "dqi_individuation", "rounds", "experts"]:
        v = [fnum(r.get(m)) for r in rows if fnum(r.get(m)) is not None]
        if not v:
            continue
        census[m] = {"min": min(v), "max": max(v), "sd": round(st.stdev(v), 4),
                     "distinct_values": len(set(v)), "n": len(v)}
    ag = [r.get("agreement", "") for r in rows if r.get("agreement", "") != ""]
    census["agreement"] = {"true": sum(1 for x in ag if x == "True"), "n": len(ag)}

    out = {"batch": str(root), "n_runs": len(rows), "n_conditions": len(g),
           "threshold_diagnostics": diagnostics,
           "contrasts": contrasts,
           "inference_by_arm_size": inference,
           "n_contrasts": len(contrasts),
           "baseline_displacement": displacement, "pole_symmetry": symmetry,
           "batch_drift_test": drift,
           "variance_census": census}
    (root / "drill_analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    # ---- markdown
    L = ["# Parameter drill-down analysis (Section 9.5)", "",
         f"Batch `{root.name}` - {len(rows)} runs across {len(g)} conditions.", "",
         "## 1. Are the screening thresholds usable?", "",
         "| metric | pooled within-condition SD | SE of a 3-run mean | order-noise band | band / SE |",
         "|---|---|---|---|---|"]
    for m, lab in METRICS:
        d = diagnostics.get(m)
        if d:
            flag = "  **<- band is BELOW run-to-run noise**" if d["band_over_se"] < 1 else ""
            L.append(f"| {lab} | {d['pooled_within_sd']} | {d['se_of_3run_mean']} | "
                     f"{d['order_noise_band']} | {d['band_over_se']}{flag} |")
    L += ["", "A usable screening band sits well above the standard error of a condition mean. "
              "Where it does not, the screen will over-fire on that metric.", ""]

    L += ["## 2. Within-sweep contrasts (high minus low, same batch, baseline offset cancels)", ""]
    for n, v in sorted(inference.items()):
        if v["significance_attainable_at_05"]:
            L.append(f"- **{v['n_contrasts']} contrasts at {n} vs {n} runs.** Exact floor p = {v['p_floor']}; "
                     f"significance at 0.05 IS attainable. {v['n_below_05']} contrasts reach p <= 0.05 "
                     f"(chance would give about {v['expected_below_05_by_chance']}).")
        else:
            L.append(f"- **{v['n_contrasts']} contrasts at {n} vs {n} runs.** Exact floor p = {v['p_floor']}, so "
                     f"conventional significance is UNREACHABLE at this arm size. {v['n_at_floor']} reach the floor "
                     f"(chance would give about {v['expected_at_floor_by_chance']}).")
    L += ["",
          "| family | sweep | layer | metric | high | low | contrast | p (exact) |",
          "|---|---|---|---|---|---|---|---|"]
    for c in sorted(contrasts, key=lambda x: (x["p_exact"], -abs(x["contrast"]))):
        mark = " **" if c["p_exact"] <= (p_floor or 0) + 1e-9 else ""
        L.append(f"| {c['family']} | {c['sweep']} | {c['layer']} | {c['metric_label']} | "
                 f"{c['high_mean']} | {c['low_mean']} | {c['contrast']:+}{mark} | {c['p_exact']} |")
    L += [""]

    L += ["## 3. Baseline displacement", "",
          "Clean comparison - calibrated configuration vs layer-perturbed, both from the screen batch:", "",
          "| metric | calibrated | perturbed | delta | Welch t |", "|---|---|---|---|---|"]
    for m, lab in METRICS:
        d = displacement["within_screen_batch"].get(m)
        if d:
            L.append(f"| {lab} | {d['a_mean']} | {d['b_mean']} | {d['delta']:+} | {d['welch_t']:+} |")
    L += ["", "Pole symmetry (does the direction of the perturbation matter?):", "",
          "| metric | calibrated | all high poles | all low poles |", "|---|---|---|---|"]
    for m, lab in METRICS:
        s = symmetry.get(m)
        if s:
            L.append(f"| {lab} | {s['calibrated']} | {s['high_poles']} | {s['low_poles']} |")

    if drift:
        L += ["", "## 3b. Session test on the calibrated configuration", "",
              "Split by RUN ID, not by condition: the confirmatory top-up added runs to 'main'",
              "itself, so condition 'main' now spans both sessions and cannot serve as the",
              "original-session arm. Membership is the commissioning record (doc 18).", "",
              "**Session test** - original draw vs every calibrated run made in the confirmatory",
              "session (top-up and replicate pooled):", "",
              "| metric | original (n=%d) | confirmatory (n=%d) | delta | Welch t | p (exact) | floor |"
              % (drift["session"].get("dqi_respect", {}).get("n_a", 0),
                 drift["session"].get("dqi_respect", {}).get("n_b", 0)),
              "|---|---|---|---|---|---|---|"]
        for m, lab in METRICS:
            d = drift["session"].get(m)
            if d:
                L.append(f"| {lab} | {d['a_mean']} | {d['b_mean']} | {d['delta']:+} | "
                         f"{d['welch_t']:+} | {d['p_exact']} | {d['floor']} |")
        L += ["", "**Internal control** - the two confirmatory groups against each other. A session",
              "effect predicts this is null; a non-null result would mean the contrast above is",
              "not measuring session.", "",
              "| metric | top-up | replicate | delta | Welch t | p (exact) |", "|---|---|---|---|---|---|"]
        for m, lab in METRICS:
            d = drift["control"].get(m)
            if d:
                L.append(f"| {lab} | {d['a_mean']} | {d['b_mean']} | {d['delta']:+} | "
                         f"{d['welch_t']:+} | {d['p_exact']} |")

    L += ["", "## 4. Variance census - which dependent variables carry information", "",
          "| variable | min | max | SD | distinct values |", "|---|---|---|---|---|"]
    for k, v in census.items():
        if k == "agreement":
            continue
        L.append(f"| {k} | {v['min']} | {v['max']} | {v['sd']} | {v['distinct_values']} |")
    L.append(f"| agreement | - | - | - | {census['agreement']['true']}/{census['agreement']['n']} True |")

    (root / "drill_analysis.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print("\nwritten: drill_analysis.json + drill_analysis.md in", root)


if __name__ == "__main__":
    main()
