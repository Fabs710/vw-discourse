"""
make_figures.py - generates the thesis figures from the frozen run data.

Style: Okabe-Ito colourblind-safe palette, distinguishable in greyscale
(series differ in hatch/marker as well as hue). 300 dpi PNG for Word.

Usage:  python make_figures.py
Output: ../Current Draft and Structure/Figures/*.png
"""
import json, glob, math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import statistics as st

OUT = os.path.join("..", "Current Draft and Structure", "Figures")
os.makedirs(OUT, exist_ok=True)

BLUE="#0072B2"; ORANGE="#E69F00"; GREEN="#009E73"; VERM="#D55E00"
SKY="#56B4E9"; PURPLE="#CC79A7"; GREY="#4D4D4D"; LGREY="#BFBFBF"
plt.rcParams.update({
    "font.family":"DejaVu Sans","font.size":9,"axes.edgecolor":GREY,
    "axes.labelcolor":"#222222","text.color":"#222222",
    "xtick.color":GREY,"ytick.color":GREY,"axes.grid":False,
    "figure.dpi":300,"savefig.dpi":300,"savefig.bbox":"tight",
})
def save(fig, name):
    p=os.path.join(OUT,name); fig.savefig(p, facecolor="white"); plt.close(fig)
    print("  wrote", name)

def box(ax,x,y,w,h,label,fc,ec=None,fs=8.5,bold=False,tc="#222222"):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.012,rounding_size=0.02",
        linewidth=1.1,facecolor=fc,edgecolor=ec or GREY,zorder=2))
    ax.text(x+w/2,y+h/2,label,ha="center",va="center",fontsize=fs,zorder=3,
            fontweight="bold" if bold else "normal",color=tc,linespacing=1.35)

def arrow(ax,p1,p2,style="-|>",color=None,lw=1.2,ls="-",rad=0.0):
    ax.add_patch(FancyArrowPatch(p1,p2,arrowstyle=style,mutation_scale=11,
        linewidth=lw,color=color or GREY,linestyle=ls,zorder=1,
        connectionstyle="arc3,rad=%s"%rad))

# ---------------------------------------------------------------- A1 framework
def pbox(ax,x,y,w,h,title,sub,col,dashed=False):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.010,rounding_size=0.02",
        linewidth=1.15,facecolor=col+"1C",edgecolor=col,zorder=2,
        linestyle=(0,(3,2)) if dashed else "-"))
    ax.text(x+w/2,y+h*0.63,title,ha="center",va="center",fontsize=8.4,fontweight="bold",zorder=3)
    if sub:
        ax.text(x+w/2,y+h*0.28,sub,ha="center",va="center",fontsize=6.8,color=GREY,zorder=3)

