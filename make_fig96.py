"""
make_fig96.py - Figure 9.6, the cross-model comparison.

Kept separate from make_figures_results.py because it is the only figure that reads
TWO batches: the pinned gpt-5.4-mini baseline and the claude-sonnet-5 replication.
Same Okabe-Ito palette and 300 dpi output as the other ten figures.

Usage:  python make_fig96.py
"""
import csv, json, os, math, itertools
import re
import statistics as st
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.join("..", "Current Draft and Structure", "Figures")
os.makedirs(OUT, exist_ok=True)
BLUE="#0072B2"; ORANGE="#E69F00"; GREEN="#009E73"; VERM="#D55E00"
SKY="#56B4E9"; PURPLE="#CC79A7"; GREY="#4D4D4D"; LGREY="#BFBFBF"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"axes.edgecolor":GREY,
    "axes.labelcolor":"#222222","text.color":"#222222","xtick.color":GREY,"ytick.color":GREY,
    "axes.grid":False,"figure.dpi":300,"savefig.dpi":300,"savefig.bbox":"tight"})

A = Path("data/sensitivity_20260723_000046")     # gpt-5.4-mini
B = Path("data/sensitivity_20260726_172041")     # claude-sonnet-5

_REP = re.compile(r"_r\d+$")   # any repetition width - _r10 broke the old slice

def base(rid):
    rid = _REP.sub("", rid)
    return rid.split("__", 1)[0]

def rows(p, cond):
    return [r for r in csv.DictReader(open(p/"index.csv", encoding="utf-8")) if base(r["run_id"]) == cond]

def col(rs, c):
    out=[]
    for r in rs:
        try: out.append(float(r[c]))
        except (TypeError, ValueError): pass
    return out

def exact_p(a, b):
    obs=abs(st.mean(a)-st.mean(b)); pool=list(a)+list(b); n=len(a); hits=tot=0
    for idx in itertools.combinations(range(len(pool)), n):
        x=[pool[i] for i in idx]; y=[pool[i] for i in range(len(pool)) if i not in idx]
        tot+=1
        if abs(st.mean(x)-st.mean(y)) >= obs-1e-12: hits+=1
    return hits/tot

# Every delta and p is recomputed from the batches below. The third tuple element used
# to carry a hard-coded delta from the five-run comparison (+0.256 respect, -32 chars and
# so on); it was never read, and it disagreed with the figure it sat in once the baseline
# was corrected to ten runs. Removed rather than updated, so there is one source of truth.
# dqi_justif_level was also missing from the list, which mattered once it reached p<.05
# on the corrected baseline - a figure that silently drops the one measure whose verdict
# changed is the wrong figure.
MET=[("dqi_respect","respect"),("position_move","position movement"),
     ("experts","experts summoned"),("red_line_declarations","red-line declarations"),
     ("dqi_justif_content","justification content"),("dqi_constructive","constructive politics"),
     ("dqi_justif_level","justification level"),
     ("dqi_individuation","individuation"),("transcript_chars","transcript length")]

a_main, b_main = rows(A,"main"), rows(B,"main")
floor = 1/math.comb(len(a_main)+len(b_main), len(a_main))

fig, axes = plt.subplots(1, 3, figsize=(11.2, 4.1),
                         gridspec_kw={"width_ratios":[1.5,0.95,0.95]})

# ---- panel 1: standardised difference, mini vs sonnet -------------------------
ax=axes[0]; labs=[]; vals=[]; cols=[]; ps=[]
for c,lab in MET:
    x,y=col(a_main,c),col(b_main,c)
    if len(x)<2 or len(y)<2: continue
    sd=st.pstdev(x+y) or 1.0
    labs.append(lab); vals.append((st.mean(y)-st.mean(x))/sd); ps.append(exact_p(x,y))
