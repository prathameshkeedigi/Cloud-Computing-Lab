"""
Figures for Problem 07 (taints and tolerations, GPU-node scenario), built from the measured CSVs.

Usage (from the CC_lab_evaluation_2 folder, after scripts/run_experiment.py):
    python scripts/generate_graphs.py

Inputs : results/placement.csv, events.csv, noexecute_timeline.csv, steps.csv
Outputs: graphs/01_*.png ... graphs/07_*.png and results/placement_summary.csv
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RES, OUT = ROOT / "results", ROOT / "graphs"
OUT.mkdir(exist_ok=True)

CP, GEN, GPU = "taints-lab-control-plane", "taints-lab-worker", "taints-lab-worker2"
PEND = "Pending (no node)"
NODES = [CP, GEN, GPU, PEND]
NLABEL = {CP: "control plane", GEN: "general node (worker)", GPU: "GPU node (worker2)", PEND: "Pending"}
NCOLOR = {CP: "#94a3b8", GEN: "#2563eb", GPU: "#7c3aed", PEND: "#ea580c"}

plt.rcParams.update({"font.size": 10, "axes.titleweight": "bold", "axes.titlesize": 12,
                     "axes.spines.top": False, "axes.spines.right": False})

place = pd.read_csv(RES / "placement.csv", keep_default_na=False)
events = pd.read_csv(RES / "events.csv", keep_default_na=False)
timeline = pd.read_csv(RES / "noexecute_timeline.csv", keep_default_na=False)
steps = pd.read_csv(RES / "steps.csv", keep_default_na=False)

# ---------------------------------------------------------------- summary table (snapshot x workload)
place["row"] = place["snapshot"] + "  [" + place["workload"] + "]"
row_order = list(dict.fromkeys(place["row"]))
summary = (place.groupby(["row", "node"]).size().unstack(fill_value=0)
           .reindex(index=row_order, columns=NODES, fill_value=0))
out = summary.copy()
out.insert(0, "workload", [r.split("[")[1].rstrip("]") for r in out.index])
out.insert(0, "snapshot", [r.split("  [")[0] for r in out.index])
out.columns = ["snapshot", "workload", "control_plane", "general_node_worker", "gpu_node_worker2", "pending"]
out.to_csv(RES / "placement_summary.csv", index=False)


def save(fig, name):
    fig.savefig(OUT / name, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", name)


def box(ax, x, y, w, h, text, fc, fs=9.3, weight="normal", ec="#1e293b"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.4))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, weight=weight)


# ---------------------------------------------------------------- Fig 1 concept
fig, ax = plt.subplots(figsize=(12.5, 6))
ax.set_xlim(0, 12.5); ax.set_ylim(0.9, 6.5); ax.axis("off")
ax.set_title("Fig. 1 - The GPU-node reservation used in this experiment")
box(ax, 0.2, 5.0, 2.9, 1.2, "Website Pod\nno toleration", "#dbeafe", weight="bold")
box(ax, 0.2, 3.5, 2.9, 1.2, "ML training Pod\ntoleration hardware=gpu\n+ nodeSelector hardware=gpu", "#ede9fe", fs=8.8, weight="bold")
box(ax, 4.3, 4.2, 3.2, 1.3, "kube-scheduler\n1) drop nodes with untolerated\n    NoSchedule taints\n2) drop nodes failing nodeSelector", "#fef9c3", fs=8.8)
for y in (5.6, 4.1):
    ax.add_patch(FancyArrowPatch((3.1, y), (4.3, 4.85), arrowstyle="-|>", mutation_scale=15, lw=1.4))
cards = [(8.6, 5.0, "control plane", "taint control-plane:NoSchedule\n(built in)", "#f1f5f9"),
         (8.6, 3.1, "general node  (taints-lab-worker)", "no taint", "#dbeafe"),
         (8.6, 1.2, "GPU node  (taints-lab-worker2)", "taint hardware=gpu:NoSchedule\nlabel hardware=gpu", "#ede9fe")]
for x, y, name, txt, fc in cards:
    box(ax, x, y, 3.7, 1.35, f"{name}\n{txt}", fc, fs=8.8)
ax.add_patch(FancyArrowPatch((7.5, 4.85), (8.6, 3.75), arrowstyle="-|>", mutation_scale=15, lw=1.6, color="#2563eb"))
ax.add_patch(FancyArrowPatch((7.5, 4.6), (8.6, 1.9), arrowstyle="-|>", mutation_scale=15, lw=1.6, color="#7c3aed"))
ax.text(7.62, 3.95, "website", color="#2563eb", fontsize=9, weight="bold")
ax.text(7.25, 2.55, "ML job", color="#7c3aed", fontsize=9, weight="bold")
ax.text(4.0, 1.75, "A toleration only ALLOWS a Pod past a taint.\nThe nodeSelector SENDS it to the GPU node.\n"
        "Taint repels  +  selector attracts  =  dedicated node",
        ha="center", va="center", fontsize=9.5,
        bbox=dict(boxstyle="round,pad=0.5", fc="#f8fafc", ec="#cbd5e1"))
save(fig, "01_gpu_node_reservation_concept.png")

# ---------------------------------------------------------------- Fig 2 placement
fig, ax = plt.subplots(figsize=(12, 0.55 * len(summary) + 1.9))
left = pd.Series(0, index=summary.index)
for node in NODES:
    vals = summary[node]
    ax.barh(list(summary.index), vals, left=left, color=NCOLOR[node], label=NLABEL[node], edgecolor="white")
    for i, (v, l) in enumerate(zip(vals, left)):
        if v:
            ax.text(l + v / 2, i, str(v), ha="center", va="center", color="white", fontsize=9, weight="bold")
    left = left + vals
ax.invert_yaxis()
ax.set_xlabel("Number of Pods")
ax.set_xlim(0, left.max() + 0.5)
ax.tick_params(axis="y", labelsize=8.8)
ax.set_title("Fig. 2 - Where the scheduler placed each workload in every scenario (measured)")
ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.45, -0.06 - 0.6 / len(summary)), frameon=False)
save(fig, "02_pod_placement_by_scenario.png")

# ---------------------------------------------------------------- Fig 3 matrix
fig, ax = plt.subplots(figsize=(10.5, 0.5 * len(summary) + 1.7))
mat = summary[NODES].values
shade = (mat > 0).astype(float)
shade[:, 3] *= 2                      # Pending column: orange instead of green
ax.imshow(shade, cmap=ListedColormap(["#f8fafc", "#bbf7d0", "#fed7aa"]), vmin=0, vmax=2, aspect="auto")
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        v = mat[i, j]
        ax.text(j, i, str(v) if v else "-", ha="center", va="center", fontsize=10,
                color=("#b91c1c" if j == 3 else "#14532d") if v else "#94a3b8", weight="bold" if v else "normal")
ax.set_xticks(range(4), [NLABEL[n].replace(" (", "\n(") for n in NODES])
ax.set_yticks(range(len(summary)), summary.index, fontsize=8.8)
ax.xaxis.tick_top()
for s in ax.spines.values():
    s.set_visible(False)
ax.set_title("Fig. 3 - Pods per node for every snapshot (green = placed on that node, orange = Pending)", pad=34)
save(fig, "03_placement_matrix.png")

# ---------------------------------------------------------------- Fig 4 NoExecute
watched = float(timeline["watched_for_s"].iloc[0])
xmax = max(70, watched + 5)
fig, ax = plt.subplots(figsize=(11, 3.8))
labels, vals, colors, notes = [], [], [], []
for _, r in timeline.iterrows():
    labels.append(f"{r['pod']}\n{r['toleration']}")
    g = str(r["gone_after_s"])
    try:
        v = float(g); vals.append(v); colors.append("#dc2626")
        notes.append(f"evicted - marked after {float(r['marked_for_deletion_after_s']):.1f} s, gone after {v:.1f} s")
    except ValueError:
        vals.append(watched); colors.append("#16a34a")
        notes.append(f"still running after {watched:.0f} s (end of watch)")
ax.barh(labels, vals, color=colors, height=0.55)
for i, (v, t) in enumerate(zip(vals, notes)):
    inside = v > xmax * 0.6
    ax.text(v - 1 if inside else v + 1, i, t, va="center", ha="right" if inside else "left", fontsize=9,
            color="white" if inside else "black", weight="bold")
ax.axvline(30, color="#475569", ls="--", lw=1)
ax.text(30.6, 0.5, "tolerationSeconds = 30", fontsize=8.5, color="#475569", va="center")
ax.set_xlim(0, xmax)
ax.invert_yaxis()
ax.tick_params(axis="y", labelsize=8.5)
ax.set_xlabel("Seconds after  kubectl taint nodes taints-lab-worker2 gpu-fault=true:NoExecute")
ax.set_title("Fig. 4 - GPU fault (NoExecute): how long each running Pod survived (measured)")
save(fig, "04_noexecute_eviction_timeline.png")

# ---------------------------------------------------------------- Fig 5 events
keep = ["Scheduled", "FailedScheduling", "TaintManagerEviction", "Killing", "Pulling", "Pulled", "Started"]
# Count one event per (Pod, reason) seen during THIS run. The "count" field is not summed:
# Kubernetes aggregates identical events (same Pod name + message), so a Pod name reused
# from an earlier run (e.g. ml-job-no-grace) can carry that run's count as well.
run_start = steps["start_utc"].min()
ev = events[events["reason"].isin(keep) & (events["last_seen_utc"] >= run_start.replace("+00:00", "Z"))].copy()
cnt = ev.drop_duplicates(["reason", "object"]).groupby("reason").size().reindex(keep).dropna()
fig, ax = plt.subplots(figsize=(10, 4))
ax.bar(cnt.index, cnt.values,
       color=["#dc2626" if r in ("FailedScheduling", "TaintManagerEviction") else "#2563eb" for r in cnt.index])
for i, v in enumerate(cnt.values):
    ax.text(i, v + cnt.max() * 0.015, f"{int(v)}", ha="center", fontsize=9)
ax.set_ylabel("Pods with this event")
plt.setp(ax.get_xticklabels(), rotation=18, ha="right")
ax.set_title("Fig. 5 - Kubernetes events recorded in namespace gpu-lab (red = taint-related)")
save(fig, "05_event_counts.png")

# ---------------------------------------------------------------- Fig 6 timings
p = place[place["scheduled_after_s"] != ""].copy()
p["scheduled_after_s"] = p["scheduled_after_s"].astype(float)
p["ready_after_s"] = pd.to_numeric(p["ready_after_s"], errors="coerce")
first = p.drop_duplicates("pod")
order = list(dict.fromkeys(first["row"]))
fig, ax = plt.subplots(figsize=(12, 5))
for i, s in enumerate(order):
    d = first[first["row"] == s]
    ax.scatter([i - 0.12] * len(d), d["scheduled_after_s"], color="#7c3aed", s=28, zorder=3,
               label="scheduled after" if i == 0 else None)
    ax.scatter([i + 0.12] * len(d), d["ready_after_s"], color="#16a34a", s=28, marker="s", zorder=3,
               label="Ready after" if i == 0 else None)
ax.set_xticks(range(len(order)), [o.replace("  [", "\n[") for o in order], fontsize=7.6, rotation=30, ha="right")
ax.set_ylabel("Seconds after the Pod was created")
ax.set_yscale("symlog", linthresh=1)
ax.set_ylim(-0.08, 40)
ax.grid(axis="y", alpha=0.3)
ax.legend(frameon=False, loc="upper left")
ax.text(0.99, 0.97, "0 = within the same second (timestamps have 1 s resolution)\n"
        "S6b: the 15 s include the time the Pods waited in Pending",
        transform=ax.transAxes, ha="right", va="top", fontsize=8.5, color="#475569")
ax.set_title("Fig. 6 - Time from Pod creation to scheduling and to Ready (first snapshot of each Pod, 1 s resolution)")
save(fig, "06_scheduling_and_ready_times.png")

# ---------------------------------------------------------------- Fig 7 dashboard
def row(prefix, workload):
    return summary.loc[[r for r in summary.index if r.startswith(prefix) and r.endswith(f"[{workload}]")][0]]


s2, s3, s4 = row("S2", "website"), row("S3", "ml-training"), row("S4", "ml-training-typo")
s5w, s5m, s6 = row("S5", "website"), row("S5", "ml-training"), row("S6 ", "website")
g = timeline.set_index("pod")["gone_after_s"]
rec = steps.loc[steps["name"].str.startswith("S6"), "recovery_after_untaint_s"].iloc[0]
fig = plt.figure(figsize=(13.5, 5.7))
fig.suptitle("Fig. 7 - Summary dashboard: reserving a GPU node with taints and tolerations",
             weight="bold", fontsize=14, y=0.995)
cards = [
    ("Website, no toleration", f"{s2[GPU]} of {int(s2.sum())}", "Pods on the GPU node (S2)", "#2563eb"),
    ("ML job, toleration only", f"{s3[GEN]} + {s3[GPU]}", "general + GPU node (S3)", "#7c3aed"),
    ("ML job, typo", f"{s4[GPU]} of {int(s4.sum())}", "Pods on the GPU node (S4)", "#dc2626"),
    ("Dedicated GPU node", f"{s5m[GPU]}/{int(s5m.sum())} ML", f"on GPU; website {s5w[GEN]}/{int(s5w.sum())} on general", "#16a34a"),
    ("All nodes blocked", f"{s6[PEND]} Pending", f"recovered {float(rec):.1f} s after untaint", "#ea580c"),
    ("GPU fault, no grace", f"{float(g['ml-job-no-grace']):.1f} s", "until the Pod was gone", "#db2777"),
]
for i, (t, v, sub, colr) in enumerate(cards):
    a = fig.add_axes([0.012 + i * 0.165, 0.7, 0.155, 0.22]); a.axis("off")
    a.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.06",
                               transform=a.transAxes, fc="#f8fafc", ec=colr, lw=2))
    a.text(0.5, 0.8, t, ha="center", fontsize=9, color="#334155", weight="bold", transform=a.transAxes)
    a.text(0.5, 0.45, v, ha="center", fontsize=15, color=colr, weight="bold", transform=a.transAxes)
    a.text(0.5, 0.14, sub, ha="center", fontsize=7.6, color="#64748b", transform=a.transAxes)
tab = out.copy()
tab.columns = ["Snapshot", "Workload", "control plane", "general node", "GPU node", "Pending"]
a = fig.add_axes([0.02, 0.0, 0.96, 0.64]); a.axis("off")
t = a.table(cellText=tab.values, colLabels=tab.columns, loc="upper center", cellLoc="center",
            colWidths=[0.38, 0.17, 0.11, 0.11, 0.11, 0.1])
t.auto_set_font_size(False); t.set_fontsize(8.6); t.scale(1, 1.38)
for (r, c), cell in t.get_celld().items():
    cell.set_edgecolor("#e2e8f0")
    if r == 0:
        cell.set_facecolor("#1e293b"); cell.set_text_props(color="white", weight="bold")
    elif c in (0, 1):
        cell.set_text_props(ha="left")
    if r > 0 and c == 5 and tab.iloc[r - 1, 5]:
        cell.set_text_props(color="#b91c1c", weight="bold")
    if r > 0 and c == 4 and tab.iloc[r - 1, 4]:
        cell.set_text_props(color="#6d28d9", weight="bold")
save(fig, "07_summary_dashboard.png")