def fig_framework():
    fig,ax=plt.subplots(figsize=(11.4,6.1)); ax.set_xlim(0,11.5); ax.set_ylim(0.85,6.75); ax.axis("off")
    ax.text(5.75,6.55,"The eleven-parameter framework on a belief-desire-intention spine",
            ha="center",fontsize=12,fontweight="bold")
    ax.text(0.78,6.26,"BDI role",fontsize=7.0,color=GREY,fontweight="bold",ha="center")
    ax.text(11.42,6.26,"theory anchor",fontsize=7.0,color=GREY,fontweight="bold",ha="right")
    rows=[("BELIEF","standing","Salience layer",
            [("power","capacity to impose"),("legitimacy","recognised claim"),("urgency","time pressure")],
            "Mitchell, Agle & Wood (1997)",BLUE),
          ("DESIRE","","Motivation layer",
            [("social_preference","regard for others"),("risk_preference","tolerance of uncertainty"),
             ("time_preference","near vs long horizon")],
            "Fehr & Schmidt (1999); Kahneman &\nTversky (1979); Frederick et al. (2002)",GREEN),
          ("INTENTION","","Position layer",
            [("flexibility","willingness to move"),("dependency","strength of alternatives")],
            "Fisher & Ury (1981);\nWhite & Neale (1991)",ORANGE),
          ("EXPRESSION","","Interaction layer",
            [("assertiveness","pursuit of own concerns"),("cooperativeness","attention to others")],
            "Thomas (1992)",VERM),
          ("BELIEF","relations","Belief prior",
            [("relational_prior","trust / adversarial stance")],
            "Rao & Georgeff (1995);\nGeorgeff et al. (1999)",PURPLE)]
    top=5.35; h=0.80; gap=0.11
    for i,(spine,qual,layer,params,theory,col) in enumerate(rows):
        y=top-i*(h+gap)
        ax.add_patch(Rectangle((0.12,y),1.32,h,facecolor=col,alpha=0.14,edgecolor=col,linewidth=1.0,zorder=1))
        ax.text(0.78,y+h*(0.60 if qual else 0.5),spine,ha="center",va="center",fontsize=7.6,
                fontweight="bold",color=col)
        if qual: ax.text(0.78,y+h*0.26,qual,ha="center",va="center",fontsize=6.4,color=col,style="italic")
        ax.text(1.58,y+h/2,layer,ha="left",va="center",fontsize=9.4,fontweight="bold")
        x=3.32
        for pn,pd in params:
            pbox(ax,x,y+0.06,1.78,h-0.12,pn,pd,col); x+=1.90
        if layer=="Interaction layer":
            pbox(ax,x,y+0.06,1.78,h-0.12,"-> conflict_mode","derived, never hand-assigned",VERM,dashed=True)
        ax.text(11.42,y+h/2,theory,ha="right",va="center",fontsize=6.8,color=GREY,style="italic",linespacing=1.4)
    ax.plot([3.18,3.18],[top-4*(h+gap),top+h],color=LGREY,linewidth=0.9,zorder=0)
    ax.plot([9.02,9.02],[top-4*(h+gap),top+h],color=LGREY,linewidth=0.9,zorder=0)
    ax.text(0.12,1.18,"Four functional layers carry the spine; the belief prior completes it. Every parameter is a "
        "1-10 slider rendered\ninto fixed verbal text before any model call (Figure 5.5).",
        fontsize=7.3,color=GREY,style="italic",va="top")
    save(fig,"Fig 5.3 - Parameter Framework.png")

# ------------------------------------------------------------ B3 slider bands
def fig_bands():
    fig,ax=plt.subplots(figsize=(9.4,3.5)); ax.set_xlim(0.3,10.7); ax.set_ylim(0,3.5); ax.axis("off")
    ax.text(5.5,3.3,"From slider value to prompt text: the banded descriptor mapping",
            ha="center",fontsize=11.5,fontweight="bold")
    bands=[(1,3,"LOW","rigid, unwilling to move\nfar from your position",BLUE),
           (4,6,"MEDIUM","moderately flexible, open to partial\nsolutions if arguments are compelling",GREEN),
           (7,10,"HIGH","highly flexible, open to\nsubstantially revising your position",ORANGE)]
    for lo,hi,lab,txt,col in bands:
        ax.add_patch(Rectangle((lo-0.42,1.55),(hi-lo)+0.84,0.62,facecolor=col,alpha=0.18,
                               edgecolor=col,linewidth=1.2))
        ax.text((lo+hi)/2,2.32,lab,ha="center",fontsize=8.5,fontweight="bold",color=col)
        ax.text((lo+hi)/2,1.86,'"%s"'%txt,ha="center",va="center",fontsize=7.0,color="#222222")
    for v in range(1,11):
        ax.plot([v,v],[1.40,1.52],color=GREY,lw=0.9)
        ax.text(v,1.18,str(v),ha="center",fontsize=8,color=GREY)
    ax.annotate("",xy=(10.55,1.46),xytext=(0.45,1.46),arrowprops=dict(arrowstyle="-",color=GREY,lw=1.0))
    ax.text(5.5,0.92,"slider value (example: the flexibility parameter)",ha="center",fontsize=7.8,
            color=GREY,style="italic")
    ax.scatter([5],[2.62],marker="v",s=70,color=GREY,zorder=4)
    ax.text(5,2.80,"calibrated value",ha="center",fontsize=7.4,color=GREY)
    for xv,col,lab in [(2,BLUE,"low pole"),(8,ORANGE,"high pole")]:
        ax.scatter([xv],[2.62],marker="v",s=70,color=col,zorder=4)
        ax.text(xv,2.80,lab,ha="center",fontsize=7.4,color=col,fontweight="bold")
    ax.text(0.35,0.50,"Within a band the wording is identical, so a change of value is invisible to the model "
        "(e.g. 5 -> 6).\nThe drill-down therefore admits a sweep only where BOTH poles cross a band boundary "
        "from the calibrated value, as shown here.",fontsize=7.6,color="#222222",va="top")
    save(fig,"Fig 5.5 - Slider to Descriptor Bands.png")

