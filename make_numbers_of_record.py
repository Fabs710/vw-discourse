"""
make_numbers_of_record.py - the one table every quoted number must defer to.

Why this exists
---------------
The thesis quotes its headline numbers in four to six places each, across 26
documents, and they were propagated by hand. Twice in one week that drifted:
the cross-model deltas survived a baseline correction in five documents but not
in the sixth, and Table 4 held a stale p = 0.982 two paragraphs below prose
saying p = 0.55. The cure is structural, not vigilance: ONE generated table,
built from the data files, against which the text is reconciled. Fix the text,
never the table.

Everything here is COMPUTED from the run data except the block marked
HAND-ENTERED, whose values live in documents rather than data files and carry
their source in the table.

Usage:  python make_numbers_of_record.py
Writes: data/numbers_of_record.json  and  data/numbers_of_record.md
"""
import csv, json, math, itertools, re
import statistics as st
from pathlib import Path

MAIN  = Path("data/sensitivity_20260723_000046")
CROSS = Path("data/sensitivity_20260726_172041")
CAP   = Path("data/sensitivity_20260726_155350")

_REP = re.compile(r"_r\d+$")
def base(rid): return _REP.sub("", rid).split("__", 1)[0]

def rows(p):
    return list(csv.DictReader(open(p / "index.csv", encoding="utf-8")))

def num(v):
    try: return float(v)
    except (TypeError, ValueError): return None

def col(rs, c): return [num(r[c]) for r in rs if num(r[c]) is not None]

def exact_p(a, b):
    obs = abs(st.mean(a) - st.mean(b)); pool = list(a) + list(b); n = len(a)
    tot = math.comb(len(pool), n); h = 0
    for idx in itertools.combinations(range(len(pool)), n):
        x = [pool[i] for i in idx]; y = [pool[i] for i in range(len(pool)) if i not in idx]
        if abs(st.mean(x) - st.mean(y)) >= obs - 1e-12: h += 1
    return h / tot

def floor_p(na, nb):
    return (2 if na == nb else 1) / math.comb(na + nb, na)

import datetime
R = {"_meta": {"generated": datetime.date.today().isoformat(), "rule": "fix the text, never the table",
               "source": "index.csv + analysis JSONs of the three controlled batches "
                         "+ audit outputs; HAND-ENTERED block excepted"}}

M, X, C = rows(MAIN), rows(CROSS), rows(CAP)
g = {}
for r in M: g.setdefault(base(r["run_id"]), []).append(r)
mini_main = g["main"]                      # ten calibrated runs
son_main  = [r for r in X if base(r["run_id"]) == "main"]

# ---- run counts and corpus ---------------------------------------------------
R["corpus"] = {
    "main_batch_runs": len(M), "cross_model_runs": len(X), "round_cap_runs": len(C),
    "controlled_runs": len(M) + len(X) + len(C),
    "programme_runs_generated": 177,      # incl. dev/dry batches; Appendix H table
    "baseline_n": len(mini_main),
    "conditions_main_batch": len(g),
}

# ---- baseline (ten-run calibrated configuration) -----------------------------
R["baseline"] = {}
for k, lab in [("dqi_respect", "respect"), ("dqi_justif_content", "justification_content"),
               ("position_move", "position_movement"), ("dqi_justif_level", "justification_level"),
               ("dqi_constructive", "constructive_politics"), ("transcript_chars", "transcript_chars")]:
    v = col(mini_main, k)
    R["baseline"][lab] = {"mean": round(st.mean(v), 4), "sd": round(st.stdev(v), 4),
                          "n": len(v), "2sd": round(2 * st.stdev(v), 4)}

# ---- screening thresholds on the completed batch -----------------------------
def band(metric):
    mm = st.mean(col(mini_main, metric))
    return max(abs(st.mean(col(g[o], metric)) - mm) for o in ("order_reversed", "order_random"))

def pooled_sd(metric):
    sds = [st.stdev(col(v, metric)) for v in g.values() if len(col(v, metric)) > 1]
    return math.sqrt(sum(s * s for s in sds) / len(sds))

R["screen_thresholds"] = {}
for k, lab in [("dqi_justif_content", "justification_content"), ("dqi_respect", "respect"),
               ("position_move", "position_movement"), ("red_line_declarations", "red_line"),
               ("transcript_chars", "transcript_chars")]:
    b, p = band(k), pooled_sd(k)
    R["screen_thresholds"][lab] = {"order_band": round(b, 4), "pooled_sd": round(p, 4),
                                   "se_3run": round(p / math.sqrt(3), 4),
                                   "band_over_se": round(b / (p / math.sqrt(3)), 2)}

