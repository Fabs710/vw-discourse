"""
make_fig_casemap.py - the case stakeholder map for Chapter 7 (Sections 7.2-7.3).

Every value on the figure is read from config/simulation_config.yaml - the same file
the engine reads - so the map cannot drift from the simulation it describes. Rows are
ordered by the roundtable turn order, which is itself a config value.

Usage:  python make_fig_casemap.py
"""
import os, re, textwrap
import yaml
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

CFG = yaml.safe_load(open("config/simulation_config.yaml", encoding="utf-8"))
BY_KEY = {s["key"]: s for s in CFG["stakeholders"]}
ORDER = CFG["roundtable"]["turn_order"]          # rows in speaking order

CAMP = {"works_council": ("labor", BLUE), "ig_metall": ("labor", BLUE),
        "management": ("executive", ORANGE), "lower_saxony": ("state shareholder", GREEN),
        "owners": ("family shareholder", PURPLE), "investors": ("capital markets", SKY)}

SCALES = [("power", "Power"), ("flexibility", "Flexibility"), ("relational_prior", "Trust")]

fig, ax = plt.subplots(figsize=(10.0, 4.6))
ax.set_xlim(0, 10.6); ax.set_ylim(-0.75, len(ORDER)); ax.axis("off")

X0 = 3.55          # where the three mini-scales start
SW = 2.05          # width of one mini-scale
GAP = 0.35

for j, (fld, lab) in enumerate(SCALES):
    ax.text(X0 + j*(SW+GAP) + SW/2, len(ORDER)-0.28, lab, ha="center",
            fontsize=8.6, color=GREY, fontweight="bold")

for i, key in enumerate(ORDER):
    s = BY_KEY[key]; camp, col = CAMP[key]
    y = len(ORDER) - 1.18 - i
    ax.text(0.02, y+0.16, f"{i+1}.  {s['name']}", fontsize=9.0, fontweight="bold", va="center")
    role = re.sub(r"\s*\([^)]*\)$", "", s["role"])      # drop a trailing parenthetical
    ax.text(0.40, y-0.16, textwrap.shorten(role, 58, placeholder="…"), fontsize=7.0,
            color=GREY, va="center")
    ax.text(0.40, y-0.38, camp, fontsize=6.6, color=col, va="center", style="italic")
    for j, (fld, lab) in enumerate(SCALES):
        x0 = X0 + j*(SW+GAP); v = s[fld]["value"]
        ax.hlines(y+0.04, x0, x0+SW, color=LGREY, lw=1.4, zorder=1)
        ax.scatter([x0 + SW*v/10.0], [y+0.04], s=64, color=col, zorder=3,
                   edgecolor="white", linewidth=0.7)
        ax.text(x0 + SW*v/10.0, y+0.30, str(v), ha="center", fontsize=7.0, color=GREY)

ax.set_title("Six parties, one table: the configured negotiation position of each stakeholder",
             fontsize=10.4, fontweight="bold", loc="left", pad=14)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "Fig 7.2 - Case Stakeholder Map.png"), facecolor="white")
print("  wrote Fig 7.2 - Case Stakeholder Map.png")