# ------------------------------------------------------- B1 legibility recovery
def spearman(x,y):
    def rank(v):
        o=sorted(range(len(v)),key=lambda i:v[i]); r=[0.0]*len(v); i=0
        while i<len(o):
            j=i
            while j+1<len(o) and v[o[j+1]]==v[o[i]]: j+=1
            a=(i+j)/2+1
            for k in range(i,j+1): r[o[k]]=a
            i=j+1
        return r
    a,b=rank(x),rank(y); ma,mb=st.mean(a),st.mean(b)
    num=sum((p-ma)*(q-mb) for p,q in zip(a,b))
    da=sum((p-ma)**2 for p in a)**.5; db=sum((q-mb)**2 for q in b)**.5
    return num/(da*db) if da and db else float("nan")

def fig_legibility():
    L=json.load(open(os.path.join("data","brief_legibility.json"),encoding="utf-8"))
    params=["power","legitimacy","urgency","social_preference","risk_preference","time_preference",
            "flexibility","dependency","assertiveness","cooperativeness","relational_prior"]
    stats=[]
    for p in params:
        t=[r[p+"_true"] for r in L]; e=[r[p+"_est"] for r in L]
        rho=spearman(t,e); mae=st.mean(abs(a-b) for a,b in zip(t,e))
        stats.append((p,rho,mae))
    stats.sort(key=lambda s:s[1])
    fig,(ax1,ax2)=plt.subplots(1,2,figsize=(9.6,4.6),gridspec_kw={"width_ratios":[1.35,1]})
    fig.subplots_adjust(bottom=0.30)
    ys=range(len(stats)); names=[s[0] for s in stats]
    for i,(p,rho,mae) in enumerate(stats):
        col=VERM if rho<0.7 else (BLUE if rho<0.85 else GREEN)
        ax1.plot([0,rho],[i,i],color=col,lw=2.0,zorder=1,alpha=0.55)
        ax1.scatter([rho],[i],s=52,color=col,zorder=3,edgecolor="white",linewidth=0.8)
        ax1.text(rho+0.018,i,"%.2f"%rho,va="center",fontsize=7.4,color=col)
    ax1.set_yticks(list(ys)); ax1.set_yticklabels(names,fontsize=8)
    ax1.set_xlim(0,1.0); ax1.set_xlabel("Spearman rho (estimated vs true value), 54 briefs")
    ax1.set_title("Parameter recovery",fontsize=10,fontweight="bold",loc="left")
    ax1.axvline(0.7,color=LGREY,ls=":",lw=1.0)
    ax1.spines[["top","right"]].set_visible(False)
    for i,(p,rho,mae) in enumerate(stats):
        col=VERM if mae>1.3 else (BLUE if mae>0.9 else GREEN)
        ax2.barh(i,mae,color=col,alpha=0.75,height=0.55,edgecolor=col,linewidth=0.8)
        ax2.text(mae+0.03,i,"%.2f"%mae,va="center",fontsize=7.4,color=col)
    ax2.set_yticks(list(ys)); ax2.set_yticklabels([]); ax2.set_xlim(0,2.0)
    ax2.set_xlabel("mean absolute error (points on the 1-10 scale)")
    ax2.set_title("Recovery precision",fontsize=10,fontweight="bold",loc="left")
    ax2.spines[["top","right"]].set_visible(False)
    fig.suptitle("Brief-legibility check: do the generated briefs communicate the parameters they encode?",
                 fontsize=11.5,fontweight="bold",y=1.01)
    fig.text(0.5,-0.10,"All eleven parameters recover positively (rho .63-.87). Pooled recovery is near-ceiling at the "
        "calibrated values (rho .92, MAE 0.71)\nand attenuates under extreme manipulation (rho .81, MAE 1.12) - the "
        "quantified footprint of the banded mapping. Power and dependency are weakest:\ntheir calibration sentences "
        "carry structural hedges, a property of the case calibration rather than of the mapping.",
        ha="center",fontsize=7.3,color=GREY)
    save(fig,"Fig 5.6 - Brief Legibility Recovery.png")

