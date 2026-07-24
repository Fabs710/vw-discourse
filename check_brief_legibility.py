"""
check_brief_legibility.py - back-translation check of the operationalization.

Gives a judge LLM each generated agent brief (numbers never shown) and asks it to
ESTIMATE all eleven slider values (1-10). Recovery quality (Spearman rho + MAE per
parameter) measures whether the briefs communicate the parameters legibly.
Covers the six baseline briefs plus the eight layer-extreme variants (62 briefs).

Usage:  python check_brief_legibility.py            # real judge (default gpt-5.4)
        python check_brief_legibility.py --dry      # stub
Writes: data/brief_legibility.json
"""
import json, argparse, copy
from pathlib import Path
import yaml
from src.utils.config_loader import load_config
from src.utils.prompt_builder import build_agent_brief
from src.models.stakeholder import SimulationMode
from src.evaluation.core import parse_json
from src.utils.llm import LLMClient

PARAMS=["power","legitimacy","urgency","social_preference","risk_preference","time_preference",
        "flexibility","dependency","assertiveness","cooperativeness","relational_prior"]
LAYERS={"salience":["power","legitimacy","urgency"],
        "motivation":["social_preference","risk_preference","time_preference"],
        "position":["flexibility","dependency"],
        "interaction":["assertiveness","cooperativeness"]}

def messages(brief):
    sysp=("You are analysing the system prompt of a simulated stakeholder agent. The persona was "
          "generated from eleven numeric parameters (1-10 scales). Estimate each parameter value "
          "from the text alone. Scales: power/legitimacy/urgency = standing (1 low, 10 high); "
          "social_preference (1 purely self-regarding, 10 fully other-regarding); risk_preference "
          "(1 highly risk-averse, 10 risk-seeking); time_preference (1 short-term, 10 long-term); "
          "flexibility (1 rigid, 10 highly flexible); dependency (1 independent/strong alternatives, "
          "10 fully dependent); assertiveness (1 passive, 10 dominant); cooperativeness (1 "
          "uncooperative, 10 highly cooperative); relational_prior (1 hostile/distrustful, 10 "
          "trusting/allied). Return ONLY JSON: "
          '{"power":5,...} with ALL eleven keys and integer estimates 1-10.')
    return [{"role":"system","content":sysp},{"role":"user","content":"AGENT BRIEF:\n\n"+brief}]

def variants():
    base=yaml.safe_load(Path("config/simulation_config.yaml").read_text(encoding="utf-8"))
    out=[("baseline", base)]
    for lay,ps in LAYERS.items():
        for val,tag in ((1,"low"),(10,"high")):
            raw=copy.deepcopy(base)
            for s in raw["stakeholders"]:
                for p in ps: s[p]["value"]=val
            out.append((f"layer_{lay}_{tag}", raw))
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--dry",action="store_true")
    ap.add_argument("--judge",default="gpt-5.4")
    a=ap.parse_args()
    if a.dry:
        class Stub:
            def call(self,m,l):
                from src.utils.llm import LLMResponse
                return LLMResponse(json.dumps({p:5 for p in PARAMS}),"stub","s","s",1,None,1,"stop",0.0)
        judge=Stub()
    else:
        judge=LLMClient(a.judge,0.0,20260714,1024)
    rows=[]
    for tag,raw in variants():
        tmp=Path("data/_legib_cfg.yaml"); tmp.write_text(yaml.safe_dump(raw,sort_keys=False,allow_unicode=True),encoding="utf-8")
        cfg=load_config(str(tmp))
        for k in cfg.roundtable.turn_order:
            sh=cfg.get_stakeholder(k)
            brief=build_agent_brief(sh,SimulationMode.ROUNDTABLE,2,False)
            est=parse_json(judge.call(messages(brief),f"legib_{tag}_{k}").text)
            row={"condition":tag,"stakeholder":k}
            for p in PARAMS:
                row[p+"_true"]=getattr(sh,p).value
                v=est.get(p)
                row[p+"_est"]=v if isinstance(v,(int,float)) else None
            rows.append(row)
            print("  %-22s %-14s ok" % (tag,k), flush=True)
    Path("data/_legib_cfg.yaml").unlink(missing_ok=True)
    Path("data/brief_legibility.json").write_text(json.dumps(rows,indent=2),encoding="utf-8")
    # summary stats
    def spearman(x,y):
        n=len(x)
        rx=sorted(range(n),key=lambda i:x[i]); ry=sorted(range(n),key=lambda i:y[i])
        r1=[0]*n; r2=[0]*n
        for r,i in enumerate(rx): r1[i]=r
        for r,i in enumerate(ry): r2[i]=r
        mx=sum(r1)/n; my=sum(r2)/n
        num=sum((r1[i]-mx)*(r2[i]-my) for i in range(n))
        den=(sum((r1[i]-mx)**2 for i in range(n))*sum((r2[i]-my)**2 for i in range(n)))**0.5
        return num/den if den else float("nan")
    print("\nparameter            n    rho    MAE")
    for p in PARAMS:
        pairs=[(r[p+"_true"],r[p+"_est"]) for r in rows if r[p+"_est"] is not None]
        if not pairs: continue
        t=[a for a,_ in pairs]; e=[b for _,b in pairs]
        mae=sum(abs(a-b) for a,b in pairs)/len(pairs)
        print(f"{p:20s} {len(pairs):3d}  {spearman(t,e):5.2f}  {mae:5.2f}")
    print("\nwritten: data/brief_legibility.json")

if __name__=="__main__":
    main()
