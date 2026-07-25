"""
analyze_sensitivity.py - R=3 analysis of the layer screen.

Aggregates all runs in a batch (base condition = run_id without the _rN suffix):
per-condition means and spread for the quality family (adapted DQI), the outcome
family (agreement rate, position movement, rounds), and the structural battery;
reads every layer effect against the ORDER-CONDITION NOISE BAND (the spread of
|order - baseline| differences); collects settlement terms; and writes
analysis.json + analysis.md next to index.csv.

Usage:  python analyze_sensitivity.py data/sensitivity_20260723_000046
"""
import json, csv, argparse, statistics as st
from pathlib import Path
from collections import defaultdict

QUALITY=["dqi_justif_level","dqi_justif_content","dqi_respect","dqi_constructive","dqi_individuation"]
OUTCOME=["position_move"]; STRUCT=["red_line_declarations","transcript_chars","experts","rounds"]
ALL=QUALITY+OUTCOME+STRUCT
LAYERS=["layer_salience_low","layer_salience_high","layer_motivation_low","layer_motivation_high",
        "layer_position_low","layer_position_high","layer_interaction_low","layer_interaction_high"]
ORDERS=["order_reversed","order_random"]

def base_id(run_id):
    for suf in ("_r1","_r2","_r3","_r4","_r5"):
        if run_id.endswith(suf): return run_id[:-3]
    return run_id

def fnum(v):
    try: return float(v)
    except (TypeError, ValueError): return None