# ------------------------------------------------------- A3 validation fidelity
def fig_fidelity():
    runs=["run_20260722_202409","run_20260722_202817","run_20260722_203247"]
    profs=[json.load(open(os.path.join("data",r,"validation_scores.json"),encoding="utf-8"))["profile"] for r in runs]
    claims=[("P1","Funder dominance","E"),("P2","Management accommodation","E"),
            ("P3","Labour concession-for-security","E"),("P5","Co-funder conditionality","E"),
            ("C1","Creditors-vs-labour axis","E"),("C2","Funder-vs-claimants axis","E"),
            ("P4","Bondholder endgame","H"),("C3","Consensual failure / court route","H"),
            ("O2","Deep operational cuts","H"),("O1","Ownership outcome severity","H")]
    fig,ax=plt.subplots(figsize=(9.4,5.0))
    ys=[]; y=0
    for i,(cid,lab,grp) in enumerate(claims):
        if i==6: y-=0.85
        ys.append(y); y-=1
    for (cid,lab,grp),yy in zip(claims,ys):
        vals=[p[cid] for p in profs]; m=st.mean(vals)
        col=BLUE if grp=="E" else ORANGE
        ax.barh(yy,m,height=0.62,color=col,alpha=0.30 if grp=="E" else 0.45,
                edgecolor=col,linewidth=1.2,hatch=None if grp=="E" else "//",zorder=2)
        ax.scatter(vals,[yy+0.235]*len(vals),s=18,color=col,zorder=4,edgecolor="white",linewidth=0.6)
        ax.text(m+0.045,yy,"%.2f"%m,va="center",fontsize=7.8,color=col,fontweight="bold")
        ax.text(-0.06,yy,"%s  %s"%(cid,lab),ha="right",va="center",fontsize=8.2)
    ax.axvline(2.0,color=LGREY,ls="--",lw=1.0)
    allm=st.mean([p[c[0]] for p in profs for c in claims])
    ax.axvline(allm,color=GREY,ls=":",lw=1.2)
    ax.text(allm,1.15,"batch mean %.2f"%allm,ha="center",fontsize=7.6,color=GREY)
    ax.text(2.0,1.15,"maximum",ha="center",fontsize=7.6,color=GREY)
    gm=st.mean([p[c[0]] for p in profs for c in claims if c[2]=="E"])
    gh=st.mean([p[c[0]] for p in profs for c in claims if c[2]=="H"])
    ax.text(2.28,ys[2],"ENACTMENT\npartly calibrated in\nmean %.2f"%gm,fontsize=8,color=BLUE,
            fontweight="bold",va="center")
    ax.text(2.28,ys[8],"HELD OUT\ngenuinely predictive\nmean %.2f"%gh,fontsize=8,color=ORANGE,
            fontweight="bold",va="center")
    ax.set_xlim(0,2.15); ax.set_ylim(min(ys)-0.7,1.6); ax.set_yticks([])
    ax.set_xticks([0,0.5,1.0,1.5,2.0])
    ax.set_xlabel("fidelity score against the documented record (0 = contradicts, 2 = clearly consistent)")
    ax.spines[["top","right","left"]].set_visible(False)
    ax.set_title("Validation case: fidelity profile across ten documented claims",
                 fontsize=11.5,fontweight="bold",loc="left")
    fig.text(0.5,-0.02,"Bars show the two-judge mean over three runs; dots are the individual runs. Claims whose "
        "parameters were calibrated from the record (enactment)\nsit at or near ceiling; the genuinely held-out "
        "claims fall away, with the documented ownership outcome (O1) not reproduced.",
        ha="center",fontsize=7.3,color=GREY)
    save(fig,"Fig 9.7 - Validation Fidelity Profile.png")

