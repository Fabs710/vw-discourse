"""
make_fig85.py - Figure 8.5, the variance decomposition from the judge test-retest.

The single most consequential measurement in the thesis and the only one with no
figure: on the two measures carrying every remaining result, roughly two-thirds of the
within-condition variance is the jury re-reading the same transcript rather than the
simulation producing a different one.

Usage:  python make_fig85.py
"""
import json, math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.join("..", "Current Draft and Structure", "Figures")
BLUE="#0072B2"; ORANGE="#E69F00"; GREEN="#009E73"; VERM="#D55E00"
SKY="#56B4E9"; GREY="#4D4D4D"; LGREY="#BFBFBF"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"axes.edgecolor":GREY,
    "axes.labelcolor":"#222222","text.color":"#222222","xtick.color":GREY,"ytick.color":GREY,
    "figure.dpi":300,"savefig.dpi":300,"savefig.bbox":"tight"})

d = json.load(open("data/sensitivity_20260723_000046/retest_analysis_retest1.json", encoding="utf-8"))["dimensions"]
ORDER = ["respect","position_move","constructive_politics","justification_level",
         "justification_content","individuation"]
LBL = {"respect":"Respect","position_move":"Position movement","constructive_politics":"Constructive politics",
       "justification_level":"Justification level","justification_content":"Justification content",
       "individuation":"Individuation"}
CARRIES = {"respect":"carries all three confirmed\nparameter effects",
           "position_move":"carries the one surviving\nscreen effect"}

fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.9), gridspec_kw={"width_ratios":[1.35,1.0]})

# ---- left: stacked share of variance -----------------------------------------
ax = axes[0]
ys = range(len(ORDER))
share = [100*d[k]["judging_variance_share"] for k in ORDER]
for i,(k,s) in enumerate(zip(ORDER, share)):
    col = VERM if s >= 50 else LGREY
    ax.barh(i, s, color=col, height=0.6)
    ax.barh(i, 100-s, left=s, color=SKY if s>=50 else "#E8EDF1", height=0.6)
    ax.text(s+1.5 if s<80 else s-1.5, i, "%.0f%%" % s, va="center",
            ha="left" if s<80 else "right", fontsize=8.4,
            color="white" if s>=80 else GREY, fontweight="bold")
ax.set_yticks(list(ys)); ax.set_yticklabels([LBL[k] for k in ORDER], fontsize=8.6)
ax.set_xlim(0,100); ax.set_ylim(-0.6, len(ORDER)-0.15); ax.set_xlabel("share of within-condition variance (%)", fontsize=8.6)
ax.set_title("Two-thirds of the variance on the measures that\ncarry the findings is the scorer, not the simulation",
             fontsize=9.8, fontweight="bold", loc="left")
ax.axvline(50, color=GREY, lw=0.8, ls=(0,(4,2)))
for s in ("top","right"): ax.spines[s].set_visible(False)
ax.text(2, len(ORDER)-0.72, "JUDGING", fontsize=7.6, color=VERM, fontweight="bold")
ax.text(72, len(ORDER)-0.72, "GENERATION", fontsize=7.6, color=BLUE, fontweight="bold")
for k,note in CARRIES.items():
    i = ORDER.index(k)
    ax.text(101, i, note, fontsize=6.9, color=GREY, va="center", ha="left")

# ---- right: what averaging k passes buys on respect ---------------------------
ax = axes[1]
r = d["respect"]; js, ts = r["judge_sd"], r["total_within_condition_sd"]
gen2 = max(0.0, ts**2 - js**2)
ks = [1,2,3,4]
tot = [math.sqrt(gen2 + js**2/k) for k in ks]
ax.plot(ks, tot, "o-", color=VERM, lw=2, ms=7)
for k,t in zip(ks,tot):
    ax.annotate("%.4f" % t, (k,t), textcoords="offset points", xytext=(0,9),
                ha="center", fontsize=8, color=GREY)
ax.axhline(math.sqrt(gen2), color=BLUE, lw=1.4, ls=(0,(4,2)))
ax.text(4.05, math.sqrt(gen2), " floor: generation\n only (%.4f)" % math.sqrt(gen2),
        fontsize=7.4, color=BLUE, va="center")
ax.set_xticks(ks); ax.set_xlabel("independent scoring passes, averaged", fontsize=8.6)
ax.set_ylabel("total within-condition SD, respect", fontsize=8.6)
ax.set_title("A second pass costs no generation\nand removes 18% of the noise",
             fontsize=9.8, fontweight="bold", loc="left")
ax.set_xlim(0.7,5.4); ax.set_ylim(math.sqrt(gen2)*0.93, ts*1.06)
for s in ("top","right"): ax.spines[s].set_visible(False)

fig.tight_layout()
fig.savefig(os.path.join(OUT, "Fig 8.5 - Judging vs Generation Variance.png"), facecolor="white")
print("  wrote Fig 8.5 - Judging vs Generation Variance.png")
