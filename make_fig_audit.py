"""
make_fig_audit.py - the independent-rater audit figure for Sections 8.5.3-8.5.4.

Two panels. Left (scope A): chance-corrected agreement with the reference coding on
the 28-item human sample, for all four raters - the two incumbent jury judges and the
two outside raters. Right (scopes B/C): how often each rater marks respect below the
2.0 ceiling on the calibrated configurations of both generation engines - the
compression that makes the outside raters' non-corroboration of the 9.6 respect gap
inconclusive rather than negative.

Every plotted value is RECOMPUTED here from the primary files (human_codes.json,
human_coding_content_rejudge.json, the per-run evaluation.json and
evaluation_audit_*.json), then asserted against the values quoted in Section 8.5.
If prose and data ever diverge, this script refuses to draw.

Usage:  python make_fig_audit.py
"""
import json, os
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
    "figure.dpi":300,"savefig.dpi":300,"savefig.bbox":"tight"})

MAIN  = Path("data/sensitivity_20260723_000046")
CROSS = Path("data/sensitivity_20260726_172041")

# ---------------------------------------------------------------- weighted kappa
def qwk(a, b, cats=(0, 1, 2)):
    """Quadratic weighted kappa on two equal-length integer score lists."""
    n = len(a); k = len(cats); idx = {c: i for i, c in enumerate(cats)}
    O = [[0]*k for _ in range(k)]
    for x, y in zip(a, b): O[idx[x]][idx[y]] += 1
    ra = [sum(O[i]) for i in range(k)]; rb = [sum(O[i][j] for i in range(k)) for j in range(k)]
    W = [[(i-j)**2/(k-1)**2 for j in range(k)] for i in range(k)]
    num = sum(W[i][j]*O[i][j] for i in range(k) for j in range(k))
    den = sum(W[i][j]*ra[i]*rb[j]/n for i in range(k) for j in range(k))
    return 0.0 if den == 0 else round(1 - num/den, 3)

# ---------------------------------------------------------------- scope A: 28 items
human = {h["id"]: h for h in json.load(open("data/human_codes.json", encoding="utf-8"))}
key   = json.load(open("data/human_coding_key.json", encoding="utf-8"))
rej   = {r["id"]: r["scores"] for r in json.load(open("data/human_coding_content_rejudge.json", encoding="utf-8"))}
aud   = {r["id"]: r["scores"] for r in json.load(open("data/audit_sample_scores.json", encoding="utf-8"))["scores"]}

def jury_scores(item):
    """The two incumbent judges' original scores for a keyed sample item."""
    ev = json.load(open(MAIN / item["cond"] / "evaluation.json", encoding="utf-8"))
    for c in ev["contribution_scores"]:
        if c["round"] == item["round"] and c["stakeholder"] == item["stakeholder"]:
            return c["judges"]
    raise KeyError(item)

ids = [it["id"] for it in key]
h_resp = [human[i]["respect"] for i in ids]
h_cont = [human[i]["justification_content"] for i in ids]          # the v2 coding

# TWO DIFFERENT JUDGE ORDERS, deliberately spelled out - this trap put a swapped
# attribution into the Sec 8.5 table (found and corrected 2 Aug):
#   evaluation.json 'judges' list  -> evaluate.py default "gpt-5.4-mini,claude-sonnet-5":
#       judges[0] = GPT judge, judges[1] = Claude judge.
#   human_coding_content_rejudge.json 'scores' -> rejudge_content.py default
#       "claude-sonnet-5,gpt-5.4": scores[0] = Claude judge, scores[1] = GPT judge.
gpt_resp = []; cla_resp = []
for it in key:
    js = jury_scores(it)
    gpt_resp.append(js[0]["respect"]); cla_resp.append(js[1]["respect"])
cla_cont = [rej[i][0] for i in ids]; gpt_cont = [rej[i][1] for i in ids]
g_resp = [aud[i]["gemini-3.6-flash"]["respect"] for i in ids]
q_resp = [aud[i]["qwen/qwen3.6-27b"]["respect"] for i in ids]
g_cont = [aud[i]["gemini-3.6-flash"]["justification_content"] for i in ids]
q_cont = [aud[i]["qwen/qwen3.6-27b"]["justification_content"] for i in ids]

A = {  # rater -> (kappa respect, kappa content v2)
    "GPT judge":    (qwk(h_resp, gpt_resp), qwk(h_cont, gpt_cont)),
    "Claude judge": (qwk(h_resp, cla_resp), qwk(h_cont, cla_cont)),
    "Gemini":       (qwk(h_resp, g_resp),   qwk(h_cont, g_cont)),
    "Qwen":         (qwk(h_resp, q_resp),   qwk(h_cont, q_cont)),
}
print("scope A (kappa vs reference coding):")
for r, (kr, kc) in A.items(): print(f"  {r:13s} respect {kr:+.3f}   content {kc:+.3f}")

# The values Section 8.5 quotes. If these asserts fire, prose and data have diverged.
assert abs(A["GPT judge"][0] - 0.50) < 0.01 and abs(A["Claude judge"][0] - 0.31) < 0.01
assert abs(A["Gemini"][0] - 0.50) < 0.01 and abs(A["Qwen"][0] - 0.46) < 0.01
assert abs(A["Claude judge"][1] - 0.88) < 0.01 and abs(A["GPT judge"][1] - 0.56) < 0.01
assert abs(A["Gemini"][1] - 0.07) < 0.01 and abs(A["Qwen"][1] - 0.17) < 0.01

