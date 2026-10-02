"""
Cloud Computing - Experiment 2
Performance Analysis of Virtual Machines and Containers

Reads  : ../results/processed/*.csv
Writes : ../graphs/*.png

Usage  : python scripts/generate_graphs.py   (run from the CC_Experiment_2 folder)
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PRO = os.path.join(ROOT, "results", "processed")
OUT = os.path.join(ROOT, "graphs")
os.makedirs(OUT, exist_ok=True)

cpu = pd.read_csv(os.path.join(PRO, "cpu_scalability.csv"))
base = pd.read_csv(os.path.join(PRO, "baseline_cpu.csv"))
disk = pd.read_csv(os.path.join(PRO, "disk_container.csv"))
status = pd.read_csv(os.path.join(PRO, "experiment_status.csv"), keep_default_na=False)

C_VM, C_CT = "#2563EB", "#0D9488"          # VM blue, container teal
C_R1, C_R2 = "#2563EB", "#7C3AED"          # run 1, run 2
GREY = "#6B7280"

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


r1 = cpu[cpu.run == 1].set_index("threads")
r2 = cpu[cpu.run == 2].set_index("threads")
threads = r1.index.to_numpy()
mean_eps = (r1.events_per_second + r2.events_per_second) / 2

# ------------------------------------------------ 01 architecture ---------
fig, axes = plt.subplots(1, 3, figsize=(16, 6.4), gridspec_kw={"width_ratios": [1, 1, 1.15]})


def stack(ax, layers, title, color, ylim=6.9):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, ylim)
    ax.axis("off")
    ax.set_title(title, color=color, fontsize=14)
    y = 0.3
    for text, h, fc, tc in layers:
        ax.add_patch(FancyBboxPatch((0.5, y), 9, h - 0.18, boxstyle="round,pad=0.02,rounding_size=0.15",
                                    facecolor=fc, edgecolor="black", lw=1))
        ax.text(5, y + (h - 0.18) / 2, text, ha="center", va="center", fontsize=10.5,
                color=tc, fontweight="bold")
        y += h


HW, HOS = "#374151", "#9CA3AF"
stack(axes[0], [("Physical Hardware", 1.2, HW, "white"),
                ("Host OS", 1.1, HOS, "black"),
                ("Hypervisor", 1.2, C_VM, "white"),
                ("Guest OS (full kernel)", 1.5, "#DBEAFE", "black"),
                ("Libraries + App", 1.3, "#EFF6FF", "black")],
      "(a) Virtual Machine", C_VM)
stack(axes[1], [("Physical Hardware", 1.2, HW, "white"),
                ("Host OS (shared kernel)", 1.5, HOS, "black"),
                ("Docker Engine", 1.2, C_CT, "white"),
                ("Container: Libraries + App\n(no guest kernel)", 1.6, "#CCFBF1", "black")],
      "(b) Container", C_CT)
stack(axes[2], [("Windows host PC (physical hardware)", 1.1, HW, "white"),
                ("VMware Workstation (Type-2 hypervisor)", 1.1, "#EA580C", "white"),
                ("Ubuntu 22.04 VM  'adarsh-virtual-machine'\n4 vCPU | 7.7 GiB RAM", 1.4, "#DBEAFE", "black"),
                ("VM tests: sysbench run directly\nin the Ubuntu VM", 1.3, "#EFF6FF", "black"),
                ("Docker 29.1.3 inside the VM ->\ncontainer tests (fio, FastAPI)", 1.4, "#CCFBF1", "black")],
      "(c) This experiment\n(Docker runs INSIDE the VM)", "#111827")
fig.suptitle("Fig. 1 - VM vs Container Architecture and the Test Setup Used",
             fontsize=15, fontweight="bold", y=1.04)
save(fig, "01_architecture_vm_vs_container.png")

# ------------------------------------------- 02 CPU scalability -----------
fig, ax = plt.subplots(figsize=(10, 5.8))
ideal = mean_eps.loc[1] * np.minimum(threads, 4)
ax.plot(threads, mean_eps.loc[1] * threads, ls=":", color="black", lw=1.2,
        label="Ideal linear scaling (from 1 thread)")
ax.plot(threads, ideal, ls="--", color=GREY, lw=1.2, label="Ideal, capped at 4 vCPU")
ax.plot(threads, r1.events_per_second, "o-", color=C_R1, lw=2.2, ms=8, label="VM - run 1")
ax.plot(threads, r2.events_per_second, "s-", color=C_R2, lw=2.2, ms=8, label="VM - run 2")
for t in threads:
    a, b = r1.events_per_second[t], r2.events_per_second[t]
    ax.annotate(f"{a:,.0f}", (t, a), xytext=(10, -18), textcoords="offset points", color=C_R1, fontsize=9.5)
    ax.annotate(f"{b:,.0f}", (t, b), xytext=(-48, 10), textcoords="offset points", color=C_R2, fontsize=9.5)
ax.axvline(4, color="#DC2626", ls="-.", lw=1.2)
ax.text(4.1, 13000, "4 vCPU limit\nof the VM", color="#DC2626", fontsize=10)
ax.set_xticks(threads)
ax.set_xlim(0.5, 8.8)
ax.set_ylim(0, 15000)
ax.set_xlabel("Number of sysbench threads")
ax.set_ylabel("Events per second (higher is better)")
ax.set_title("Fig. 2 - CPU Throughput vs Threads (VM, prime limit 20000, 30 s)")
ax.legend(loc="upper left")
save(fig, "02_cpu_scalability.png")

# ------------------------------------- 03 speedup + efficiency -----------
sp1 = r1.events_per_second / r1.events_per_second[1]
sp2 = r2.events_per_second / r2.events_per_second[1]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5))
a1.plot(threads, threads, ":", color="black", label="Ideal")
a1.plot(threads, sp1, "o-", color=C_R1, lw=2, label="Run 1")
a1.plot(threads, sp2, "s-", color=C_R2, lw=2, label="Run 2")
for t in threads[2:]:
    a1.annotate(f"{sp1[t]:.2f}x", (t, sp1[t]), xytext=(6, -15), textcoords="offset points", color=C_R1, fontsize=9.5)
    a1.annotate(f"{sp2[t]:.2f}x", (t, sp2[t]), xytext=(6, 6), textcoords="offset points", color=C_R2, fontsize=9.5)
a1.set_xticks(threads)
a1.set_xlabel("Threads")
a1.set_ylabel("Speedup vs 1 thread")
a1.set_title("(a) Speedup")
a1.legend(loc="upper left")
x = np.arange(len(threads))
w = 0.38
e1, e2 = sp1 / threads * 100, sp2 / threads * 100
b1 = a2.bar(x - w / 2, e1, w, color=C_R1, edgecolor="black", lw=0.6, label="Run 1")
b2 = a2.bar(x + w / 2, e2, w, color=C_R2, edgecolor="black", lw=0.6, label="Run 2")
for bars, vals in [(b1, e1), (b2, e2)]:
    for b, v in zip(bars, vals):
        a2.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.0f}", ha="center", fontsize=9.5, fontweight="bold")
a2.axhline(100, color="black", ls=":", lw=1)
a2.set_xticks(x, [str(t) for t in threads])
a2.set_ylim(0, 120)
a2.set_xlabel("Threads")
a2.set_ylabel("Efficiency = speedup / threads (%)")
a2.set_title("(b) Efficiency (drops at 8 threads > 4 vCPU)")
a2.legend(loc="upper right", ncol=2)
a2.grid(axis="x", visible=False)
fig.suptitle("Fig. 3 - CPU Scaling Efficiency in the VM", fontsize=15, fontweight="bold")
fig.tight_layout()
save(fig, "03_cpu_speedup_efficiency.png")

# ---------------------------------------------- 04 latency ---------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5))
for r, c, m, lab in [(r1, C_R1, "o", "Run 1"), (r2, C_R2, "s", "Run 2")]:
    a1.plot(threads, r.lat_avg_ms, m + "-", color=c, lw=2, label=f"{lab} - average")
    a1.plot(threads, r.lat_p95_ms, m + "--", color=c, lw=1.5, alpha=0.7, label=f"{lab} - 95th percentile")
a1.set_xticks(threads)
a1.set_xlabel("Threads")
a1.set_ylabel("Latency per event (ms)")
a1.set_title("(a) Average and 95th-percentile latency")
a1.legend(fontsize=9.5)
b1 = a2.bar(x - w / 2, r1.lat_max_ms, w, color=C_R1, edgecolor="black", lw=0.6, label="Run 1")
b2 = a2.bar(x + w / 2, r2.lat_max_ms, w, color=C_R2, edgecolor="black", lw=0.6, label="Run 2")
for bars, vals in [(b1, r1.lat_max_ms), (b2, r2.lat_max_ms)]:
    for b, v in zip(bars, vals):
        a2.text(b.get_x() + b.get_width() / 2, v + 0.3, f"{v:.2f}", ha="center", fontsize=9.5)
a2.set_xticks(x, [str(t) for t in threads])
a2.set_xlabel("Threads")
a2.set_ylabel("Maximum latency (ms)")
a2.set_title("(b) Maximum (worst-case) latency")
a2.legend()
a2.grid(axis="x", visible=False)
fig.suptitle("Fig. 4 - Event Latency vs Threads: waiting starts when threads > vCPUs",
             fontsize=15, fontweight="bold")
fig.tight_layout()
save(fig, "04_cpu_latency_vs_threads.png")

# ------------------------------------ 05 4-thread repeatability ----------
labels = ["Baseline\n(terminal)", "Baseline\n(saved file)", "Scalability\nrun 1", "Scalability\nrun 2"]
vals = [base.events_per_second[0], base.events_per_second[1],
        r1.events_per_second[4], r2.events_per_second[4]]
mean, std = np.mean(vals), np.std(vals, ddof=1)
fig, ax = plt.subplots(figsize=(10, 5.4))
bars = ax.bar(labels, vals, color=["#93C5FD", "#93C5FD", C_R1, C_R2], edgecolor="black", lw=0.6,
              width=0.55, zorder=3)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 12, f"{v:,.2f}", ha="center", fontweight="bold")
ax.axhline(mean, color="#DC2626", lw=1.5, zorder=4, label=f"Mean = {mean:,.2f}")
ax.axhspan(mean - std, mean + std, color="#FCA5A5", alpha=0.3, zorder=0, label=f"± 1 std dev ({std:,.2f})")
ax.set_ylim(6400, 6950)
ax.set_ylabel("Events per second (axis starts at 6400)")
ax.set_title(f"Fig. 5 - Repeatability of the 4-Thread CPU Test (CV = {std / mean * 100:.2f}%)")
ax.legend(loc="upper left")
ax.grid(axis="x", visible=False)
save(fig, "05_cpu_4thread_repeatability.png")

# --------------------------------------- 06 thread fairness --------------
fig, ax = plt.subplots(figsize=(10, 5.2))
cv1 = r1.fairness_events_stddev / r1.fairness_events_avg * 100
cv2 = r2.fairness_events_stddev / r2.fairness_events_avg * 100
b1 = ax.bar(x - w / 2, cv1, w, color=C_R1, edgecolor="black", lw=0.6, label="Run 1")
b2 = ax.bar(x + w / 2, cv2, w, color=C_R2, edgecolor="black", lw=0.6, label="Run 2")
for bars, vals in [(b1, cv1), (b2, cv2)]:
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.05, f"{v:.2f}%", ha="center", fontsize=9.5)
ax.set_xticks(x, [str(t) for t in threads])
ax.set_xlabel("Threads")
ax.set_ylabel("Std dev of events per thread (% of average)")
ax.set_title("Fig. 6 - Thread Fairness: how evenly work was shared")
ax.legend()
ax.grid(axis="x", visible=False)
save(fig, "06_thread_fairness.png")

# --------------------------------------------- 07 disk throughput --------
sw = disk[disk.test == "seq-write"].set_index("run")
rr = disk[disk.test == "random-read"].set_index("run")
fig, axs = plt.subplots(1, 3, figsize=(15, 5))
for ax, col, title, unit, fmt in [
        (axs[0], sw.bandwidth_MBps, "(a) Sequential write, 1 MiB blocks", "MB/s", "{:,.0f}"),
        (axs[1], rr.bandwidth_MBps, "(b) Random read, 4 KiB blocks", "MB/s", "{:.1f}"),
        (axs[2], rr.iops, "(c) Random read IOPS", "IOPS", "{:,.0f}")]:
    b = ax.bar(["Run 1", "Run 2"], col, color=[C_CT, "#5EEAD4"], edgecolor="black", lw=0.6, width=0.55)
    for bar, v in zip(b, col):
        ax.text(bar.get_x() + bar.get_width() / 2, v * 1.02, fmt.format(v), ha="center", fontweight="bold")
    ax.set_ylim(0, col.max() * 1.18)
    ax.set_title(title)
    ax.set_ylabel(unit)
    ax.grid(axis="x", visible=False)
fig.suptitle("Fig. 7 - Disk I/O inside the Docker Container (fio 3.36, direct=1, 30 s)",
             fontsize=15, fontweight="bold")
fig.tight_layout()
save(fig, "07_disk_container_throughput.png")

# --------------------------------------------- 08 disk latency -----------
pcts = ["p50_us", "p90_us", "p99_us", "p99_9_us"]
names = ["50th", "90th", "99th", "99.9th"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5))
xx = np.arange(len(pcts))
for ax, df_, title in [(a1, sw, "(a) Sequential write"), (a2, rr, "(b) Random read")]:
    v1, v2 = df_.loc[1, pcts].to_numpy(float), df_.loc[2, pcts].to_numpy(float)
    b1 = ax.bar(xx - w / 2, v1, w, color=C_CT, edgecolor="black", lw=0.6, label="Run 1")
    b2 = ax.bar(xx + w / 2, v2, w, color="#5EEAD4", edgecolor="black", lw=0.6, label="Run 2")
    for bars, vals in [(b1, v1), (b2, v2)]:
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v * 1.12, f"{v:,.0f}", ha="center", fontsize=9)
    ax.set_yscale("log")
    ax.set_xticks(xx, [n + " pct" for n in names])
    ax.set_ylabel("Completion latency (microseconds, log)")
    ax.set_title(title)
    ax.legend(loc="upper left")
    ax.grid(axis="x", visible=False)
a1.set_ylim(100, 20000)
a2.set_ylim(10, 1500)
fig.suptitle("Fig. 8 - Disk Latency Percentiles inside the Container", fontsize=15, fontweight="bold")
fig.tight_layout()
save(fig, "08_disk_container_latency.png")

# ---------------------------------------- 09 experiment coverage ---------
cmap = {"Measured": "#16A34A", "Done": "#16A34A", "Partial": "#F59E0B",
        "Not captured": "#E5E7EB", "-": "white"}
fig, ax = plt.subplots(figsize=(13, 6.2))
ax.axis("off")
cells = [[r.step, r.experiment, r.vm_status, r.container_status, r.note] for r in status.itertuples()]
tbl = ax.table(cellText=cells, colLabels=["Step", "Experiment", "VM", "Container", "Note"],
               loc="center", cellLoc="left", colWidths=[0.07, 0.21, 0.12, 0.12, 0.48])
tbl.auto_set_font_size(False)
tbl.set_fontsize(10.5)
tbl.scale(1, 2.0)
for (r, c), cell in tbl.get_celld().items():
    if r == 0:
        cell.set_facecolor("#1F2937")
        cell.set_text_props(color="white", fontweight="bold")
    elif c in (2, 3):
        txt = cell.get_text().get_text()
        cell.set_facecolor(cmap.get(txt, "white"))
        if txt in ("Measured", "Done"):
            cell.set_text_props(color="white", fontweight="bold")
ax.set_title("Fig. 9 - What Was Measured in This Experiment (from the screenshots)",
             fontsize=15, fontweight="bold")
save(fig, "09_experiment_coverage.png")

# ---------------------------------------------- 10 dashboard -------------
fig = plt.figure(figsize=(14, 7.6))
gs = fig.add_gridspec(2, 4, height_ratios=[0.75, 1.25], hspace=0.38, wspace=0.3)
kpis = [("Peak CPU (VM)", f"{max(r1.events_per_second.max(), r2.events_per_second.max()):,.0f}",
         "events/s at 4 threads", C_VM),
        ("Speedup 1 -> 4 threads", f"{mean_eps[4] / mean_eps[1]:.2f}x", "on 4 vCPU", C_VM),
        ("Container seq. write", f"{sw.bandwidth_MBps.mean():,.0f} MB/s", "average of 2 runs", C_CT),
        ("Container random read", f"{rr.iops.mean() / 1000:.1f}k IOPS", "average of 2 runs", C_CT)]
for i, (title, big, small, c) in enumerate(kpis):
    ax = fig.add_subplot(gs[0, i])
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor="#F9FAFB", edgecolor=c, lw=2.5))
    ax.text(0.5, 0.77, title.upper(), ha="center", fontsize=10, color="#374151", transform=ax.transAxes)
    ax.text(0.5, 0.43, big, ha="center", fontsize=19, fontweight="bold", color=c, transform=ax.transAxes)
    ax.text(0.5, 0.14, small, ha="center", fontsize=10, color="#374151", transform=ax.transAxes)
ax = fig.add_subplot(gs[1, :])
ax.axis("off")
rows = [[f"{t}", f"{r1.events_per_second[t]:,.2f}", f"{r2.events_per_second[t]:,.2f}",
         f"{mean_eps[t]:,.2f}", f"{mean_eps[t] / mean_eps[1]:.2f}x",
         f"{(r1.lat_avg_ms[t] + r2.lat_avg_ms[t]) / 2:.2f}"] for t in threads]
tbl = ax.table(cellText=rows, colLabels=["Threads", "Run 1 (events/s)", "Run 2 (events/s)",
                                         "Mean (events/s)", "Speedup", "Avg latency (ms)"],
               loc="center", cellLoc="center")
tbl.auto_set_font_size(False)
tbl.set_fontsize(11.5)
tbl.scale(1, 2.2)
for (r, c), cell in tbl.get_celld().items():
    if r == 0:
        cell.set_facecolor("#1F2937")
        cell.set_text_props(color="white", fontweight="bold")
    elif r == 4:
        cell.set_facecolor("#FEF2F2")
ax.set_title("VM CPU scalability summary (8 threads on 4 vCPU = oversubscribed)", fontweight="bold")
fig.suptitle("Fig. 10 - Experiment 2 Performance Summary", fontsize=15, fontweight="bold")
save(fig, "10_summary_dashboard.png")

print(f"\n4-thread mean {mean:.2f}, std {std:.2f}, CV {std / mean * 100:.2f}%")
print("mean eps:", mean_eps.round(2).to_dict())
print("All figures written to", OUT)