def agg(vals):
    v=[x for x in vals if x is not None]
    if not v: return None
    return {"mean": round(st.mean(v),3), "sd": round(st.stdev(v),3) if len(v)>1 else None,
            "min": round(min(v),3), "max": round(max(v),3), "n": len(v)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("batch")
    a=ap.parse_args(); root=Path(a.batch)
    rows=list(csv.DictReader(open(root/"index.csv",encoding="utf-8")))
    groups=defaultdict(list)
    for r in rows: groups[base_id(r["run_id"])].append(r)

    # per-condition aggregates
    cond={}
    for cid, rs in groups.items():
        d={}
        for m in ALL: d[m]=agg([fnum(r.get(m)) for r in rs])
        ag=[r.get("agreement","") for r in rs if r.get("agreement","")!=""]
        d["agreement_rate"]={"true": sum(1 for x in ag if x=="True"), "n": len(ag)}
        # format-consistent content: embedded-call runs only. The screen batch's
        # UNSUFFIXED first repetitions were content-scored with the isolated call
        # (excluded); every _rN run - including the drill's _r1 - is embedded.
        d["content_fmt"]=agg([fnum(r.get("dqi_justif_content")) for r in rs
                              if r["run_id"].endswith(("_r1","_r2","_r3","_r4","_r5"))])
        # floor: token-share spread from evaluation.json
        spreads=[]
        for r in rs:
            ev=Path(r.get("run_folder","")) if Path(r.get("run_folder","")).exists() else root/r["run_id"]
            ev=ev/"evaluation.json"
            if ev.exists():
                e=json.loads(ev.read_text(encoding="utf-8"))
                ts=e.get("floor",{}).get("token_share",{})
                if ts: spreads.append(max(ts.values())-min(ts.values()))
        d["floor_spread"]=agg(spreads)
        cond[cid]=d

    # noise band from order conditions: per metric, max |order_mean - main_mean|
    noise={}
    for m in QUALITY+OUTCOME:
        mm = cond.get("main",{}).get(m)
        if not mm: continue
        diffs=[abs(cond[o][m]["mean"]-mm["mean"]) for o in ORDERS if cond.get(o,{}).get(m)]
        noise[m]=round(max(diffs),3) if diffs else None

    # condition effects vs baseline, flagged against noise band + baseline spread.
    # Generic over ALL non-baseline, non-order conditions, so the parameter
    # drill-down (param_* / <stakeholder>_<param>_low|high) is picked up
    # automatically alongside the layer screen; LAYERS is kept for ordering.
    effects=[]
    ordered = LAYERS + sorted(c for c in cond if c not in LAYERS and c != "main" and c not in ORDERS)
    for lay in ordered:
        if lay not in cond: continue
        for m in QUALITY+OUTCOME:
            c=cond[lay].get(m); b=cond.get("main",{}).get(m)
            if not c or not b: continue
            eff=round(c["mean"]-b["mean"],3)
            nb=noise.get(m); bsd=b.get("sd")
            exceeds_noise = (nb is not None and abs(eff)>nb)
            beyond_spread = (bsd is not None and abs(eff)>2*bsd) if bsd is not None else None
            effects.append({"condition":lay,"metric":m,"effect_vs_main":eff,
                            "noise_band":nb,"exceeds_noise":exceeds_noise,
                            "gt_2sd_baseline":beyond_spread})

    # settlement terms (available where the outcome judge ran post-patch)
    terms={}
    for cid, rs in groups.items():
        t=[]
        for r in rs:
            ev=Path(r["run_folder"] if Path(r.get("run_folder","")).exists() else root/r["run_id"])/"evaluation.json"
            if not ev.exists(): continue
            e=json.loads(ev.read_text(encoding="utf-8"))
            kt=e.get("outcome",{}).get("key_terms_per_judge")
            if kt: t.append({r["run_id"]: kt})
        if t: terms[cid]=t

    out={"conditions":cond,"noise_band":noise,"layer_effects":effects,"settlement_terms":terms}
    (root/"analysis.json").write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")

    # markdown summary
    L=["# Layer-screen analysis (R-aggregated)",""]
    L.append("## Condition means (mean / sd / n)"); L.append("")
    hdr="| condition | "+" | ".join(m.replace("dqi_","") for m in QUALITY+OUTCOME)+" | agree | rounds | content_fmt | floor_spread |"
    L.append(hdr); L.append("|"+"---|"*(len(QUALITY+OUTCOME)+5))
    drill=sorted(c for c in cond if c!="main" and c not in LAYERS and c not in ORDERS)
    order_out=["main"]+LAYERS+drill+ORDERS
    for cid in order_out:
        if cid not in cond: continue
        cells=[]
        for m in QUALITY+OUTCOME:
            d=cond[cid].get(m)
            cells.append("-" if not d else f"{d['mean']}{'±'+str(d['sd']) if d['sd'] is not None else ''} (n{d['n']})")
        agr=cond[cid]["agreement_rate"]; rd=cond[cid].get("rounds")
        cf=cond[cid].get("content_fmt"); fsp=cond[cid].get("floor_spread")
        extra=f" | {cf['mean'] if cf else '-'} | {fsp['mean'] if fsp else '-'} |"
        L.append(f"| {cid} | "+" | ".join(cells)+f" | {agr['true']}/{agr['n']} | {rd['mean'] if rd else '-'} |"+extra)
    L.append(""); L.append("## Order-noise band per metric")
    L.append(", ".join(f"{m.replace('dqi_','')}: ±{v}" for m,v in noise.items() if v is not None))
    L.append(""); L.append("## Layer effects exceeding the order-noise band")
    sig=[e for e in effects if e["exceeds_noise"]]
    if sig:
        L.append("| condition | metric | effect vs main | noise band | > 2sd baseline |")
        L.append("|---|---|---|---|---|")
        for e in sorted(sig,key=lambda x:-abs(x["effect_vs_main"])):
            L.append(f"| {e['condition']} | {e['metric'].replace('dqi_','')} | {e['effect_vs_main']:+} | ±{e['noise_band']} | {e['gt_2sd_baseline']} |")
    else:
        L.append("none")
    (root/"analysis.md").write_text("\n".join(L),encoding="utf-8")
    print("\n".join(L[:40]))
    print("\nwritten: analysis.json + analysis.md in", root)

if __name__=="__main__":
    main()