# ------------------------------------------------- scopes B/C: below-ceiling shares
def below_shares(batch, run_dirs):
    """(jury judge-level share, gemini share, qwen share) of respect scores < 2."""
    jn = jd = 0; out = {}
    for tag in ("gemini", "qwen"):
        an = ad = 0
        for rd in run_dirs:
            a = json.load(open(batch / rd / f"evaluation_audit_{tag}.json", encoding="utf-8"))
            for c in a["contribution_scores"]:
                ad += 1; an += 1 if c["judges"][0]["respect"] < 2 else 0
        out[tag] = an / ad
    for rd in run_dirs:
        e = json.load(open(batch / rd / "evaluation.json", encoding="utf-8"))
        for c in e["contribution_scores"]:
            for j in c["judges"]:
                jd += 1; jn += 1 if j["respect"] < 2 else 0
    return jn / jd, out["gemini"], out["qwen"]

mini = below_shares(MAIN,  ["main", "main_recheck_r1"])
son  = below_shares(CROSS, ["main__m-claudesonnet_r1", "main__m-claudesonnet_r2", "main__m-claudesonnet_r3"])
print(f"below-ceiling respect, mini calibrated: jury {mini[0]:.3f} gemini {mini[1]:.3f} qwen {mini[2]:.3f}")
print(f"below-ceiling respect, sonnet:          jury {son[0]:.3f} gemini {son[1]:.3f} qwen {son[2]:.3f}")
assert abs(mini[0] - 0.365) < 0.005 and abs(mini[1] - 0.083) < 0.005 and abs(mini[2] - 0.083) < 0.005
assert abs(son[0] - 0.215) < 0.005 and abs(son[1] - 0.111) < 0.005 and abs(son[2] - 0.125) < 0.005

# ---------------------------------------------------------------------- the figure
fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.8), gridspec_kw={"width_ratios": [1.15, 1.0]})

RATERS = ["GPT judge", "Claude judge", "Gemini", "Qwen"]
RCOL   = {"GPT judge": BLUE, "Claude judge": PURPLE, "Gemini": GREEN, "Qwen": ORANGE}

ax = axes[0]; w = 0.19
for r_i, r in enumerate(RATERS):
    xs = [g + (r_i - 1.5) * w for g in (0, 1)]
    vs = [A[r][0], A[r][1]]
    ax.bar(xs, vs, w * 0.92, color=RCOL[r], label=r)
    for x, v in zip(xs, vs):
        ax.text(x, v + 0.015 if v >= 0 else 0.015, f"{v:.2f}", ha="center", fontsize=7.0, color=GREY)
ax.axhline(0, color=GREY, lw=0.9)
ax.set_xticks([0, 1]); ax.set_xticklabels(["respect", "justification content (v2)"], fontsize=8.6)
ax.set_ylabel("weighted kappa vs reference coding", fontsize=8.3)
ax.set_ylim(-0.05, 1.0)
ax.set_title("Four raters recover respect;\ncontent holds only for the raters it was tuned on",
             fontsize=9.6, fontweight="bold", loc="left")
ax.legend(fontsize=7.4, frameon=False, ncol=2, loc="upper left")
for s in ("top", "right"): ax.spines[s].set_visible(False)

ax = axes[1]; w = 0.24
SETS = [("gpt-5.4-mini\n(calibrated, 2 runs)", mini), ("claude-sonnet-5\n(calibrated, 3 runs)", son)]
BCOL = [GREY, GREEN, ORANGE]; BLAB = ["jury (both judges)", "Gemini", "Qwen"]
for b_i in range(3):
    xs = [g + (b_i - 1) * w for g in (0, 1)]
    vs = [SETS[0][1][b_i] * 100, SETS[1][1][b_i] * 100]
    ax.bar(xs, vs, w * 0.9, color=BCOL[b_i], label=BLAB[b_i])
    for x, v in zip(xs, vs):
        ax.text(x, v + 0.8, f"{v:.0f}%", ha="center", fontsize=7.4, color=GREY)
ax.set_xticks([0, 1]); ax.set_xticklabels([s[0] for s in SETS], fontsize=8.2)
ax.set_ylabel("respect scored below ceiling (% of records)", fontsize=8.3)
ax.set_title("The jury discriminates; the outside raters\nsit at the ceiling - compression, not refutation",
             fontsize=9.6, fontweight="bold", loc="left")
ax.legend(fontsize=7.4, frameon=False, loc="upper right")
for s in ("top", "right"): ax.spines[s].set_visible(False)

fig.text(0.0, -0.10,
  "Left: quadratic weighted kappa against the blind reference coding on the 28-item sample (Section 8.5.1); the v2 content\n"
  "anchor was refined against the two incumbent judges, and only they retain it. Right: share of contribution-level respect\n"
  "scores below the 2.0 ceiling on the calibrated configuration of each engine - jury pooled across both judges, outside\n"
  "raters scored independently. The jury separates the engines by fifteen points in the expected direction; raters marking\n"
  "down fewer than one contribution in ten have almost no events with which to register a difference (Section 8.5.4).",
  fontsize=7.2, color=GREY, va="top", linespacing=1.5)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "Fig 8.6 - Independent Rater Audit.png"), facecolor="white")
print("  wrote Fig 8.6 - Independent Rater Audit.png")