# ---- the surviving screen effect --------------------------------------------
hi = col(g["layer_position_high"], "position_move"); mm = col(mini_main, "position_move")
R["screen_effect_position_movement"] = {
    "baseline": round(st.mean(mm), 4), "high": round(st.mean(hi), 4),
    "effect": round(st.mean(hi) - st.mean(mm), 4),
    "exact_p_vs_baseline_posthoc": round(exact_p(mm, hi), 4),
    "floor": round(floor_p(len(mm), len(hi)), 4),
    "note": "screen verdict rests on the two pre-stated criteria; the p is a post-hoc robustness figure"}

# ---- session test (calibrated configuration, split by commissioning record) --
ORIG = ["main", "main_r2", "main_r3", "main_r4", "main_r5"]
TOP  = ["main_r%d" % i for i in range(6, 11)]
RECH = ["main_recheck_r%d" % i for i in range(1, 6)]
byid = {r["run_id"]: r for r in M}
def sv(ids, k): return [num(byid[i][k]) for i in ids if i in byid and num(byid[i][k]) is not None]
a, b = sv(ORIG, "dqi_respect"), sv(TOP + RECH, "dqi_respect")
c, d_ = sv(TOP, "dqi_respect"), sv(RECH, "dqi_respect")
R["session_test_respect"] = {
    "original_mean": round(st.mean(a), 4), "confirmatory_mean": round(st.mean(b), 4),
    "delta": round(st.mean(b) - st.mean(a), 4), "p": round(exact_p(a, b), 4),
    "control_delta": round(st.mean(d_) - st.mean(c), 4), "control_p": round(exact_p(c, d_), 4)}

# ---- baseline displacement (calibrated vs perturbed, completed batch) --------
CAL = {"main", "main_recheck", "order_reversed", "order_random"}
cal = [x for cnd in CAL for x in col(g.get(cnd, []), "dqi_respect")]
per = [x for cnd in g if cnd not in CAL for x in col(g[cnd], "dqi_respect")]
def welch_t(x, y):
    vx, vy = st.variance(x), st.variance(y)
    return (st.mean(y) - st.mean(x)) / math.sqrt(vx / len(x) + vy / len(y))
R["baseline_displacement_respect"] = {
    "calibrated_mean": round(st.mean(cal), 4), "n_calibrated": len(cal),
    "perturbed_mean": round(st.mean(per), 4),
    "delta": round(st.mean(per) - st.mean(cal), 4), "welch_t": round(welch_t(cal, per), 2),
    "history": "+0.102 (11 cal runs, Jul) -> +0.063 (16) -> this value (27)"}

# ---- round cap ---------------------------------------------------------------
cap6 = [r for r in C if num(r.get("rounds")) == 6.0] or C
R["round_cap"] = {}
for k, lab in [("dqi_respect", "respect"), ("position_move", "position_movement"),
               ("transcript_chars", "transcript_chars")]:
    a4, a6 = col(mini_main, k), col(cap6, k)
    R["round_cap"][lab] = {"r4": round(st.mean(a4), 4), "r6": round(st.mean(a6), 4),
                          "delta": round(st.mean(a6) - st.mean(a4), 4),
                          "p": round(exact_p(a4, a6), 4)}

# ---- cross-model (Table 4, ten-run baseline) --------------------------------
R["cross_model"] = {"floor": round(floor_p(len(mini_main), len(son_main)), 4)}
for k, lab in [("dqi_respect", "respect"), ("position_move", "position_movement"),
               ("experts", "experts"), ("red_line_declarations", "red_line"),
               ("dqi_justif_content", "justification_content"), ("dqi_justif_level", "justification_level"),
               ("dqi_constructive", "constructive_politics"), ("dqi_individuation", "individuation"),
               ("transcript_chars", "transcript_chars"), ("tokens", "tokens"), ("cost_usd", "gen_cost")]:
    a4, s4 = col(mini_main, k), col(son_main, k)
    if len(a4) < 2 or len(s4) < 2: continue
    R["cross_model"][lab] = {"mini": round(st.mean(a4), 4), "sonnet": round(st.mean(s4), 4),
                             "delta": round(st.mean(s4) - st.mean(a4), 4),
                             "p": round(exact_p(a4, s4), 4)}
