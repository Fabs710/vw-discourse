"""
make_fig_architecture.py - Figure "System architecture of one deliberation run".

Replaces the hand-drawn 11a PNG with a scripted diagram in the corpus style.
Colour legend matches the thesis caption exactly:
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
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

OUT = os.path.join("..", "Current Draft and Structure", "Figures")
os.makedirs(OUT, exist_ok=True)
GREEN="#009E73"; BLUE="#0072B2"; ORANGE="#E69F00"; GREY="#4D4D4D"; PURPLE="#CC79A7"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,
    "figure.dpi":300,"savefig.dpi":300,"savefig.bbox":"tight"})

fig, ax = plt.subplots(figsize=(11.6, 6.4))
ax.set_xlim(0, 11.6); ax.set_ylim(0, 6.4); ax.axis("off")

def box(x, y, w, h, text, color, fs=8.2, bold=False, dashed=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.055",
        facecolor=color + "1A", edgecolor=color, linewidth=1.3,
        linestyle=(0, (4, 2)) if dashed else "solid", zorder=2))
    ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=fs,
            color="#222222", fontweight="bold" if bold else "normal",
            linespacing=1.25, zorder=3)

def arrow(a, b, color=GREY, lw=1.4, dashed=False, rad=0.0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=13,
        color=color, lw=lw, linestyle=(0, (4, 2)) if dashed else "solid",
        connectionstyle=f"arc3,rad={rad}", zorder=4, shrinkA=2, shrinkB=2))

ax.text(5.8, 6.22, "System architecture of one deliberation run",
        ha="center", fontsize=12.5, fontweight="bold")

# ---- left column: configuration and control (green)
box(0.25, 4.85, 2.05, 0.80, "configuration\n11 parameters × 6 stakeholders\n(seed, pinned snapshot)", GREEN, 7.6)
box(0.25, 3.75, 2.05, 0.70, "prompt builder\nslider → banded descriptor\n+ calibration sentence", GREEN, 7.6)
box(0.25, 2.65, 2.05, 0.70, "salience ordering\npower · legitimacy · urgency\nsets who speaks first", GREEN, 7.6)
arrow((1.27, 4.85), (1.27, 4.45))
arrow((1.27, 3.75), (1.27, 3.35))

# ---- shared information (orange)
box(2.75, 5.05, 2.30, 0.62, "SCENARIO (central case file)\nidentical for every agent", ORANGE, 7.8, bold=False)
box(3.05, 0.62, 2.30, 0.62, "SHARED TRANSCRIPT\ngrows turn by turn", ORANGE, 7.8)

# ---- roundtable loop (frame)
ax.add_patch(Rectangle((2.60, 1.45), 5.45, 3.30, facecolor="none",
             edgecolor=GREY, linewidth=1.1, zorder=1))
ax.text(2.72, 4.58, "ROUNDTABLE LOOP  (up to 4 rounds)", fontsize=8.0,
        color=GREY, fontweight="bold")

# agents / turns (blue)
box(2.85, 3.30, 2.05, 1.05, "agent briefs\n6 stakeholder system prompts\n(case-neutral personas)", BLUE, 7.6)
box(5.25, 3.30, 2.60, 1.05, "stakeholder turn\nscenario + transcript window\n+ re-grounding reminder", BLUE, 7.6)
box(5.25, 2.48, 2.60, 0.62, "expert summons (max 2 per run)\npersona generated on the fly", BLUE, 7.3)
box(2.85, 1.65, 2.05, 0.68, "moderator summary\nneutral, per round", BLUE, 7.4)
box(5.25, 1.65, 2.60, 0.68, "convergence monitor\ncontinue | intervene | synthesize", GREEN, 7.4)

arrow((2.30, 4.10), (2.85, 3.95))                      # prompt builder -> briefs
arrow((2.30, 3.00), (2.62, 3.00))                      # ordering -> loop
arrow((3.90, 5.05), (5.90, 4.35), rad=-0.15, color=ORANGE)   # scenario -> turn
arrow((4.90, 3.82), (5.25, 3.82))                      # briefs -> turn
arrow((6.55, 3.30), (6.55, 3.10))                      # turn -> expert
arrow((5.32, 3.30), (5.12, 1.28), rad=0.10, color=ORANGE)    # contributions -> transcript
ax.text(4.99, 2.40, "contributions", fontsize=6.5, color=ORANGE, rotation=82, ha="center")
arrow((3.60, 1.65), (3.60, 1.24), color=ORANGE)        # moderator summary -> transcript
arrow((5.25, 3.38), (3.95, 2.33), rad=0.20)            # round end -> moderator
arrow((3.90, 1.99), (5.25, 1.99))                      # moderator -> monitor
arrow((7.88, 2.10), (7.88, 3.55), rad=-0.16)           # monitor 'continue' -> next turn
ax.text(7.74, 2.85, "continue", fontsize=6.4, color=GREY, rotation=90, va="center", ha="center")

# ---- synthesis + artifacts
box(8.45, 3.55, 2.85, 0.90, "SYNTHESIS\nten-section decision document\n(salience-weighted)", BLUE, 7.8)
box(8.45, 2.20, 2.85, 0.95, "frozen run artifacts\nbriefs · transcript · synthesis\nrun summary (tokens, cost, calls)", GREEN, 7.4)
arrow((7.85, 1.85), (8.45, 3.85), rad=-0.28)           # monitor 'synthesize' -> synthesis
ax.text(8.32, 2.55, "synthesize", fontsize=6.4, color=GREY, style="italic", rotation=64)
arrow((9.87, 3.55), (9.87, 3.15))                      # synthesis -> artifacts

# ---- evaluation (dashed, post-hoc)
box(8.45, 0.55, 2.85, 1.20, "EVALUATION (post hoc)\ntwo-judge DQI jury · outcome family\nfloor metrics - reads frozen files only,\nnever touches the simulation", PURPLE, 7.3, dashed=True)
arrow((9.87, 2.20), (9.87, 1.75), dashed=True, color=PURPLE)

# ---- legend
ax.add_patch(Rectangle((0.25, 0.30), 0.28, 0.18, facecolor=GREEN+"1A", edgecolor=GREEN))
ax.text(0.60, 0.39, "configuration / control", fontsize=7.4, va="center")
ax.add_patch(Rectangle((2.30, 0.30), 0.28, 0.18, facecolor=BLUE+"1A", edgecolor=BLUE))
ax.text(2.65, 0.39, "model-facing prompts / outputs", fontsize=7.4, va="center")
ax.add_patch(Rectangle((4.95, 0.30), 0.28, 0.18, facecolor=ORANGE+"1A", edgecolor=ORANGE))
ax.text(5.30, 0.39, "shared information", fontsize=7.4, va="center")
ax.add_patch(Rectangle((6.75, 0.30), 0.28, 0.18, facecolor=PURPLE+"1A", edgecolor=PURPLE, linestyle=(0,(4,2))))
ax.text(7.10, 0.39, "post-hoc evaluation (separate)", fontsize=7.4, va="center")

fig.savefig(os.path.join(OUT, "Fig 6.5 - System Architecture.png"), facecolor="white")
print("  wrote Fig 6.5 - System Architecture.png")
