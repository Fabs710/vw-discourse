"""
make_figures_results.py - the results figures, built from the completed sensitivity batch.

Companion to make_figures.py (same Okabe-Ito palette, same 300 dpi output folder).
Kept separate because these four depend on a completed batch, whereas the six in
make_figures.py depend only on the design and the legibility/validation data.

Figures produced
  Fig 9.2   Screen effects against both screening thresholds
  Fig 9.2b  DQI profile across conditions (small multiples)
  Fig 9.5   Drill-down: within-sweep contrasts against the permutation floor
  Fig 8.4   Judge-bias checks: length quartiles and judge offsets

Usage:  python make_figures_results.py [batch]
        default batch: data/sensitivity_20260723_000046
"""
import csv, json, os, re, sys, math, itertools
import statistics as st
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.join("..", "Current Draft and Structure", "Figures")
os.makedirs(OUT, exist_ok=True)

BLUE = "#0072B2"; ORANGE = "#E69F00"; GREEN = "#009E73"; VERM = "#D55E00"
SKY = "#56B4E9"; PURPLE = "#CC79A7"; GREY = "#4D4D4D"; LGREY = "#BFBFBF"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": GREY,
    "axes.labelcolor": "#222222", "text.color": "#222222",
    "xtick.color": GREY, "ytick.color": GREY, "axes.grid": False,
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
})

BATCH = Path(sys.argv[1] if len(sys.argv) > 1 else "data/sensitivity_20260723_000046")


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), facecolor="white")
    plt.close(fig)
    print("  wrote", name)


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


_REP = re.compile(r"_r\d+$")


def base_id(rid):
    return _REP.sub("", rid)   # any repetition number, not just single digits


ROWS = list(csv.DictReader(open(BATCH / "index.csv", encoding="utf-8")))
G = defaultdict(list)
for r in ROWS:
    G[base_id(r["run_id"])].append(r)


def vals(cond, m):
    return [fnum(r.get(m)) for r in G.get(cond, []) if fnum(r.get(m)) is not None]


def mean(cond, m):
    v = vals(cond, m)
    return st.mean(v) if v else None


def exact_p(a, b):
    obs = abs(st.mean(a) - st.mean(b)); pool = a + b; n = len(a)
    hits = tot = 0
    for idx in itertools.combinations(range(len(pool)), n):
        x = [pool[i] for i in idx]; y = [pool[i] for i in range(len(pool)) if i not in idx]
        tot += 1
        if abs(st.mean(x) - st.mean(y)) >= obs - 1e-12:
            hits += 1
    return hits / tot


LAYER_CONDS = ["layer_salience_low", "layer_salience_high", "layer_motivation_low", "layer_motivation_high",
               "layer_position_low", "layer_position_high", "layer_interaction_low", "layer_interaction_high"]
LAYER_LABEL = {c: c.replace("layer_", "").replace("_", " ") for c in LAYER_CONDS}


