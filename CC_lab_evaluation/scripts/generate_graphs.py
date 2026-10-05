"""
CC Lab Evaluation - Library Management microservices
Performance-analysis figure generator.

Reads  : ../results/observation_table.csv   (written by loadtest/run_workloads.py)
         ../results/container_usage.csv
Writes : ../graphs/*.png

Usage  : python scripts/generate_graphs.py   (run from the CC_lab_evaluation folder)
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")
OUT = os.path.join(ROOT, "graphs")
os.makedirs(OUT, exist_ok=True)

obs = pd.read_csv(os.path.join(RES, "observation_table.csv"))
use = pd.read_csv(os.path.join(RES, "container_usage.csv"))

c = obs["concurrency"].to_numpy()
labels = [f"{w}\n({n})" for w, n in zip(obs["workload"], c)]
SERVICES = ["borrow-service", "book-service", "member-service", "notification-service"]
COL = {"borrow-service": "#7C3AED", "book-service": "#2563EB",
       "member-service": "#16A34A", "notification-service": "#EA580C"}
MAIN = "#2563EB"

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


def pivot(col):
    return (use.pivot(index="workload", columns="container", values=col)
            .reindex(obs["workload"])[SERVICES])


def line(ax, y, fmt, color=MAIN, marker="o"):
    ax.plot(c, y, marker + "-", color=color, lw=2.2, ms=8)
    for xi, yi in zip(c, y):
        ax.annotate(fmt.format(yi), (xi, yi), xytext=(0, 9), textcoords="offset points",
                    ha="center", fontsize=9.5, fontweight="bold", color=color)
    ax.set_xscale("log", base=2)
    ax.set_xticks(c, [str(v) for v in c])
    ax.set_xlabel("Concurrent requests (Locust users)")


# ------------------------------------------- 01 response time vs concurrency
fig, ax = plt.subplots(figsize=(9.5, 5.5))
ax.plot(c, obs["avg_response_ms"], "o-", color=MAIN, lw=2.2, ms=8)
for xi, yi in zip(c, obs["avg_response_ms"]):
    ax.annotate(f"{yi:.1f} ms", (xi, yi), xytext=(10, -16), textcoords="offset points",
                fontsize=9.5, fontweight="bold", color=MAIN)
ax.set_xscale("log", base=2)
ax.set_xticks(c, [str(v) for v in c])
ax.set_xlabel("Concurrent requests (Locust users)")
ax.plot(c, obs["median_response_ms"], "s--", color="#16A34A", lw=1.6, label="Median")
ax.plot(c, obs["p95_response_ms"], "^--", color="#DC2626", lw=1.6, label="95th percentile")
ax.plot([], [], "o-", color=MAIN, label="Average")
ax.set_ylim(0, max(obs["p95_response_ms"].max(), obs["avg_response_ms"].max()) * 1.2)
ax.set_ylabel("Response time (ms)")
ax.set_title("Fig. 1 - Concurrent Requests vs Response Time")
ax.legend(loc="upper left")
save(fig, "01_response_time_vs_concurrency.png")

# ---------------------------------------------- 02 throughput vs concurrency
fig, ax = plt.subplots(figsize=(9.5, 5.5))
line(ax, obs["throughput_rps"], "{:.1f}")
ax.set_ylim(0, obs["throughput_rps"].max() * 1.2)
ax.set_ylabel("Throughput (requests / second)")
ax.set_title("Fig. 2 - Concurrent Requests vs Throughput")
save(fig, "02_throughput_vs_concurrency.png")

# --------------------------------------------- 03 CPU per container
cpu = pivot("avg_cpu_pct")
x = np.arange(len(obs))
w = 0.2
fig, ax = plt.subplots(figsize=(11, 5.6))
for i, s in enumerate(SERVICES):
    b = ax.bar(x + (i - 1.5) * w, cpu[s], w, color=COL[s], edgecolor="black", lw=0.5, label=s)
    for bar, v in zip(b, cpu[s]):
        ax.text(bar.get_x() + bar.get_width() / 2, v + cpu.values.max() * 0.01, f"{v:.0f}",
                ha="center", fontsize=8)
ax.set_xticks(x, labels)
ax.set_xlabel("Workload (concurrent requests)")
ax.set_ylabel("Average CPU utilisation (%)  - 100 % = one core")
ax.set_title("Fig. 3 - Concurrent Requests vs CPU Utilisation (per container)")
ax.legend(ncol=2, loc="upper left")
ax.set_ylim(0, cpu.values.max() * 1.25)
ax.grid(axis="x", visible=False)
save(fig, "03_cpu_vs_concurrency.png")

# --------------------------------------------- 04 memory per container
mem = pivot("avg_mem_mib")
fig, ax = plt.subplots(figsize=(11, 5.6))
for i, s in enumerate(SERVICES):
    b = ax.bar(x + (i - 1.5) * w, mem[s], w, color=COL[s], edgecolor="black", lw=0.5, label=s)
    for bar, v in zip(b, mem[s]):
        ax.text(bar.get_x() + bar.get_width() / 2, v + mem.values.max() * 0.01, f"{v:.0f}",
                ha="center", fontsize=8)
ax.set_xticks(x, labels)
ax.set_xlabel("Workload (concurrent requests)")
ax.set_ylabel("Average memory usage (MiB)")
ax.set_title("Fig. 4 - Concurrent Requests vs Memory Utilisation (per container)")
ax.legend(ncol=2, loc="upper left")
ax.set_ylim(0, mem.values.max() * 1.3)
ax.grid(axis="x", visible=False)
save(fig, "04_memory_vs_concurrency.png")

# ------------------------------------ 05 throughput vs response time (knee)
fig, ax = plt.subplots(figsize=(9.5, 5.5))
ax.plot(obs["throughput_rps"], obs["avg_response_ms"], "o-", color=MAIN, lw=2.2, ms=9)
for _, r in obs.iterrows():
    ax.annotate(f"{r.workload} ({r.concurrency})", (r.throughput_rps, r.avg_response_ms),
                xytext=(8, 8), textcoords="offset points", fontsize=10)
ax.set_xlabel("Throughput (requests / second)")
ax.set_ylabel("Average response time (ms)")
ax.set_title("Fig. 5 - Throughput vs Response Time")
save(fig, "05_throughput_vs_response_time.png")

# ------------------------------------------- 06 requests and failures
fig, ax = plt.subplots(figsize=(10, 5.3))
ok = obs["total_requests"] - obs["failed_requests"]
ax.bar(labels, ok, color="#16A34A", edgecolor="black", lw=0.5, label="Successful")
ax.bar(labels, obs["failed_requests"], bottom=ok, color="#DC2626", edgecolor="black", lw=0.5,
       label="Failed")
for i, (t, f) in enumerate(zip(obs["total_requests"], obs["failed_requests"])):
    ax.text(i, t * 1.01, f"{t:,}\n({f} failed, {f / t * 100:.2f} %)", ha="center", fontsize=9)
ax.set_ylim(0, obs["total_requests"].max() * 1.2)
ax.set_xlabel("Workload (concurrent requests)")
ax.set_ylabel("Requests completed in the test window")
ax.set_title("Fig. 6 - Successful vs Failed Requests")
ax.legend(loc="upper left")
ax.grid(axis="x", visible=False)
save(fig, "06_requests_and_failures.png")

# ---------------------------------------- 07 CPU share per service (stacked)
share = cpu.div(cpu.sum(axis=1), axis=0) * 100
fig, ax = plt.subplots(figsize=(10, 5.3))
bottom = np.zeros(len(obs))
for s in SERVICES:
    ax.bar(labels, share[s], bottom=bottom, color=COL[s], edgecolor="white", label=s)
    for i, v in enumerate(share[s]):
        if v > 3.5:
            ax.text(i, bottom[i] + v / 2, f"{v:.0f}%", ha="center", va="center",
                    color="white", fontweight="bold", fontsize=9 if v > 6 else 7.5)
    bottom += share[s].to_numpy()
ax.set_ylim(0, 100)
ax.set_xlabel("Workload (concurrent requests)")
ax.set_ylabel("Share of total CPU used by the app (%)")
ax.set_title("Fig. 7 - Which Microservice Uses the Most CPU?")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=4)
ax.grid(axis="x", visible=False)
save(fig, "07_cpu_share_per_service.png")

# ------------------------------------------------- 08 summary dashboard
fig = plt.figure(figsize=(14, 6.4))
gs = fig.add_gridspec(2, 4, height_ratios=[0.55, 1.2], hspace=0.15, wspace=0.3)
peak = obs.loc[obs["throughput_rps"].idxmax()]
top = cpu.mean().idxmax()
kpis = [("Peak throughput", f"{peak.throughput_rps:.1f} req/s", f"at {peak.concurrency} users", MAIN),
        ("Avg response time", f"{obs.avg_response_ms.iloc[0]:.0f} -> {obs.avg_response_ms.iloc[-1]:.0f} ms",
         "W1 (1 user) -> W5 (16 users)", "#DC2626"),
        ("Failed requests", f"{obs.failed_requests.sum():,}", f"of {obs.total_requests.sum():,}", "#16A34A"),
        ("Busiest service", top.replace("-service", ""), f"avg {cpu[top].mean():.0f}% CPU", COL[top])]
for i, (t, big, small, colr) in enumerate(kpis):
    a = fig.add_subplot(gs[0, i])
    a.axis("off")
    a.add_patch(plt.Rectangle((0, 0), 1, 1, transform=a.transAxes, facecolor="#F9FAFB",
                              edgecolor=colr, lw=2.5))
    a.text(0.5, 0.76, t.upper(), ha="center", fontsize=10, color="#374151", transform=a.transAxes)
    a.text(0.5, 0.42, big, ha="center", fontsize=17, fontweight="bold", color=colr, transform=a.transAxes)
    a.text(0.5, 0.14, small, ha="center", fontsize=10, color="#374151", transform=a.transAxes)
a = fig.add_subplot(gs[1, :])
a.axis("off")
rows = [[r.workload, r.concurrency, f"{r.avg_response_ms:.2f}", f"{r.p95_response_ms:.0f}",
         f"{r.throughput_rps:.2f}", f"{r.failed_requests}", f"{r.total_cpu_pct:.1f}",
         f"{r.total_mem_mib:.1f}"] for r in obs.itertuples()]
tbl = a.table(cellText=rows, colLabels=["Workload", "Concurrency", "Avg resp.\n(ms)", "p95\n(ms)",
                                        "Throughput\n(req/s)", "Failed", "CPU, all 4\n(%)",
                                        "Memory, all 4\n(MiB)"],
              loc="center", cellLoc="center")
tbl.auto_set_font_size(False)
tbl.set_fontsize(11.5)
tbl.scale(1, 2.1)
for (r, cc), cell in tbl.get_celld().items():
    if r == 0:
        cell.set_facecolor("#1F2937")
        cell.set_text_props(color="white", fontweight="bold")
        cell.set_height(cell.get_height() * 1.5)
fig.suptitle("Fig. 8 - Performance Summary: Library Microservices under Varying Workload",
             fontsize=15, fontweight="bold")
save(fig, "08_summary_dashboard.png")

# ----------------------------------------------- 09 Little's Law check
# Little's Law for a closed system: users = throughput x response time.
# If the measurements are consistent, N_calc should equal the real number of users.
n_calc = obs["throughput_rps"] * obs["avg_response_ms"] / 1000
fig, ax = plt.subplots(figsize=(9.5, 5.5))
ax.plot([0.8, 20], [0.8, 20], ":", color="black", lw=1.2, label="Perfect match (y = x)")
ax.plot(c, n_calc, "o", color=MAIN, ms=10, label="Throughput x avg response time")
for xi, yi in zip(c, n_calc):
    ax.annotate(f"{yi:.2f}", (xi, yi), xytext=(10, -14), textcoords="offset points",
                fontsize=10, fontweight="bold", color=MAIN)
ax.set_xscale("log", base=2)
ax.set_yscale("log", base=2)
ax.set_xticks(c, [str(v) for v in c])
ax.set_yticks(c, [str(v) for v in c])
ax.set_xlabel("Concurrent users set in Locust (N)")
ax.set_ylabel("N calculated from measurements")
ax.set_title("Fig. 9 - Little's Law Check: N = Throughput x Response Time")
ax.legend(loc="upper left")
save(fig, "09_littles_law_check.png")

print("\nLittle's Law N:", n_calc.round(2).tolist())
print("\nAll figures written to", OUT)
