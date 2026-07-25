"""
run_sensitivity.py - systematic sensitivity analysis + order-robustness check.

Two sweep modes (per the layered design and the supervisor's steer):
  * layer  - shift a WHOLE LAYER's parameters together, for all stakeholders, to
             an extreme-low and an extreme-high value. These layer conditions
             double as the extreme-value CONTROLS (they bracket the range each
             layer can produce and act as manipulation checks).
  * param  - the per-parameter drill-down, used only inside the layer(s) that the
             layer-level screen shows to be influential.
  * all    - both.

Runs the main scenario, then the selected sweep conditions (others held at their
main value), then re-runs the main scenario under reversed and randomised order.
Each run is a full roundtable; results collect into data/sensitivity_<ts>/index.csv.
Judge-based quality/outcome columns are left blank for the evaluation step;
structural proxies are recorded now.

Usage:
    python run_sensitivity.py --dry                 # stubbed LLM (no API), verify harness
    python run_sensitivity.py --mode layer          # layer-level screen + extremes (default)
    python run_sensitivity.py --mode param          # per-parameter drill-down
    python run_sensitivity.py --mode all            # both
    python run_sensitivity.py --only main,layer      # subsets: main, layer, param, order, or ids
"""
from __future__ import annotations
import csv, json, copy, random, datetime, argparse
from pathlib import Path
import yaml
from src.utils.config_loader import load_config
from src.engines.roundtable import run_roundtable

BASE_CONFIG = "config/simulation_config.yaml"

# Four functional layers (Belief/relational_prior handled separately; add if needed).
LAYERS = {
    "salience":    ["power", "legitimacy", "urgency"],
    "motivation":  ["social_preference", "risk_preference", "time_preference"],
    "position":    ["flexibility", "dependency"],
    "interaction": ["assertiveness", "cooperativeness"],
}
# Extreme poles used for the layer-level screen; these ARE the extreme-value controls.
LAYER_LOW, LAYER_HIGH = 1, 10

# Per-parameter drill-down sweeps (used within an influential layer).
# Screen-informed HYBRID drill-down (post layer screen): live layers in depth +
# one null-confirmation probe per inert layer. Sweep targets selected by the
# legibility-informed rule: calibration must let BOTH poles cross verbal bands.
PARAM_SWEEPS = {
    # live layer: position
    "mgmt.flexibility":     ("management", "flexibility", 2, 8),
    "igmetall.flexibility": ("ig_metall", "flexibility", 2, 8),
    "mgmt.dependency":      ("management", "dependency", 2, 8),
    "works.dependency":     ("works_council", "dependency", 2, 8),
    # live layer: interaction
    "saxony.assertiveness": ("lower_saxony", "assertiveness", 3, 9),
    "works.cooperativeness":("works_council", "cooperativeness", 2, 8),
    # null-confirmation probes
    "owners.social_pref":   ("owners", "social_preference", 2, 8),
    "investors.power":      ("investors", "power", 3, 9),
    # belief-layer probe (the one framework element outside the layer screen):
    # management's relational prior, calibrated 4 (mid band) -> 2/8 cross both bands
    "mgmt.relational_prior": ("management", "relational_prior", 2, 8),
}
RED_LINE_SIGNALS = ["red line", "cannot concede", "will not concede", "non-negotiable", "under no circumstances", "will not abandon"]

def _load_raw():
    return yaml.safe_load(Path(BASE_CONFIG).read_text(encoding="utf-8"))

def _sh(raw, key):
    for s in raw["stakeholders"]:
        if s["key"] == key:
            return s
    raise KeyError(key)

def _salience(s):
    return (s["power"]["value"] + s["legitimacy"]["value"] + s["urgency"]["value"]) / 3.0

def _proxies(run_folder):
    outs = list((Path(run_folder) / "outputs").glob("round*.txt"))
    rl, chars = 0, 0
    for f in outs:
        t = f.read_text(encoding="utf-8").lower()
        chars += len(t)
        if any(sig in t for sig in RED_LINE_SIGNALS):
            rl += 1
    return {"agent_turns": len(outs), "red_line_declarations": rl, "transcript_chars": chars}