# ------------------------------------------------------------- A4 eval pipeline
def fig_pipeline():
    fig,ax=plt.subplots(figsize=(11.4,5.9)); ax.set_xlim(0,11.5); ax.set_ylim(0,6.1); ax.axis("off")
    ax.text(5.75,5.86,"From transcript to reported effect: the evaluation pipeline",
            ha="center",fontsize=12,fontweight="bold")
    box(ax,0.15,4.28,1.42,0.92,"frozen run\nartifacts",SKY+"30",SKY,7.8)
    box(ax,1.92,4.72,2.05,0.60,"QUALITY family\ncontribution-level DQI",BLUE+"20",BLUE,7.5,True)
    box(ax,1.92,3.98,2.05,0.60,"OUTCOME family\nagreement, movement, terms",ORANGE+"20",ORANGE,7.1,True)
    box(ax,1.92,3.24,2.05,0.60,"PARTICIPATION\nfloor metrics (not judged)",GREEN+"20",GREEN,7.3,True)
    box(ax,4.32,5.02,1.78,0.50,"judge A - OpenAI family",BLUE+"14",BLUE,7.3)
    box(ax,4.32,4.42,1.78,0.50,"judge B - Anthropic family",BLUE+"14",BLUE,7.3)
    box(ax,6.45,4.72,1.42,0.60,"jury mean\nper dimension",BLUE+"20",BLUE,7.5)
    box(ax,6.45,3.98,1.42,0.60,"per-run\noutcome values",ORANGE+"20",ORANGE,7.5)
    box(ax,8.22,4.30,1.62,0.94,"condition aggregate\nover R repetitions\n(mean, SD, n)","#F2F2F2",GREY,7.5,True)
    box(ax,7.05,2.62,3.95,0.74,"DOUBLE SCREENING FILTER\n(1) outside the order-noise band  AND  (2) beyond twice the baseline SD",
        VERM+"16",VERM,7.3,True)
    box(ax,7.05,1.62,3.95,0.62,"reported effect:   robust  |  suggestive  |  null",VERM+"26",VERM,8.2,True)
    arrow(ax,(1.57,4.74),(1.92,5.02)); arrow(ax,(1.57,4.74),(1.92,4.28)); arrow(ax,(1.57,4.74),(1.92,3.54))
    arrow(ax,(3.97,5.02),(4.32,5.27)); arrow(ax,(3.97,5.02),(4.32,4.67))
    arrow(ax,(6.10,5.27),(6.45,5.14)); arrow(ax,(6.10,4.67),(6.45,4.90))
    arrow(ax,(3.97,4.28),(6.45,4.28))
    arrow(ax,(7.87,5.02),(8.22,4.95)); arrow(ax,(7.87,4.28),(8.22,4.60))
    arrow(ax,(9.03,4.30),(9.03,3.36)); arrow(ax,(9.03,2.62),(9.03,2.24))
    ax.text(1.95,3.06,"reported descriptively; never enters the screening filter",fontsize=6.8,color=GREEN,
            style="italic",va="center",ha="left")
    # instrument-validation strip
    ax.add_patch(Rectangle((0.15,0.42),6.30,1.42,facecolor=PURPLE,alpha=0.06,
                           edgecolor=PURPLE,linewidth=1.0,linestyle=(0,(4,2)),zorder=0))
    ax.text(0.32,1.58,"INSTRUMENT VALIDATION - completed before any behavioural claim rests on the numbers",
            fontsize=7.4,color=PURPLE,fontweight="bold")
    box(ax,0.32,0.62,1.88,0.82,"brief legibility\n54 briefs,\nback-translation",PURPLE+"18",PURPLE,7.1)
    box(ax,2.36,0.62,1.88,0.82,"human anchor\n28 contributions,\nblind; v1 -> v2 repair",PURPLE+"18",PURPLE,7.1)
    box(ax,4.40,0.62,1.88,0.82,"judge-bias checks\nverbosity, self-preference\n(576 / 840 records)",PURPLE+"18",PURPLE,7.1)
    arrow(ax,(1.26,1.44),(1.26,4.28),ls=(0,(4,2)),color=PURPLE,lw=1.0,rad=0.0)
    arrow(ax,(3.30,1.44),(4.90,4.42),ls=(0,(4,2)),color=PURPLE,lw=1.0,rad=-0.16)
    arrow(ax,(5.34,1.44),(5.34,4.42),ls=(0,(4,2)),color=PURPLE,lw=1.0,rad=-0.10)
    ax.text(0.15,0.18,"Evaluation runs only on frozen artifacts - it never touches the simulation.",
            fontsize=7.2,color=GREY,style="italic")
    save(fig,"Fig 8.1 - Evaluation Pipeline.png")