ph = col([r for r in X if base(r["run_id"]) == "layer_position_high"], "position_move")
pl = col([r for r in X if base(r["run_id"]) == "layer_position_low"], "position_move")
mh = col(g["layer_position_high"], "position_move"); ml = col(g["layer_position_low"], "position_move")
R["cross_model"]["position_sweep_contrast"] = {
    "mini": round(st.mean(mh) - st.mean(ml), 4), "sonnet": round(st.mean(ph) - st.mean(pl), 4)}

# ---- jury agreement across the main batch -----------------------------------
kk = col(M, "kappa_mean")
R["jury"] = {"kappa_median": round(st.median(kk), 3), "kappa_mean": round(st.mean(kk), 3),
             "n": len(kk), "at_or_below_fair_041": sum(1 for x in kk if x <= 0.41),
             "substantial_061_plus": sum(1 for x in kk if x >= 0.61)}

# ---- variance census ---------------------------------------------------------
R["variance_census"] = {}
for k, lab in [("dqi_respect", "respect"), ("dqi_justif_content", "justification_content"),
               ("dqi_constructive", "constructive_politics"), ("dqi_justif_level", "justification_level"),
               ("dqi_individuation", "individuation"), ("red_line_declarations", "red_line")]:
    v = col(M, k)
    R["variance_census"][lab] = {"sd": round(st.stdev(v), 4), "distinct": len(set(v)),
                                 "min": round(min(v), 3), "max": round(max(v), 3),
                                 "at_2.0": sum(1 for x in v if x == 2.0)}