def build_conditions(mode="layer", only=None):
    conds = [{"id": "main", "label": "main scenario", "order": "salience"}]
    if mode in ("layer", "all"):
        for layer in LAYERS:
            conds.append({"id": "layer_%s_low" % layer,  "label": "layer %s = %s (extreme-low)"  % (layer, LAYER_LOW),  "order": "salience", "layer_override": (layer, LAYER_LOW)})
            conds.append({"id": "layer_%s_high" % layer, "label": "layer %s = %s (extreme-high)" % (layer, LAYER_HIGH), "order": "salience", "layer_override": (layer, LAYER_HIGH)})
    if mode in ("param", "all"):
        for label, (k, param, lo, hi) in PARAM_SWEEPS.items():
            base = label.replace(".", "_")
            conds.append({"id": base + "_low",  "label": "%s=%s" % (label, lo), "order": "salience", "override": (k, param, lo)})
            conds.append({"id": base + "_high", "label": "%s=%s" % (label, hi), "order": "salience", "override": (k, param, hi)})
    conds.append({"id": "order_reversed", "label": "order: reversed", "order": "reversed"})
    conds.append({"id": "order_random",   "label": "order: random",   "order": "random"})
    if only:
        sel = set(only)
        def keep(c):
            if c["id"] in sel: return True
            if "main" in sel and c["id"] == "main": return True
            if "order" in sel and c["order"] in ("reversed", "random"): return True
            if "layer" in sel and c.get("layer_override"): return True
            if "param" in sel and c.get("override"): return True
            return False
        conds = [c for c in conds if keep(c)]
    return conds

