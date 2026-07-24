"""
refresh_content.py - re-score justification_content (v2 anchor) for ALL
contributions of already-judged runs, updating evaluation.json + index.csv.
Other dimensions are untouched (their codebook did not change).

Usage:  python refresh_content.py data/sensitivity_20260723_000046 [--dry]
"""
import json, csv, argparse
from pathlib import Path
from src.evaluation.core import parse_json, CODEBOOK
from src.utils.llm import LLMClient

ANCHOR = CODEBOOK.split("justification_content")[1].split("respect -")[0]
def messages(role, text):
    sysp = ("You are a careful, consistent discourse-quality coder. Score ONE dimension "
            "of ONE contribution on an ordinal 0-2 scale.\n\njustification_content" + ANCHOR +
            '\nReturn ONLY JSON: {"rationale":"one short sentence","justification_content":0}')
    return [{"role":"system","content":sysp},
            {"role":"user","content":"STAKEHOLDER ROLE: %s\n\nCONTRIBUTION:\n%s" % (role, text[:18000])}]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("target"); ap.add_argument("--dry",action="store_true")
    ap.add_argument("--judges",default="claude-sonnet-5,gpt-5.4")
    a=ap.parse_args()
    if a.dry:
        from src.evaluation.core import StubJudge
        judges=[StubJudge("A",0),StubJudge("B",1)]
    else:
        judges=[LLMClient(m.strip(),0.0,20260714,1024) for m in a.judges.split(",")]
    import yaml
    root=Path(a.target)
    idx_rows=list(csv.DictReader(open(root/"index.csv",encoding="utf-8")))
    for rf in sorted(root.iterdir()):
        ev=rf/"evaluation.json"
        if not ev.exists(): continue
        e=json.loads(ev.read_text(encoding="utf-8"))
        if e.get("content_anchor")=="v2":
            print("  %s: already v2, skipped" % rf.name); continue
        cfg=yaml.safe_load((rf/"config_used.yaml").read_text(encoding="utf-8")) if (rf/"config_used.yaml").exists() else None
        roles={s["key"]:"%s (%s)"%(s["name"],s["role"]) for s in (cfg["stakeholders"] if cfg else [])}
        new_vals=[]
        for c in e["contribution_scores"]:
            text=(rf/"outputs"/f"round{c['round']}_{c['stakeholder']}.txt").read_text(encoding="utf-8")
            role=roles.get(c["stakeholder"], c["stakeholder"])
            for ji,jd in enumerate(judges):
                d=parse_json(jd.call(messages(role,text),"cv2_%s_%s_r%s"%(rf.name,c["stakeholder"],c["round"])).text)
                v=d.get("justification_content")
                c["judges"][ji]["justification_content"]=v if isinstance(v,(int,float)) else None
            vals=[j["justification_content"] for j in c["judges"] if isinstance(j.get("justification_content"),(int,float))]
            if vals: new_vals.append(sum(vals)/len(vals))
        # update aggregates
        e["dqi"]["justification_content"]=round(sum(new_vals)/len(new_vals),3) if new_vals else None
        for k in e["per_stakeholder"]:
            sv=[ (lambda vs: sum(vs)/len(vs) if vs else None)([j["justification_content"] for c in e["contribution_scores"] if c["stakeholder"]==k for j in c["judges"] if isinstance(j.get("justification_content"),(int,float))]) ][0]
            e["per_stakeholder"][k]["justification_content"]=round(sv,3) if sv is not None else None
        e["content_anchor"]="v2"
        ev.write_text(json.dumps(e,indent=2,ensure_ascii=False),encoding="utf-8")
        for r in idx_rows:
            if r["run_id"]==rf.name:
                r["dqi_justif_content"]=e["dqi"]["justification_content"]
        print("  %s: content -> %s" % (rf.name, e["dqi"]["justification_content"]), flush=True)
    with open(root/"index.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(idx_rows[0].keys())); w.writeheader(); w.writerows(idx_rows)
    print("index.csv content column refreshed")

if __name__=="__main__":
    main()