order=sorted(range(len(vals)), key=lambda i: vals[i])
labs=[labs[i] for i in order]; vals=[vals[i] for i in order]; ps=[ps[i] for i in order]
cols=[VERM if p<=floor+1e-9 else (ORANGE if p<=0.05 else LGREY) for p in ps]
ax.barh(range(len(vals)), vals, color=cols, height=0.62)
ax.axvline(0, color=GREY, lw=0.9)
ax.set_yticks(range(len(labs))); ax.set_yticklabels(labs, fontsize=8.2)
ax.set_xlabel("standardized difference  (Sonnet − mini, pooled SD units)", fontsize=8.3)
ax.set_title("Changing the generator moves more than any\nmanipulation in the study", fontsize=9.6, fontweight="bold", loc="left")
for i,(v,p) in enumerate(zip(vals,ps)):
    ax.text(v + (0.12 if v>=0 else -0.12), i, f"p={p:.3f}", va="center",
            ha="left" if v>=0 else "right", fontsize=7.2, color=GREY)
ax.set_xlim(min(vals)-1.5, max(vals)+1.5)
for s in ("top","right"): ax.spines[s].set_visible(False)

# ---- panel 2: the length control --------------------------------------------
ax=axes[1]
xa,xb=col(a_main,"transcript_chars"),col(b_main,"transcript_chars")
ax.scatter([0]*len(xa), xa, s=44, color=BLUE, zorder=3, label="gpt-5.4-mini")
ax.scatter([1]*len(xb), xb, s=44, color=PURPLE, zorder=3, label="claude-sonnet-5")
ax.hlines(st.mean(xa), -0.28, 0.28, color=BLUE, lw=2.2)
ax.hlines(st.mean(xb), 0.72, 1.28, color=PURPLE, lw=2.2)
ax.set_xticks([0,1]); ax.set_xticklabels(["gpt-5.4-mini","claude-sonnet-5"], fontsize=8.2)
ax.set_xlim(-0.55,1.55); ax.set_ylabel("transcript length (characters)", fontsize=8.3)
ax.set_title("…while writing the same amount", fontsize=9.6, fontweight="bold", loc="left")
ax.annotate(f"means differ by {abs(st.mean(xb)-st.mean(xa)):,.0f} characters\nin ~150,000   (p = {exact_p(xa,xb):.2f})",
            xy=(0.5, max(xa+xb)), xytext=(0.5, max(xa+xb)*1.035), ha="center", fontsize=7.8, color=GREY)
ax.set_ylim(min(xa+xb)*0.93, max(xa+xb)*1.09)
for s in ("top","right"): ax.spines[s].set_visible(False)

# ---- panel 3: does the position layer replicate in direction? ----------------
ax=axes[2]
def contrast(p, metric):
    hi,lo=rows(p,"layer_position_high"),rows(p,"layer_position_low")
    if not hi or not lo: return None
    return st.mean(col(hi,metric))-st.mean(col(lo,metric))
pairs=[("dqi_respect","respect"),("position_move","position movement")]
w=0.34; xs=range(len(pairs))
va=[contrast(A,m) for m,_ in pairs]; vb=[contrast(B,m) for m,_ in pairs]
ax.bar([x-w/2 for x in xs], va, w, color=BLUE, label="gpt-5.4-mini")
ax.bar([x+w/2 for x in xs], vb, w, color=PURPLE, label="claude-sonnet-5")
ax.axhline(0, color=GREY, lw=0.9)
ax.set_xticks(list(xs)); ax.set_xticklabels([l for _,l in pairs], fontsize=8.2)
ax.set_ylabel("position layer, high − low", fontsize=8.3)
ax.set_title("The framework's direction survives\nthe change of engine", fontsize=9.6, fontweight="bold", loc="left")
ax.legend(fontsize=7.6, frameon=False, loc="upper left")
for s in ("top","right"): ax.spines[s].set_visible(False)

fig.tight_layout()
fig.savefig(os.path.join(OUT, "Fig 9.6 - Cross-Model Comparison.png"), facecolor="white")
print("  wrote Fig 9.6 - Cross-Model Comparison.png")
