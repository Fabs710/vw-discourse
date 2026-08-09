"""
make_fig_architecture.py - Figure "System architecture of one deliberation run".

Clean rebuild (v3): numbered stages, strictly orthogonal arrows, no element
overlaps or crossings. Colour legend matches the thesis caption exactly:
  green  = configuration and control components
  blue   = model-facing prompts and outputs
  orange = shared information (the central scenario and the growing transcript)
  dashed = post-hoc evaluation, separate from the simulation

Usage:  python make_fig_architecture.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle

OUT = os.path.join("..", "Current Draft and Structure", "Figures")
os.makedirs(OUT, exist_ok=True)
GREEN="#009E73"; BLUE="#0072B2"; ORANGE="#E69F00"; GREY="#4D4D4D"; PURPLE="#CC79A7"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,
    "figure.dpi":300,"savefig.dpi":300,"savefig.bbox":"tight"})

fig, ax = plt.subplots(figsize=(12.4, 7.0))
ax.set_xlim(0, 12.4); ax.set_ylim(0, 7.0); ax.axis("off")

def fit(w, text, fs):
    """Warn when the longest line would not fit the box width."""
    longest = max(len(l) for l in text.split("\n"))
    need = longest * 0.0102 * fs
    if need > w - 0.14:
        print(f"  [fit warning] '{text.splitlines()[0][:30]}...' needs {need:.2f} > {w-0.14:.2f}")

def box(x, y, w, h, text, color, fs=7.2, num=None):
    fit(w, text, fs)
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.045",
        facecolor=color + "1A", edgecolor=color, linewidth=1.3, zorder=2))
    ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=fs,
            color="#222222", linespacing=1.3, zorder=3)
    if num is not None:
        ax.add_patch(Circle((x + 0.16, y + h - 0.02), 0.125, facecolor="white",
                            edgecolor=color, linewidth=1.2, zorder=4))
        ax.text(x + 0.16, y + h - 0.02, str(num), ha="center", va="center",
                fontsize=7.6, color=color, fontweight="bold", zorder=5)

def arr(a, b, color=GREY, dashed=False, lw=1.4):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=12,
        color=color, lw=lw, linestyle=(0, (4, 2)) if dashed else "solid",
        zorder=4, shrinkA=1, shrinkB=1))

def elbow(points, color=GREY, lw=1.4):
    """Polyline through points, arrow head on the last segment only."""
    xs = [p[0] for p in points[:-1]]; ys = [p[1] for p in points[:-1]]
    ax.plot(xs, ys, color=color, lw=lw, solid_capstyle="round", zorder=1)
    arr(points[-2], points[-1], color=color, lw=lw)

ax.text(6.2, 6.76, "System architecture of one deliberation run",
        ha="center", fontsize=12.5, fontweight="bold")

# ---- left column: configuration and control (green)
box(0.30, 5.45, 2.30, 0.95, "configuration\n11 parameters × 6 stakeholders\nseed, pinned model snapshot", GREEN, 7.0, num=1)
box(0.30, 4.15, 2.30, 0.95, "prompt builder\nslider → banded descriptor\n+ calibration sentence", GREEN, 7.2, num=2)
box(0.30, 2.85, 2.30, 0.95, "salience ordering\npower · legitimacy · urgency\nsets the speaking order", GREEN, 7.2)
arr((1.45, 5.45), (1.45, 5.13))
arr((1.45, 4.15), (1.45, 3.83))
arr((2.60, 4.62), (3.38, 4.68))                      # builder -> agent briefs
arr((2.60, 3.32), (3.09, 3.32))                      # ordering -> loop frame
ax.text(2.78, 3.08, "turn order", fontsize=6.0, color=GREY, ha="center")

# ---- roundtable loop frame
ax.add_patch(Rectangle((3.10, 1.35), 5.45, 4.95, facecolor="none",
             edgecolor=GREY, linewidth=1.1, zorder=1))
ax.text(3.10, 6.40, "ROUNDTABLE LOOP (max 4 rounds)", fontsize=7.4,
        color=GREY, fontweight="bold")   # sits ABOVE the frame - cannot touch any box

# shared information (orange)
box(6.10, 5.55, 2.35, 0.55, "SCENARIO - central case file\nidentical for every agent", ORANGE, 6.8)
box(4.60, 0.42, 2.50, 0.60, "SHARED TRANSCRIPT\ngrows turn by turn", ORANGE, 7.2)
ax.add_patch(FancyArrowPatch((5.85, 1.02), (5.85, 1.35), arrowstyle="<|-|>",
    mutation_scale=11, color=ORANGE, lw=1.4, zorder=4))
ax.text(6.00, 1.13, "read + append, every turn", fontsize=6.2, color=ORANGE, ha="left")

# loop stages
box(3.40, 4.20, 2.15, 1.00, "agent briefs\n6 system prompts\n(case-neutral personas)", BLUE, 7.0, num=3)
box(6.10, 4.20, 2.35, 1.00, "stakeholder turn\nscenario + transcript window\n+ re-grounding reminder", BLUE, 6.8, num=4)
box(6.10, 3.50, 2.35, 0.48, "optional expert summons\n≤ 2 per run, on-the-fly persona", BLUE, 6.4)
box(6.10, 2.58, 2.35, 0.72, "moderator summary\nneutral, per round", BLUE, 7.2, num=5)
box(6.10, 1.55, 2.35, 0.80, "convergence monitor\ncontinue | intervene | synthesize", GREEN, 6.7, num=6)
arr((7.275, 5.55), (7.275, 5.22), color=ORANGE)        # scenario -> turn
arr((5.55, 4.70), (6.08, 4.70))                      # briefs -> turn
arr((7.275, 4.20), (7.275, 4.00))                      # turn -> summons
arr((7.275, 3.50), (7.275, 3.32))                      # summons -> moderator
arr((7.275, 2.58), (7.275, 2.37))                      # moderator -> monitor
elbow([(6.10, 1.95), (3.75, 1.95), (3.75, 4.18)])    # monitor 'continue' -> next round
ax.text(3.62, 3.00, "continue: next round", fontsize=6.2, color=GREY,
        rotation=90, va="center", ha="center")

# ---- right column: synthesis, artifacts, evaluation
box(9.05, 4.90, 3.05, 1.00, "SYNTHESIS\nten-section decision document\n(salience-weighted)", BLUE, 7.2, num=7)
box(9.05, 3.20, 3.05, 1.00, "frozen run artifacts\nbriefs · transcript · synthesis\nrun summary: tokens, cost, calls", GREEN, 6.9)
ax.add_patch(FancyBboxPatch((9.05, 1.30), 3.05, 1.40, boxstyle="round,pad=0.045",
    facecolor=PURPLE + "14", edgecolor=PURPLE, linewidth=1.3,
    linestyle=(0, (4, 2)), zorder=2))
ax.text(10.575, 2.00, "EVALUATION - post hoc\ntwo-judge DQI jury · outcome family\nfloor metrics; reads the frozen\nfiles only, never the simulation",
        ha="center", va="center", fontsize=6.9, linespacing=1.3, zorder=3)
elbow([(8.45, 1.95), (8.80, 1.95), (8.80, 5.40), (9.03, 5.40)])   # monitor -> synthesis
ax.text(8.68, 3.65, "synthesize", fontsize=6.2, color=GREY,
        rotation=90, va="center", ha="center")
arr((10.575, 4.90), (10.575, 4.22))                  # synthesis -> artifacts
arr((10.575, 3.20), (10.575, 2.72), color=PURPLE, dashed=True)

# ---- legend
def swatch(x, color, label, dashed=False):
    ax.add_patch(Rectangle((x, 0.05), 0.28, 0.17, facecolor=color + "1A",
        edgecolor=color, linestyle=(0, (4, 2)) if dashed else "solid"))
    ax.text(x + 0.36, 0.135, label, fontsize=7.3, va="center")
swatch(0.30, GREEN, "configuration / control")
swatch(2.55, BLUE, "model-facing prompts / outputs")
swatch(5.45, ORANGE, "shared information")
swatch(7.60, PURPLE, "post-hoc evaluation (separate)", dashed=True)

fig.savefig(os.path.join(OUT, "Fig 6.5 - System Architecture.png"), facecolor="white")
print("  wrote Fig 6.5 - System Architecture.png")