# ------------------------------------------------------------------ Fig 9.2
def fig_screen_effects():
    """Layer-screen effects vs baseline, against both screening thresholds."""
    # Thresholds are DERIVED from the data, not hard-coded: after a confirmatory
    # top-up the baseline spread and the order band must be recomputed, or the figure
    # would silently show the old thresholds against new effects.
    def _band(m):
        base = vals("main", m)
        diffs = [abs(st.mean(vals(o, m)) - st.mean(base)) for o in ("order_reversed", "order_random") if vals(o, m)]
        return max(diffs) if diffs else 0.0
    def _twosd(m):
        base = vals("main", m)
        return 2 * st.stdev(base) if len(base) > 1 else 0.0
    metrics = [("dqi_respect", "Respect", _band("dqi_respect"), _twosd("dqi_respect")),
               ("position_move", "Position movement", _band("position_move"), _twosd("position_move"))]
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.3))
    for ax, (m, label, band, twosd) in zip(axes, metrics):
        base = mean("main", m)
        effs = [(LAYER_LABEL[c], mean(c, m) - base) for c in LAYER_CONDS]
        effs.sort(key=lambda x: x[1])
        y = range(len(effs))
        cols = []
        for _, e in effs:
            passes = abs(e) > band and abs(e) > twosd
            cols.append(VERM if passes else (SKY if abs(e) > band else LGREY))
        ax.barh(list(y), [e for _, e in effs], color=cols, edgecolor=GREY, linewidth=0.7, height=0.62, zorder=3)
        ax.axvline(0, color=GREY, lw=1.0, zorder=2)
        for v, ls, lab, col in [(band, (0, (3, 2)), "order-noise band", BLUE),
                                (twosd, (0, (1, 1.6)), "2 SD baseline", ORANGE)]:
            ax.axvline(v, color=col, lw=1.2, ls=ls, zorder=2)
            ax.axvline(-v, color=col, lw=1.2, ls=ls, zorder=2)
        ax.set_yticks(list(y)); ax.set_yticklabels([n for n, _ in effs], fontsize=8)
        ax.set_xlabel(f"effect on {label.lower()} vs baseline", fontsize=8.5)
        ax.set_title(label, fontsize=10, fontweight="bold", pad=8)
        ax.spines[["top", "right"]].set_visible(False)
        ax.text(0.99, 0.03, f"band ±{band:.3f}   2 SD ±{twosd:.3f}", transform=ax.transAxes,
                ha="right", fontsize=7, color=GREY)
    handles = [plt.Rectangle((0, 0), 1, 1, fc=VERM, ec=GREY, lw=0.7),
               plt.Rectangle((0, 0), 1, 1, fc=SKY, ec=GREY, lw=0.7),
               plt.Rectangle((0, 0), 1, 1, fc=LGREY, ec=GREY, lw=0.7)]
    fig.legend(handles, ["clears both criteria", "clears the band only", "clears neither"],
               loc="lower center", ncol=3, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.045))
    fig.suptitle("Layer-screen effects against both screening criteria", fontsize=12,
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    save(fig, "Fig 9.2 - Screen Effects vs Thresholds.png")


# ----------------------------------------------------------------- Fig 9.2b
def fig_dqi_profile():
    """Small multiples: every DQI item across baseline, layer poles and order conditions."""
    items = [("dqi_justif_level", "Justification level"), ("dqi_justif_content", "Justification content"),
             ("dqi_respect", "Respect"), ("dqi_constructive", "Constructive politics"),
             ("dqi_individuation", "Individuation")]
    conds = ["main"] + LAYER_CONDS + ["order_reversed", "order_random"]
    labels = ["baseline"] + [LAYER_LABEL[c] for c in LAYER_CONDS] + ["order rev.", "order rand."]
    fig, axes = plt.subplots(1, 5, figsize=(13.2, 3.9), sharey=True)
    for ax, (m, label) in zip(axes, items):
        mus = [mean(c, m) for c in conds]
        sds = [st.stdev(vals(c, m)) if len(vals(c, m)) > 1 else 0 for c in conds]
        cols = [GREY] + [BLUE] * 8 + [PURPLE] * 2
        ax.errorbar(mus, range(len(conds)), xerr=sds, fmt="o", ms=4.2, lw=0,
                    elinewidth=1.0, ecolor=LGREY, zorder=3)
        for i, (mu, c) in enumerate(zip(mus, cols)):
            ax.plot([mu], [i], "o", ms=4.6, color=c, zorder=4)
        ax.axvline(mus[0], color=GREY, lw=0.9, ls=(0, (3, 2)), zorder=2)
        ax.set_xlim(1.25, 2.06)
        ax.set_title(label, fontsize=9, fontweight="bold", pad=6)
        ax.set_xticks([1.4, 1.7, 2.0])
        ax.spines[["top", "right"]].set_visible(False)
        span = max(mus) - min(mus)
        ax.text(0.03, 0.03, f"range {span:.3f}", transform=ax.transAxes, fontsize=7, color=GREY)
    axes[0].set_yticks(range(len(conds))); axes[0].set_yticklabels(labels, fontsize=8)
    axes[0].invert_yaxis()
    fig.suptitle("Adapted-DQI profile across conditions: only two of five items discriminate",
                 fontsize=12, fontweight="bold", y=1.04)
    fig.tight_layout()
    save(fig, "Fig 9.2b - DQI Profile Small Multiples.png")


# ------------------------------------------------------------------ Fig 9.5
def fig_drill_contrasts():
    """Within-sweep contrasts for the nine drill sweeps, with exact permutation p."""
    sweeps = [("mgmt_flexibility", "Mgmt flexibility", "position"),
              ("igmetall_flexibility", "IG Metall flexibility", "position"),
              ("mgmt_dependency", "Mgmt dependency", "position"),
              ("works_dependency", "Works council dependency", "position"),
              ("saxony_assertiveness", "Saxony assertiveness", "interaction"),
              ("works_cooperativeness", "Works cooperativeness", "interaction"),
              ("owners_social_pref", "Owners social preference", "motivation"),
              ("investors_power", "Investors power", "salience"),
              ("mgmt_relational_prior", "Mgmt relational prior", "BELIEF")]
    metrics = [("dqi_respect", "Respect"), ("position_move", "Position movement")]
    LAYCOL = {"position": BLUE, "interaction": GREEN, "motivation": ORANGE,
              "salience": PURPLE, "BELIEF": VERM}
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.6))
    for ax, (m, label) in zip(axes, metrics):
        data = []
        for pre, name, lay in sweeps:
            hi, lo = vals(pre + "_high", m), vals(pre + "_low", m)
            if len(hi) != len(lo) or len(hi) < 2:
                continue
            data.append((name, lay, st.mean(hi) - st.mean(lo), exact_p(hi, lo)))
        data.sort(key=lambda x: x[2])
        y = list(range(len(data)))
        ax.barh(y, [d[2] for d in data], color=[LAYCOL[d[1]] for d in data],
                edgecolor=GREY, linewidth=0.7, height=0.6, zorder=3,
                alpha=1.0)
        for i, d in enumerate(data):
            if d[3] > 0.10 + 1e-9:
                ax.barh([i], [d[2]], color="white", edgecolor=GREY, linewidth=0.7,
                        height=0.6, zorder=4, alpha=0.62)
            ax.text(d[2] + (0.004 if d[2] >= 0 else -0.004), i, f"p={d[3]:.2f}",
                    va="center", ha="left" if d[2] >= 0 else "right", fontsize=7, color=GREY, zorder=5)
        ax.axvline(0, color=GREY, lw=1.0, zorder=2)
        ax.set_yticks(y); ax.set_yticklabels([d[0] for d in data], fontsize=8)
        ax.set_xlabel(f"contrast on {label.lower()}  (high pole − low pole)", fontsize=8.5)
        ax.set_title(label, fontsize=10, fontweight="bold", pad=8)
        ax.spines[["top", "right"]].set_visible(False)
        xa, xb = ax.get_xlim(); ax.set_xlim(xa * 1.25, xb * 1.25)
    handles = [plt.Rectangle((0, 0), 1, 1, fc=LAYCOL[k], ec=GREY, lw=0.7) for k in
               ["position", "interaction", "motivation", "salience", "BELIEF"]]
    fig.legend(handles, ["position", "interaction", "motivation", "salience", "belief"],
               loc="lower center", ncol=5, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.05))
    fig.suptitle("Drill-down: within-sweep contrasts, solid where p reaches the 0.10 permutation floor",
                 fontsize=11.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    save(fig, "Fig 9.5 - Drill Contrasts vs Permutation Floor.png")


# ------------------------------------------------------------------ Fig 8.4
def fig_judge_bias():
    """Verbosity check (score by transcript-length quartile) and the two-judge agreement spread."""
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.1))

    # left: verbosity - mean judged score by transcript-length quartile
    pairs = [(fnum(r["transcript_chars"]), fnum(r["dqi_respect"]), fnum(r["dqi_justif_content"]))
             for r in ROWS if fnum(r.get("transcript_chars")) is not None]
    pairs.sort(key=lambda x: x[0])
    q = len(pairs) // 4
    quarts = [pairs[0:q], pairs[q:2 * q], pairs[2 * q:3 * q], pairs[3 * q:]]
    ax = axes[0]
    for j, (col, name, mk) in enumerate([(BLUE, "respect", "o"), (ORANGE, "justification content", "s")]):
        mus = [st.mean([p[1 + j] for p in qq]) for qq in quarts]
        sds = [st.stdev([p[1 + j] for p in qq]) for qq in quarts]
        ax.errorbar(range(4), mus, yerr=sds, marker=mk, ms=5.5, lw=1.4, color=col,
                    ecolor=LGREY, elinewidth=1.0, capsize=3, label=name, zorder=3)
    ax.set_xticks(range(4))
    ax.set_xticklabels([f"Q{i+1}\n{int(st.mean([p[0] for p in quarts[i]])/1000)}k" for i in range(4)], fontsize=8)
    ax.set_xlabel("transcript-length quartile (mean characters)", fontsize=8.5)
    ax.set_ylabel("mean judged score (0–2)", fontsize=8.5)
    ax.set_title("Verbosity check", fontsize=10, fontweight="bold", pad=8)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)

    # right: distribution of per-run two-judge agreement (quadratic weighted kappa)
    ax = axes[1]
    ks = sorted(fnum(r["kappa_mean"]) for r in ROWS if fnum(r.get("kappa_mean")) is not None)
    ax.hist(ks, bins=14, color=SKY, edgecolor=GREY, linewidth=0.8, zorder=3)
    med = st.median(ks)
    ax.axvline(med, color=VERM, lw=1.5, ls=(0, (3, 2)), zorder=4)
    ax.text(med, ax.get_ylim()[1] * 0.94, f"median {med:.2f}  ", color=VERM, fontsize=8, va="top", ha="right")
    for thr, lab in [(0.41, "moderate"), (0.61, "substantial")]:
        ax.axvline(thr, color=GREY, lw=0.9, ls=(0, (1, 1.8)), zorder=2)
        ax.text(thr, ax.get_ylim()[1] * 0.06, f" {lab}", fontsize=7, color=GREY, rotation=90, va="bottom")
    ax.set_xlabel("per-run two-judge agreement (quadratic weighted κ)", fontsize=8.5)
    ax.set_ylabel("runs", fontsize=8.5)
    ax.set_title(f"Inter-judge agreement across {len(ks)} runs", fontsize=10, fontweight="bold", pad=8)
    ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle("Judge-bias checks", fontsize=12, fontweight="bold", y=1.03)
    # The caption used to read "if the judges rewarded length, scores would rise across
    # quartiles", which invited the reader to treat a flat line as the expected result.
    # Both series DO rise, so that phrasing described the figure as a pass when it is a
    # weak fail. It now states the association and its size.
    # Two lines: a single long caption forced tight_layout to widen the whole figure
    # from 3194 to 5380 px, which would print as a letterbox.
    fig.tight_layout()
    save(fig, "Fig 8.4 - Judge Bias Checks.png")


if __name__ == "__main__":
    print(f"batch: {BATCH}  ({len(ROWS)} runs, {len(G)} conditions)")
    fig_screen_effects()
    fig_dqi_profile()
    fig_drill_contrasts()
    fig_judge_bias()
    print("done ->", OUT)
