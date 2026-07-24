"""
rejudge_content.py - re-score ONLY justification_content (refined v2 anchor)
on the 28 human-coding sample contributions, with both judges.

Usage:  python rejudge_content.py                 # real judges
        python rejudge_content.py --dry           # stub
Writes: data/human_coding_content_rejudge.json
"""
import json, argparse
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
    ap=argparse.ArgumentParser(); ap.add_argument("--dry",action="store_true")
    ap.add_argument("--judges",default="claude-sonnet-5,gpt-5.4")
    a=ap.parse_args()
    if a.dry:
        from src.evaluation.core import StubJudge
        judges=[StubJudge("A",0),StubJudge("B",1)]
    else:
        judges=[LLMClient(m.strip(),0.0,20260714,1024) for m in a.judges.split(",")]
    key=json.load(open("data/human_coding_key.json"))
    import yaml
    out=[]
    for e in key:
        rf=Path("data/sensitivity_20260723_000046")/e["cond"]
        text=(rf/"outputs"/f"round{e['round']}_{e['stakeholder']}.txt").read_text(encoding="utf-8")
        cfg=yaml.safe_load((rf/"config_used.yaml").read_text(encoding="utf-8"))
        role=next("%s (%s)"%(s["name"],s["role"]) for s in cfg["stakeholders"] if s["key"]==e["stakeholder"])
        rec={"id":e["id"],"scores":[]}
        for jd in judges:
            d=parse_json(jd.call(messages(role,text),"content_v2_%s"%e["id"]).text)
            v=d.get("justification_content")
            rec["scores"].append(v if isinstance(v,(int,float)) else None)
        out.append(rec)
        print("  %s -> %s" % (e["id"], rec["scores"]), flush=True)
    Path("data/human_coding_content_rejudge.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
    print("written: data/human_coding_content_rejudge.json")

if __name__=="__main__":
    main()