# -------------------------------------------------------- B2 programme map
def fig_programme():
    fig,ax=plt.subplots(figsize=(11.0,5.8)); ax.set_xlim(0,11.0); ax.set_ylim(0,6.35); ax.axis("off")
    ax.text(5.5,6.14,"The experimental programme: conditions, repetitions and run counts",
            ha="center",fontsize=12,fontweight="bold")
    ax.text(8.06,5.84,"reps",ha="center",fontsize=7.6,color=GREY,fontweight="bold")
    ax.text(8.92,5.84,"runs",ha="center",fontsize=7.6,color=GREY,fontweight="bold")
    ax.text(9.95,5.84,"status",ha="left",fontsize=7.6,color=GREY,fontweight="bold")
    rows=[("baseline (main scenario)","R = 5","5",BLUE,"done",BLUE),
          ("layer screen: 4 layers x 2 poles","R = 3","24",BLUE,"done",BLUE),
          ("order robustness: reversed, random","R = 3","6",BLUE,"done",BLUE),
          ("parameter drill-down: 9 sweeps x 2 poles","R = 3","54",GREEN,"done",GREEN),
          ("confirmatory top-up: 4 sweeps to R = 6","R = 6","29",GREEN,"done",GREEN),
          ("rounds-cap check (6 rounds)","R = 3","3",PURPLE,"done",PURPLE),
          ("cross-model replication (2nd engine)","subset","9",None,"running",GREY)]
    y0=5.30; h=0.475; gap=0.105
    ys=[]
    for i,(lab,rep,n,col,status,scol) in enumerate(rows):
        y=y0-i*(h+gap); ys.append(y)
        c=col or GREY
        box(ax,3.30,y,4.35,h,lab,(c+"16") if col else "#F4F4F4",c,7.9)
        ax.text(8.06,y+h/2,rep,ha="center",va="center",fontsize=7.5,color=GREY)
        strong=n.isdigit()
        box(ax,8.52,y+0.03,0.80,h-0.06,n,(c+"26") if strong else "#EFEFEF",c,8.8 if strong else 7.2,strong)
        ax.text(9.95,y+h/2,status,ha="left",va="center",fontsize=7.2,color=scol,style="italic")
    yv=ys[-1]-(h+gap)-0.16
    box(ax,3.30,yv,4.35,h,"3 runs x 10 documented fidelity claims x 2 judges",ORANGE+"16",ORANGE,7.9)
    ax.text(8.06,yv+h/2,"R = 3",ha="center",va="center",fontsize=7.5,color=GREY)
    box(ax,8.52,yv+0.03,0.80,h-0.06,"3",ORANGE+"26",ORANGE,8.8,True)
    ax.text(9.95,yv+h/2,"done",ha="left",va="center",fontsize=7.2,color=ORANGE,style="italic")
    box(ax,0.15,ys[2]+0.02,2.45,0.92,"SENSITIVITY CASE\nVW 2024 restructuring\noutcome withheld",BLUE+"20",BLUE,8.0,True)
    box(ax,0.15,yv-0.02,2.45,0.72,"VALIDATION CASE\nGM 2009 restructuring\noutcome documented",ORANGE+"20",ORANGE,8.0,True)
    ax.plot([2.92,2.92],[ys[-1]+h/2,ys[0]+h/2],color=BLUE,lw=1.2,zorder=1)
    arrow(ax,(2.60,ys[2]+0.48),(2.92,ys[2]+0.48),color=BLUE)
    for y in ys: arrow(ax,(2.92,y+h/2),(3.30,y+h/2),color=BLUE)
    arrow(ax,(2.60,yv+h/2),(3.30,yv+h/2),color=ORANGE)
    ax.plot([8.42,8.42],[yv-0.05,ys[0]+h+0.05],color=LGREY,lw=0.8,zorder=0)
    ax.text(0.15,0.30,"121 runs analysed: 35 on the layer screen (baseline + poles + order), 83 across the drill-down and its "
        "confirmatory top-up, 3 on the round-cap check;\n3 on the validation case, with 9 cross-model runs executing. "
        "Every condition changes exactly one thing against the baseline - speaking order, round cap,\nseed and model "
        "snapshot are held constant throughout, and the round-cap runs sit in their own batch so they can never pool.",
        fontsize=7.0,color=GREY,va="center")
    save(fig,"Fig 7.5 - Experimental Programme.png")

if __name__=="__main__":
    print("building figures ->", OUT)
    fig_framework(); fig_bands(); fig_legibility(); fig_fidelity(); fig_pipeline(); fig_programme()
    print("done.")
