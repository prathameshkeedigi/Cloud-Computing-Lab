"""
Cloud Computing - Experiment 1
Performance Analysis of Type-1 (Proxmox VE) and Type-2 (VMware Workstation) Hypervisors

Reads  : ../results/sysbench_results.csv
         ../results/type2_vm_resources.csv
Writes : ../graphs/*.png

Usage  : python scripts/generate_graphs.py   (run from the CC_Experiment_1 folder)
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")
OUT = os.path.join(ROOT, "graphs")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- data ----
df = pd.read_csv(os.path.join(RES, "sysbench_results.csv"))
t1 = df[df["Type"] == "Type-1"].iloc[0]
t2 = df[df["Type"] == "Type-2"].iloc[0]

C1, C2 = "#2563EB", "#EA580C"          # Type-1 blue, Type-2 orange
L1 = "Type-1\nProxmox VE"
L2 = "Type-2\nVMware Workstation"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.titlesize": 14, "axes.titleweight": "bold",
    "axes.labelsize": 12, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True,
    "grid.linestyle": "--", "grid.alpha": 0.35,
    "figure.dpi": 110, "savefig.dpi": 200,
    "savefig.bbox": "tight", "legend.frameon": False,
})


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), facecolor="white")
    plt.close(fig)
    print("saved", name)


def pct(a, b):
    """Percentage change from a to b."""
    return (b - a) / a * 100


# ------------------------------------------------ 01 architecture diagram --
fig, axes = plt.subplots(1, 2, figsize=(13, 6.2))


def stack(ax, layers, title, accent):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis("off")
    ax.set_title(title, color=accent, fontsize=15)
    y = 0.4
    for text, h, color, tcolor in layers:
        ax.add_patch(FancyBboxPatch((0.6, y), 8.8, h - 0.2, boxstyle="round,pad=0.02,rounding_size=0.15",
                                    facecolor=color, edgecolor="black", lw=1))
        ax.text(5, y + (h - 0.2) / 2, text, ha="center", va="center", fontsize=11.5,
                color=tcolor, fontweight="bold")
        y += h


vm = "#E5E7EB"
stack(axes[0], [
    ("Physical Hardware (CPU, RAM, Disk, NIC)", 1.6, "#374151", "white"),
    ("Type-1 Hypervisor  -  Proxmox VE (KVM)\nruns DIRECTLY on hardware", 2.0, C1, "white"),
    ("Guest VM: Ubuntu\n(CC-Experiment1-type1)", 2.2, vm, "black"),
    ("Sysbench CPU test", 1.4, "#DBEAFE", "black"),
], "Type-1 (Bare-metal)", C1)
stack(axes[1], [
    ("Physical Hardware (Intel Core i7-14700)", 1.4, "#374151", "white"),
    ("Host Operating System (Windows)", 1.4, "#9CA3AF", "black"),
    ("Type-2 Hypervisor  -  VMware Workstation\nruns as an APPLICATION on the host OS", 1.8, C2, "white"),
    ("Guest VM: Ubuntu 22.04.5 LTS (master)", 1.6, vm, "black"),
    ("Sysbench CPU test", 1.2, "#FFEDD5", "black"),
], "Type-2 (Hosted)", C2)
fig.suptitle("Fig. 1 - Software Stack of the Two Hypervisor Types", fontsize=15, fontweight="bold")
save(fig, "01_hypervisor_architecture.png")

# ------------------------------------------------ 02 events per second -----
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 5.2), gridspec_kw={"width_ratios": [1.15, 1]})
vals = [t1.Events_per_sec, t2.Events_per_sec]
b = a1.bar([L1, L2], vals, color=[C1, C2], edgecolor="black", lw=0.6, width=0.55)
for bar, v in zip(b, vals):
    a1.text(bar.get_x() + bar.get_width() / 2, v + 25, f"{v:,.2f}", ha="center", fontweight="bold")
a1.set_ylim(0, 2000)
a1.set_ylabel("Events per second  (higher is better)")
a1.set_title("(a) Full scale (starting at 0)")
a1.grid(axis="x", visible=False)
b = a2.bar([L1, L2], vals, color=[C1, C2], edgecolor="black", lw=0.6, width=0.55)
for bar, v in zip(b, vals):
    a2.text(bar.get_x() + bar.get_width() / 2, v + 2, f"{v:,.2f}", ha="center", fontweight="bold")
a2.set_ylim(1690, 1775)
a2.set_title("(b) Zoomed view (axis starts at 1690)")
a2.annotate(f"+{pct(vals[0], vals[1]):.2f}%", xy=(1, vals[1]), xytext=(0.5, 1765),
            ha="center", fontsize=13, fontweight="bold", color=C2,
            arrowprops=dict(arrowstyle="->", color=C2))
a2.grid(axis="x", visible=False)
fig.suptitle("Fig. 2 - CPU Throughput: Sysbench Events per Second", fontsize=15, fontweight="bold")
fig.tight_layout()
save(fig, "02_events_per_second.png")

# ------------------------------------------------ 03 total events + time --
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 5))
ev = [t1.Total_events, t2.Total_events]
b = a1.bar([L1, L2], ev, color=[C1, C2], edgecolor="black", lw=0.6, width=0.55)
for bar, v in zip(b, ev):
    a1.text(bar.get_x() + bar.get_width() / 2, v + 200, f"{int(v):,}", ha="center", fontweight="bold")
a1.set_ylim(0, 20000)
a1.set_ylabel("Events completed in 10 s")
a1.set_title(f"(a) Total events  (+{int(ev[1] - ev[0])} for Type-2)")
a1.grid(axis="x", visible=False)
tpe = [t1.Total_time_s / t1.Total_events * 1000, t2.Total_time_s / t2.Total_events * 1000]
b = a2.bar([L1, L2], tpe, color=[C1, C2], edgecolor="black", lw=0.6, width=0.55)
for bar, v in zip(b, tpe):
    a2.text(bar.get_x() + bar.get_width() / 2, v + 0.01, f"{v:.4f} ms", ha="center", fontweight="bold")
a2.set_ylim(0, 0.7)
a2.set_ylabel("Time per event (ms)  (lower is better)")
a2.set_title("(b) Average time per event = total time / events")
a2.grid(axis="x", visible=False)
fig.suptitle("Fig. 3 - Work Completed in the Fixed 10-Second Test", fontsize=15, fontweight="bold")
fig.tight_layout()
save(fig, "03_total_events_and_time_per_event.png")

# ---------------------------------------------------- 04 latency ---------
metrics = ["Min", "Average", "95th percentile", "Max"]
v1 = [t1.Lat_min_ms, t1.Lat_avg_ms, t1.Lat_p95_ms, t1.Lat_max_ms]
v2 = [t2.Lat_min_ms, t2.Lat_avg_ms, t2.Lat_p95_ms, t2.Lat_max_ms]
x = np.arange(len(metrics))
w = 0.36
fig, ax = plt.subplots(figsize=(10.5, 5.6))
b1 = ax.bar(x - w / 2, v1, w, color=C1, edgecolor="black", lw=0.6, label="Type-1 (Proxmox VE)")
b2 = ax.bar(x + w / 2, v2, w, color=C2, edgecolor="black", lw=0.6, label="Type-2 (VMware Workstation)")
for bars, vals in [(b1, v1), (b2, v2)]:
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.04, f"{v:.2f}", ha="center",
                fontsize=10, fontweight="bold")
ax.set_xticks(x, metrics)
ax.set_ylim(0, 3.2)
ax.set_ylabel("Latency per event (ms)  (lower is better)")
ax.set_title("Fig. 4 - Event Latency Statistics")
ax.legend(loc="upper left")
ax.grid(axis="x", visible=False)
save(fig, "04_latency_comparison.png")

# ---------------------------------------------- 05 latency consistency ----
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 5))
spread = [t1.Lat_max_ms - t1.Lat_min_ms, t2.Lat_max_ms - t2.Lat_min_ms]
b = a1.bar([L1, L2], spread, color=[C1, C2], edgecolor="black", lw=0.6, width=0.55)
for bar, v in zip(b, spread):
    a1.text(bar.get_x() + bar.get_width() / 2, v + 0.04, f"{v:.2f} ms", ha="center", fontweight="bold")
a1.set_ylim(0, 2.6)
a1.set_ylabel("Max - Min latency (ms)")
a1.set_title("(a) Latency spread  (lower = more stable)")
a1.grid(axis="x", visible=False)
ratio = [t1.Lat_max_ms / t1.Lat_avg_ms, t2.Lat_max_ms / t2.Lat_avg_ms]
b = a2.bar([L1, L2], ratio, color=[C1, C2], edgecolor="black", lw=0.6, width=0.55)
for bar, v in zip(b, ratio):
    a2.text(bar.get_x() + bar.get_width() / 2, v + 0.08, f"{v:.2f}x", ha="center", fontweight="bold")
a2.axhline(1, color="black", ls=":", lw=1)
a2.set_ylim(0, 5.5)
a2.set_ylabel("Max latency / Average latency")
a2.set_title("(b) Worst event vs typical event")
a2.grid(axis="x", visible=False)
fig.suptitle("Fig. 5 - Latency Consistency (Jitter)", fontsize=15, fontweight="bold")
fig.tight_layout()
save(fig, "05_latency_consistency.png")

# ------------------------------------------ 06 relative performance -------
# Every metric scored so that Type-1 = 100 and higher = better for Type-2.
names = ["Events / sec", "Total events", "Avg latency", "95th pct latency", "Max latency"]
rel = [t2.Events_per_sec / t1.Events_per_sec * 100,
       t2.Total_events / t1.Total_events * 100,
       t1.Lat_avg_ms / t2.Lat_avg_ms * 100,
       t1.Lat_p95_ms / t2.Lat_p95_ms * 100,
       t1.Lat_max_ms / t2.Lat_max_ms * 100]
fig, ax = plt.subplots(figsize=(10.5, 5.2))
y = np.arange(len(names))[::-1]
ax.barh(y, [100] * len(names), 0.38, color=C1, edgecolor="black", lw=0.6,
        label="Type-1 (Proxmox VE) = 100", align="edge")
ax.barh(y - 0.38, rel, 0.38, color=C2, edgecolor="black", lw=0.6,
        label="Type-2 (VMware Workstation)", align="edge")
for yi, r in zip(y, rel):
    ax.text(r + 3, yi - 0.19, f"{r:.1f}  ({r - 100:+.1f}%)", va="center", fontweight="bold", color=C2)
ax.set_yticks(y, names)
ax.set_xlim(0, 330)
ax.axvline(100, color="black", ls=":", lw=1)
ax.set_xlabel("Relative score (Type-1 = 100, higher is better)")
ax.set_title("Fig. 6 - Type-2 Performance Relative to Type-1")
ax.legend(loc="upper right")
ax.grid(axis="y", visible=False)
save(fig, "06_relative_performance.png")

# ------------------------------------------- 07 Type-2 VM resources -------
res = pd.read_csv(os.path.join(RES, "type2_vm_resources.csv"))
mem = res[res["Resource"] == "Memory"].iloc[0]
disk = res[res["Resource"] == "Root_disk_/dev/sda3"].iloc[0]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 5))
parts = [mem.Used, mem.Buff_cache, mem.Free]
a1.pie(parts, labels=[f"Used\n{mem.Used} GiB", f"Buffer / cache\n{mem.Buff_cache} GiB",
                      f"Free\n{mem.Free} GiB"],
       colors=[C2, "#FED7AA", "#E5E7EB"], startangle=90,
       wedgeprops=dict(width=0.42, edgecolor="white"), textprops=dict(fontsize=10.5))
a1.text(0, 0, f"{mem.Total} GiB\ntotal RAM", ha="center", va="center", fontsize=12, fontweight="bold")
a1.set_title("(a) Memory  (free -h)")
a2.barh(["/dev/sda3  ( / )"], [disk.Used], color=C2, edgecolor="black", lw=0.6, label=f"Used {disk.Used:.0f} GB")
a2.barh(["/dev/sda3  ( / )"], [disk.Free], left=[disk.Used], color="#E5E7EB", edgecolor="black",
        lw=0.6, label=f"Available {disk.Free} GB")
a2.set_xlim(0, 20)
a2.set_xlabel("GB  (20 GB virtual disk)")
a2.set_title("(b) Root disk  (df -h): 65% used")
a2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
a2.grid(axis="y", visible=False)
fig.suptitle("Fig. 7 - Type-2 VM Resource Snapshot Before the Benchmark", fontsize=15, fontweight="bold")
fig.tight_layout()
save(fig, "07_type2_vm_resources.png")

# ------------------------------------------------------ 08 dashboard -----
fig = plt.figure(figsize=(14, 7.6))
gs = fig.add_gridspec(2, 3, height_ratios=[0.8, 1.25], hspace=0.4, wspace=0.3)
kpis = [("Throughput difference", f"+{pct(t1.Events_per_sec, t2.Events_per_sec):.2f}%",
         "Type-2 higher events/sec", C2),
        ("Average latency", f"{t1.Lat_avg_ms:.2f} vs {t2.Lat_avg_ms:.2f} ms",
         "practically equal", "#374151"),
        ("Max latency", f"{t1.Lat_max_ms:.2f} vs {t2.Lat_max_ms:.2f} ms",
         "Type-1 showed more jitter", C1)]
for i, (title, big, small, c) in enumerate(kpis):
    ax = fig.add_subplot(gs[0, i])
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes,
                               facecolor="#F9FAFB", edgecolor=c, lw=2.5))
    ax.text(0.5, 0.76, title.upper(), ha="center", fontsize=11, color="#374151", transform=ax.transAxes)
    ax.text(0.5, 0.42, big, ha="center", fontsize=20, fontweight="bold", color=c, transform=ax.transAxes)
    ax.text(0.5, 0.13, small, ha="center", fontsize=11, color="#374151", transform=ax.transAxes)
ax = fig.add_subplot(gs[1, :])
ax.axis("off")
rows = [
    ["Events per second", f"{t1.Events_per_sec:.2f}", f"{t2.Events_per_sec:.2f}", "Higher", "Type-2"],
    ["Total events (10 s)", f"{int(t1.Total_events):,}", f"{int(t2.Total_events):,}", "Higher", "Type-2"],
    ["Total time (s)", f"{t1.Total_time_s:.4f}", f"{t2.Total_time_s:.4f}", "Fixed", "Equal"],
    ["Average latency (ms)", f"{t1.Lat_avg_ms:.2f}", f"{t2.Lat_avg_ms:.2f}", "Lower", "Type-2 (marginal)"],
    ["95th percentile (ms)", f"{t1.Lat_p95_ms:.2f}", f"{t2.Lat_p95_ms:.2f}", "Lower", "Type-2"],
    ["Max latency (ms)", f"{t1.Lat_max_ms:.2f}", f"{t2.Lat_max_ms:.2f}", "Lower", "Type-2"],
]
tbl = ax.table(cellText=rows, colLabels=["Metric", "Type-1 Proxmox VE", "Type-2 VMware",
                                         "Better if", "Better result"],
               loc="center", cellLoc="center")
tbl.auto_set_font_size(False)
tbl.set_fontsize(11.5)
tbl.scale(1, 2.0)
for (r, c), cell in tbl.get_celld().items():
    if r == 0:
        cell.set_facecolor("#1F2937")
        cell.set_text_props(color="white", fontweight="bold")
    elif c == 1:
        cell.set_facecolor("#EFF6FF")
    elif c == 2:
        cell.set_facecolor("#FFF7ED")
fig.suptitle("Fig. 8 - Experiment 1 Summary: sysbench cpu --cpu-max-prime=20000 (1 thread, 10 s)",
             fontsize=15, fontweight="bold")
save(fig, "08_summary_dashboard.png")

print("\nEvents/sec difference: %+.2f%%" % pct(t1.Events_per_sec, t2.Events_per_sec))
print("All figures written to", OUT)