def run_plan(conditions, client=None, repeat=1, into=None, skip_first=False):
    """repeat: run each condition N times (ids suffixed _r1.._rN when N>1).
    into: append to an EXISTING batch folder (its index.csv is extended).
    skip_first: with --into, skip _r1 because the base run already exists."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    root = Path(into) if into else (Path("data") / ("sensitivity_" + ts))
    expanded = []
    for cond in conditions:
        for r in range(1, repeat + 1):
            if skip_first and r == 1:
                continue
            c = dict(cond)
            if repeat > 1 or skip_first:
                c = dict(cond); c["id"] = "%s_r%d" % (cond["id"], r)
                c["label"] = "%s [rep %d]" % (cond["label"], r)
            expanded.append(c)
    conditions = expanded
    base_root = Path(BASE_CONFIG).resolve().parent.parent
    scen_abs = str((base_root / _load_raw()["scenario_path"]).resolve())
    rows = []
    for cond in conditions:
        if into:
            rf_check = root / cond["id"]
            if (rf_check / "run_summary.json").exists():
                summ = json.loads((rf_check / "run_summary.json").read_text(encoding="utf-8"))
                rows.append({
                    "run_id": cond["id"], "condition": cond["label"], "order": cond.get("order", "salience"),
                    "rounds": summ["rounds_completed"], "convergence": summ["convergence_status"],
                    "experts": len(summ["experts_summoned"]), "tokens": summ["total_tokens"],
                    "in_tokens": summ.get("input_tokens", 0), "out_tokens": summ.get("output_tokens", 0),
                    "cost_usd": summ.get("estimated_cost_usd"), "truncated": summ.get("truncated_calls", 0),
                    **_proxies(str(rf_check)),
                    "agreement": "", "position_move": "",
                    "dqi_justif_level": "", "dqi_justif_content": "", "dqi_respect": "",
                    "dqi_constructive": "", "dqi_individuation": "", "kappa_mean": "",
                    "judge_notes": "", "run_folder": str(rf_check),
                })
                print("  skip (already completed, row reconstructed): %s" % cond["id"], flush=True)
                continue
            if rf_check.exists():                      # partial from a crashed attempt
                import shutil, os, stat, time
                def _unlock(fn, path, exc):            # clear read-only attributes and retry
                    os.chmod(path, stat.S_IWRITE)
                    fn(path)
                wiped = False
                for attempt in range(3):
                    try:
                        shutil.rmtree(rf_check, onerror=_unlock)
                        wiped = True
                        break
                    except PermissionError:
                        time.sleep(2 * (attempt + 1))  # give OneDrive a moment to release handles
                if not wiped:
                    parked = rf_check.with_name(rf_check.name + "_partial_parked")
                    try:
                        rf_check.rename(parked)
                        print("  could not delete locked partial %s - parked as %s, re-running fresh"
                              % (cond["id"], parked.name), flush=True)
                    except PermissionError:
                        raise SystemExit(
                            "Partial folder %s is locked by another process (OneDrive/Explorer). "
                            "Close Explorer windows or pause OneDrive syncing, delete the folder "
                            "manually, then rerun this command." % rf_check)
                else:
                    print("  wiped partial folder, re-running: %s" % cond["id"], flush=True)
        raw = copy.deepcopy(_load_raw())
        raw["scenario_path"] = scen_abs
        if cond.get("override"):
            k, param, val = cond["override"]
            _sh(raw, k)[param]["value"] = val
        if cond.get("layer_override"):
            layer, val = cond["layer_override"]
            for s in raw["stakeholders"]:
                for p in LAYERS[layer]:
                    s[p]["value"] = val
        om = cond.get("order", "salience")
        if om == "salience":
            raw["roundtable"]["salience_orchestration"] = True
        else:
            raw["roundtable"]["salience_orchestration"] = False
            keys = [s["key"] for s in raw["stakeholders"]]
            order = sorted(keys, key=lambda kk: _salience(_sh(raw, kk)), reverse=True)
            if om == "reversed":
                order = list(reversed(order))
            elif om == "random":
                random.Random(raw["model"]["seed"]).shuffle(order)
            raw["roundtable"]["turn_order"] = order
        rf = root / cond["id"]
        rf.mkdir(parents=True, exist_ok=True)
        cfg_path = rf / "config_used.yaml"
        cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8")
        cfg = load_config(str(cfg_path))
        summ = run_roundtable(cfg, cond["id"], str(rf), client=client)
        rows.append({
            "run_id": cond["id"], "condition": cond["label"], "order": om,
            "rounds": summ["rounds_completed"], "convergence": summ["convergence_status"],
            "experts": len(summ["experts_summoned"]), "tokens": summ["total_tokens"],
            "in_tokens": summ.get("input_tokens", 0), "out_tokens": summ.get("output_tokens", 0),
            "cost_usd": summ.get("estimated_cost_usd"), "truncated": summ.get("truncated_calls", 0),
            **_proxies(str(rf)),
            "agreement": "", "position_move": "",
            "dqi_justif_level": "", "dqi_justif_content": "", "dqi_respect": "",
            "dqi_constructive": "", "dqi_individuation": "", "kappa_mean": "",
            "judge_notes": "",
            "run_folder": str(rf),
        })
        print("  done: %-22s rounds=%s tokens=%s" % (cond["id"], summ["rounds_completed"], summ["total_tokens"]))
    root.mkdir(parents=True, exist_ok=True)
    idx = root / "index.csv"
    if not rows:
        print("nothing to run (all conditions already completed)"); return str(root), rows
    if into and idx.exists():                     # extend the existing index
        old = list(csv.DictReader(open(idx, encoding="utf-8")))
        fields = list(old[0].keys())
        seen = {o["run_id"] for o in old}
        rows = [rw for rw in rows if rw["run_id"] not in seen]
        for r in rows:
            for k in fields:
                r.setdefault(k, "")
        rows = old + [{k: r.get(k, "") for k in fields} for r in rows]
        fieldnames = fields
    else:
        fieldnames = list(rows[0].keys())
    with open(idx, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader(); w.writerows(rows)
    (root / "index.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nindex written: %s" % idx)
    return str(root), rows

def _stub_client():
    from src.utils.llm import LLMResponse
    class Stub:
        def call(self, messages, label):
            if label.startswith("convergence"):
                t = '{"status":"progressing","recommendation":"continue"}'
            elif "gen_persona" in label:
                t = "You are a neutral expert; speak only within your domain."
            else:
                t = "[stub %s] My position stands; this is unacceptable to me. cannot concede." % label
            return LLMResponse(t, "stub", "stub", "stub-1", 10, "fp", 1, "stop", 0.0)
    return Stub()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="stubbed LLM, no API")
    ap.add_argument("--mode", default="layer", choices=["layer", "param", "all"], help="which sweeps to run")
    ap.add_argument("--only", default="", help="comma list: main, layer, param, order, or run ids")
    ap.add_argument("--repeat", type=int, default=1, help="run each condition N times (ids get _rK suffixes)")
    ap.add_argument("--into", default="", help="append runs to an existing sensitivity_<ts> folder")
    ap.add_argument("--skip-first", action="store_true", help="with --into: skip _r1 (base run already exists)")
    a = ap.parse_args()
    only = [x.strip() for x in a.only.split(",") if x.strip()] or None
    conds = build_conditions(a.mode, only)
    n_eff = len(conds) * (a.repeat - (1 if a.skip_first else 0))
    print("Plan (mode=%s, repeat=%d%s): %d runs" % (a.mode, a.repeat, ", into existing batch" if a.into else "", n_eff))
    run_plan(conds, client=_stub_client() if a.dry else None,
             repeat=a.repeat, into=(a.into or None), skip_first=a.skip_first)

if __name__ == "__main__":
    main()
