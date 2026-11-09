"""Generate the three explanatory diagrams for the README.

All three are drawn from the example data in examples/sample_eta_map.json.
No real trip, key, ticket or vehicle is used anywhere.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

OUT = os.path.join(os.path.dirname(__file__), "images")
os.makedirs(OUT, exist_ok=True)

NAVY = "#1f3552"
TEAL = "#0e7c7b"
AMBER = "#c47a12"
LIGHT = "#eef3f7"
GREY = "#5a6b7a"


def box(ax, x, y, w, h, title, body, face="white", edge=NAVY, title_c=NAVY):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                facecolor=face, edgecolor=edge, linewidth=1.6))
    ax.text(x + w / 2, y + h - 0.28, title, ha="center", va="top",
            fontsize=12, fontweight="bold", color=title_c)
    ax.text(x + w / 2, y + h - 0.62, body, ha="center", va="top",
            fontsize=9.5, color="#24344a", linespacing=1.5)


def arrow(ax, x1, y1, x2, y2, label=""):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=16, linewidth=1.8, color=TEAL))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.12, label,
                ha="center", va="bottom", fontsize=9, color=TEAL, fontweight="bold")


# 1. How it works -------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 4.6))
ax.set_xlim(0, 11); ax.set_ylim(0, 4.6); ax.axis("off")
ax.text(5.5, 4.35, "How it works: from a tracking link to a live position",
        ha="center", fontsize=14, fontweight="bold", color=NAVY)
box(ax, 0.2, 1.9, 2.3, 1.7, "1. Your tracking link",
    "RedBus / operator sends\na link like trkg.in/...\nIt opens the Trackingo\ntracker page", face=LIGHT)
box(ax, 3.0, 1.9, 2.3, 1.7, "2. Trackingo page",
    "The page shows a map\nand a stop timeline.\nIt polls its own API\nevery ~20 seconds", face="white")
box(ax, 5.8, 1.9, 2.3, 1.7, "3. Internal API",
    "GET /api/live/eta_map\n?current_status=true\n&key=YOUR_KEY\nReturns JSON, no login", face="#e6f4f3", edge=TEAL, title_c=TEAL)
box(ax, 8.6, 1.9, 2.2, 1.7, "4. This tool",
    "Calls the same API\ndirectly and prints\nposition, speed and\nETA per stop", face="#fff4e0", edge=AMBER, title_c=AMBER)
arrow(ax, 2.5, 2.75, 3.0, 2.75)
arrow(ax, 5.3, 2.75, 5.8, 2.75)
arrow(ax, 8.1, 2.75, 8.6, 2.75)
ax.text(5.5, 1.35, "The key insight: RedBus's public status text (\"Next: K R Puram\") is not a GPS position.",
        ha="center", fontsize=11, color=AMBER, fontweight="bold")
ax.text(5.5, 0.85, "The Trackingo API is. Trust the GPS fix, speed and timestamp — not the status line.",
        ha="center", fontsize=11, color=NAVY)
ax.text(5.5, 0.35, "The API is internal, not a published developer API. It can change without notice.",
        ha="center", fontsize=9, color=GREY)
fig.tight_layout()
fig.savefig(f"{OUT}/how-it-works.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# 2. What the API returns ----------------------------------------------
fig, ax = plt.subplots(figsize=(11, 5.2))
ax.set_xlim(0, 11); ax.set_ylim(0, 5.2); ax.axis("off")
ax.text(5.5, 4.9, "What the eta_map response actually contains",
        ha="center", fontsize=14, fontweight="bold", color=NAVY)
ax.text(5.5, 4.5, "GET /api/live/eta_map?current_status=true&key=YOUR_KEY  →  JSON",
        ha="center", fontsize=10.5, color=GREY, family="monospace")
box(ax, 0.3, 2.6, 5.0, 1.5, "Live position  —  current_status_details",
    "lat_long: [13.00515, 77.68488]      speed: 0 km/h\ntimestamp: 10:59:42 PM      location: B. Narayanapura\nstate (hstate): idle", face=LIGHT)
box(ax, 5.7, 2.6, 5.0, 1.5, "Per stop  —  eta_map_data",
    "One row per stop: scheduled, expected,\narrival_time, departure_time, status.\nEmpty arrival = stop not reached yet.", face="#e6f4f3", edge=TEAL, title_c=TEAL)
box(ax, 0.3, 0.7, 5.0, 1.5, "Journey  —  journey_details (separate call)",
    "Operator, vehicle, service, route stops\nand boarding / drop-off details.\nCan include booking / contact fields — keep private.", face="white")
box(ax, 5.7, 0.7, 5.0, 1.5, "Distance  —  distance_details",
    "Distance information for the\njourney. Used for the\nmap view on the tracker page.", face="white")
ax.text(5.5, 0.3, "Example values only, from examples/sample_eta_map.json — not a real trip.",
        ha="center", fontsize=9, color=GREY)
fig.tight_layout()
fig.savefig(f"{OUT}/what-the-api-returns.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# 3. Example timeline ----------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 5.0))
ax.set_xlim(0, 11); ax.set_ylim(0, 5.0); ax.axis("off")
ax.text(5.5, 4.7, "Reading the timeline: scheduled vs expected (example data)",
        ha="center", fontsize=14, fontweight="bold", color=NAVY)
ax.text(5.5, 4.3, "Bus is at B. Narayanapura — speed 0 km/h, idle, GPS 10:59:42 PM. Running 28 minutes late.",
        ha="center", fontsize=11, color=NAVY)
stops = [
    ("Tin Factory", "10:20 PM", "10:28 PM", "+8m", True),
    ("ITI Gate", "10:30 PM", "10:58 PM", "+28m", True),
    ("K R Puram", "10:40 PM", "11:08 PM", "+28m", False),
    ("TC Palya", "10:55 PM", "11:23 PM", "+28m", False),
    ("Bhattarahalli", "11:00 PM", "11:28 PM", "+28m", False),
    ("Hoskote", "11:05 PM", "11:33 PM", "+28m", False),
]
x0, x1 = 0.7, 10.3
ax.plot([x0, x1], [3.1, 3.1], color=NAVY, linewidth=3, solid_capstyle="round", zorder=1)
for i, (name, sched, exp, delay, done) in enumerate(stops):
    x = x0 + i * (x1 - x0) / 5
    col = TEAL if done else AMBER
    ax.plot([x], [3.1], marker="o", markersize=16, color=col,
            markeredgecolor="white", markeredgewidth=2, zorder=3)
    ax.text(x, 3.55, name, ha="center", fontsize=10.5, fontweight="bold", color=NAVY)
    ax.text(x, 2.55, f"sched {sched}", ha="center", fontsize=9, color=GREY)
    ax.text(x, 2.15, f"expected {exp}", ha="center", fontsize=9.5,
            color=col, fontweight="bold")
    ax.text(x, 1.75, delay, ha="center", fontsize=9.5, color=col)
    ax.text(x, 1.35, "departed" if done else "not reached", ha="center",
            fontsize=9, color=col, style="italic")
ax.annotate("bus is here — between\nITI Gate and K R Puram",
            xy=(x0 + 2 * (x1 - x0) / 5, 3.1), xytext=(4.2, 0.55),
            fontsize=10, color=AMBER, fontweight="bold", ha="center",
            arrowprops=dict(arrowstyle="->", color=AMBER, lw=1.8))
ax.text(5.5, 0.15, "If arrival_time is empty, the bus has not reached that stop — however the status text reads.",
        ha="center", fontsize=9.5, color=NAVY)
fig.tight_layout()
fig.savefig(f"{OUT}/example-timeline.png", dpi=200, bbox_inches="tight")
plt.close(fig)

print("wrote", sorted(os.listdir(OUT)))