# ---- verbosity ---------------------------------------------------------------
def spearman(x, y):
    def ranks(z):
        o = sorted(range(len(z)), key=lambda i: z[i]); r = [0.0] * len(z); i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and z[o[j + 1]] == z[o[i]]: j += 1
            for q in range(i, j + 1): r[o[q]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = ranks(x), ranks(y); mx, my = st.mean(rx), st.mean(ry)
    return sum((p - mx) * (q - my) for p, q in zip(rx, ry)) / math.sqrt(
        sum((p - mx) ** 2 for p in rx) * sum((q - my) ** 2 for q in ry))
pairs = [(num(r["transcript_chars"]), num(r["dqi_respect"]), num(r["dqi_justif_content"])) for r in M]
pairs = [p for p in pairs if all(v is not None for v in p)]
R["verbosity_rho"] = {"respect": round(spearman([p[0] for p in pairs], [p[1] for p in pairs]), 3),
                      "justification_content": round(spearman([p[0] for p in pairs], [p[2] for p in pairs]), 3)}

# ---- test-retest (from stored analysis) -------------------------------------
f = MAIN / "retest_analysis_retest1.json"
if f.exists():
    R["test_retest"] = json.loads(f.read_text(encoding="utf-8"))

# ---- judge audit (scopes A, B, C from stored outputs) ------------------------
f = Path("data/audit_sample_scores.json")
if f.exists():
    s = json.loads(f.read_text(encoding="utf-8"))["statistics"]
    R["audit_scope_A"] = {"n_items": s["n_items"], "cost_usd": s["judging_cost"]["cost_usd"],
                          "pairs": s["pairs"], "usable": s["usable_output_rate"]}
R["audit_scopes_BC"] = {}
for batch, lab in [(CROSS, "B_sonnet"), (MAIN, "C_mini")]:
    for suf in ("audit_gemini", "audit_qwen"):
        f = batch / ("audit_judge_analysis_%s.json" % suf)
        if f.exists():
            j = json.loads(f.read_text(encoding="utf-8"))
            R["audit_scopes_BC"]["%s_%s" % (lab, suf)] = {
                dim: {kk2: v[kk2] for kk2 in ("audit", "jury_mean", "audit_minus_jury",
                                              "kappa_audit_j1", "kappa_audit_j2", "kappa_j1_j2",
                                              "audit_share_at_ceiling")}
                for dim, v in j["dimensions"].items()}

# ---- costs (computed where logged) ------------------------------------------
gen = sum(x or 0 for x in (num(r.get("cost_usd")) for r in M + X + C))
jud = sum(x or 0 for x in (num(r.get("eval_cost_usd")) for r in M + X + C))
aud = 0.0
for b in (MAIN, CROSS):
    for f in b.glob("*/evaluation_audit_*.json"):
        aud += (json.loads(f.read_text(encoding="utf-8")).get("judging_cost") or {}).get("cost_usd", 0) or 0
R["costs"] = {"generation_controlled_batches": round(gen, 2),
              "judging_logged_controlled": round(jud, 2),
              "audit_scopes_BC": round(aud, 2)}

# ---- HAND-ENTERED: values whose source is a document, not a data file --------
R["hand_entered"] = {
    "_rule": "each value names its source; change it only by changing the source",
    "gm_fidelity": {"value": "1.62 of 2 across ten pre-registered claims", "source": "doc 14, Sec 9.7"},
    "legibility": {"value": "independent model recovers the intended band", "source": "doc 12, Sec 5.6"},
    "human_check_v2": {"kappa_content_v2": ".88 (Claude) / .56 (GPT)", "kappa_respect": ".50 / .31",
                       "source": "doc 14, Sec 8.5; data/human_codes.json"},
    "generation_total_appH": {"value": "$88.69 across 177 generated runs", "source": "Appendix H (doc 17)"},
    "judging_logged_appH": {"value": "$15.71 across 62 instrumented runs", "source": "Appendix H"},
    "pre_instrumentation_estimate": {"value": "~$22 (estimate on known call volume)", "source": "Appendix H"},
    "audit_total": {"value": "$5.65 ($0.26 sample + $5.39 scopes B/C)", "source": "Appendix H + audit log"},
    "project_total": {"value": "~$132", "source": "Appendix H"},
    "confirmed_drill_effects": {"value": "3 of 20 contrasts, ~1 expected by chance; strongest belief/respect +0.073 p=.0087",
                                "source": "doc 16, Sec 9.5"},
}

out = Path("data/numbers_of_record.json")
out.write_text(json.dumps(R, indent=1), encoding="utf-8")

L = ["# Numbers of record - generated %s" % R["_meta"]["generated"],
     "", "Rule: **fix the text, never the table.** Regenerate with `python make_numbers_of_record.py`.", ""]
def sec(title, obj):
    L.append("## " + title); L.append("")
    L.append("```json"); L.append(json.dumps(obj, indent=1)); L.append("```"); L.append("")
for k in ["corpus", "baseline", "screen_thresholds", "screen_effect_position_movement",
          "session_test_respect", "baseline_displacement_respect", "round_cap", "cross_model",
          "jury", "variance_census", "verbosity_rho", "audit_scope_A", "costs", "hand_entered"]:
    if k in R: sec(k, R[k])
Path("data/numbers_of_record.md").write_text("\n".join(L), encoding="utf-8")
print("written: data/numbers_of_record.json + .md")
for k in ("corpus", "jury", "costs"):
    print(" ", k, "=", json.dumps(R[k]))

# ---- judge offsets (appended 27 Jul after the sign-error correction) ----------
# OpenAI-minus-Anthropic, per dimension, both batches, from contribution records.
# In the table so the reconciliation catches any future sign confusion.
def _offsets(root):
    out = {}
    for dim in ["justification_level", "justification_content", "respect",
                "constructive_politics", "individuation"]:
        vals = []
        for d in Path(root).iterdir():
            f = d / "evaluation.json"
            if not f.exists(): continue
            j = json.loads(f.read_text(encoding="utf-8"))
            for c in j.get("contribution_scores", []):
                if len(c.get("judges", [])) > 1:
                    a, b = c["judges"][0].get(dim), c["judges"][1].get(dim)
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        vals.append(a - b)
        if vals:
            out[dim] = {"mean_offset_openai_minus_anthropic": round(st.mean(vals), 4),
                        "n_records": len(vals)}
    return out

R2 = json.loads(Path("data/numbers_of_record.json").read_text(encoding="utf-8"))
R2["judge_offsets"] = {"main_batch": _offsets(MAIN), "cross_model_batch": _offsets(CROSS),
                       "note": "judges[0]=OpenAI, judges[1]=Anthropic (build order, core.py); "
                               "positive = OpenAI more lenient. Sign error corrected 29 Jul."}
Path("data/numbers_of_record.json").write_text(json.dumps(R2, indent=1), encoding="utf-8")
with Path("data/numbers_of_record.md").open("a", encoding="utf-8") as f:
    f.write("\n## judge_offsets\n\n```json\n" + json.dumps(R2["judge_offsets"], indent=1) + "\n```\n")
print("judge_offsets appended")
