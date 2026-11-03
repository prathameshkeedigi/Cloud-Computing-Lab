"""
Cloud Computing - Experiment 3
Building a Three-Node Kubernetes Cluster on Windows (kind) - Deploy, Scale, Self-Heal

Reads  : ../results/processed/*.csv
Writes : ../graphs/*.png

Usage  : python scripts/generate_graphs.py   (run from the CC_Experiment_3 folder)
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Patch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PRO = os.path.join(ROOT, "results", "processed")
OUT = os.path.join(ROOT, "graphs")
os.makedirs(OUT, exist_ok=True)

nodes = pd.read_csv(os.path.join(PRO, "cluster_nodes.csv"), keep_default_na=False)
sysp = pd.read_csv(os.path.join(PRO, "system_pods.csv"))
snaps = pd.read_csv(os.path.join(PRO, "web_pod_snapshots.csv"), keep_default_na=False)
checks = pd.read_csv(os.path.join(PRO, "replica_checkpoints.csv"))
events = pd.read_csv(os.path.join(PRO, "pod_startup_events.csv"))

NODES = ["kind-control-plane", "kind-worker", "kind-worker2"]
C_NODE = {"kind-control-plane": "#7C3AED", "kind-worker": "#2563EB", "kind-worker2": "#EA580C"}
GREY, DARK, GREEN, AMBER = "#6B7280", "#1F2937", "#16A34A", "#F59E0B"

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


def box(ax, x, y, w, h, text, fc, ec="black", tc="black", fs=10, bold=False, lw=1.0, r=0.12):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.02,rounding_size={r}",
                                facecolor=fc, edgecolor=ec, lw=lw))
    if text:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc,
                fontweight="bold" if bold else "normal")


def node_counts(snapshot):
    s = snaps[snaps.snapshot == snapshot]
    return [int((s.node == n).sum()) for n in NODES]


# ------------------------------------------------ 01 architecture ---------
fig, ax = plt.subplots(figsize=(16, 9.2))
ax.set_xlim(0, 16)
ax.set_ylim(0, 9.4)
ax.axis("off")

box(ax, 0.2, 7.9, 15.6, 1.1, "", "#F3F4F6", lw=1.4)
box(ax, 0.6, 8.1, 2.6, 0.7, "kubectl v1.36.1", "#E0E7FF", fs=10.5, bold=True)
box(ax, 3.5, 8.1, 2.6, 0.7, "kind v0.33.0", "#E0E7FF", fs=10.5, bold=True)
box(ax, 6.4, 8.1, 4.3, 0.7, "context kind-kind -> https://127.0.0.1:7295", "white", fs=10)
ax.text(15.5, 8.45, "Windows PC  (PowerShell)", fontsize=12.5, fontweight="bold", va="center", ha="right")

box(ax, 0.2, 0.2, 15.6, 7.45, "", "#EFF6FF", ec="#2563EB", lw=1.6)
ax.text(3.0, 7.3, "Docker Desktop 4.97.0 (Engine 29.9.2, WSL 2 VM)  -  each node is one "
        "container (kindest/node:v1.37.0)", fontsize=11.2, fontweight="bold", color="#1E3A8A", va="center")

cols = {"kind-control-plane": 0.5, "kind-worker": 5.7, "kind-worker2": 10.9}
info = nodes.set_index("node")
for n, x in cols.items():
    c = C_NODE[n]
    box(ax, x, 0.45, 4.6, 6.45, "", "white", ec=c, lw=2.2)
    role = "control plane (the 'brain')" if n == "kind-control-plane" else "worker (runs the apps)"
    ax.text(x + 2.3, 6.55, n, ha="center", fontsize=13, fontweight="bold", color=c)
    ax.text(x + 2.3, 6.15, f"{role}  -  node IP {info.loc[n, 'node_ip']}", ha="center", fontsize=9.5, color=DARK)
    ax.text(x + 2.3, 5.8, f"Pod IPs {info.loc[n, 'pod_subnet_seen']}   -   container {info.loc[n, 'docker_container_id']}",
            ha="center", fontsize=9, color=GREY)

cp = [("kube-apiserver", "#DDD6FE"), ("etcd", "#DDD6FE"), ("kube-scheduler", "#DDD6FE"),
      ("kube-controller-manager", "#DDD6FE"), ("coredns  x2", "#EDE9FE")]
y = 5.05
for name, fc in cp:
    box(ax, 0.8, y, 4.0, 0.52, name, fc, fs=10, bold=True)
    y -= 0.66
for x in cols.values():
    box(ax, x + 0.3, 1.25, 1.9, 0.52, "kube-proxy", "#E5E7EB", fs=9.5)
    box(ax, x + 2.4, 1.25, 1.9, 0.52, "kindnet (CNI)", "#E5E7EB", fs=9.5)
ax.text(cols["kind-control-plane"] + 2.3, 0.75, "no application Pods here", ha="center", fontsize=9.5,
        style="italic", color=GREY)

final = snaps[snaps.snapshot == "S4"]
for n in ["kind-worker", "kind-worker2"]:
    x = cols[n]
    pods = final[final.node == n].pod.str.replace("web-5fc9f4bf66-", "web-...", regex=False).tolist()
    yy = 4.85
    for p in pods:
        fresh = p.endswith("bkrvs")
        box(ax, x + 0.6, yy, 3.4, 0.55, p + ("   (replacement)" if fresh else ""),
            "#DCFCE7" if fresh else "#DBEAFE", ec=GREEN if fresh else "black", fs=10, bold=True,
            lw=1.8 if fresh else 1.0)
        yy -= 0.72
    ax.text(x + 2.3, yy + 0.25, "NGINX Pods of Deployment 'web'", ha="center", fontsize=9.5, color=GREY)

ax.annotate("", xy=(1.9, 6.95), xytext=(1.9, 8.08),
            arrowprops=dict(arrowstyle="-|>", color=DARK, lw=1.6))
ax.text(2.05, 7.3, "API calls", fontsize=9.5, color=DARK, va="center")
ax.set_title("Fig. 1 - The Three-Node kind Cluster Built in This Experiment (state after Step 6.4)",
             fontsize=15, pad=10)
save(fig, "01_cluster_architecture.png")

# --------------------------------------------- 02 system Pods per node ----
comp_order = ["kube-apiserver", "etcd", "kube-scheduler", "kube-controller-manager", "CoreDNS",
              "kube-proxy", "kindnet (CNI)"]
comp_col = {"kube-apiserver": "#7C3AED", "etcd": "#8B5CF6", "kube-scheduler": "#A78BFA",
            "kube-controller-manager": "#C4B5FD", "CoreDNS": "#DB2777",
            "kube-proxy": "#0D9488", "kindnet (CNI)": "#F59E0B"}
counts = sysp.groupby(["node", "component"]).size().unstack(fill_value=0).reindex(NODES).fillna(0)
fig, ax = plt.subplots(figsize=(12, 5.2))
left = [0] * len(NODES)
for comp in comp_order:
    vals = counts[comp].tolist() if comp in counts else [0] * len(NODES)
    ax.barh(NODES, vals, left=left, color=comp_col[comp], edgecolor="black", lw=0.8, label=comp)
    for i, v in enumerate(vals):
        if v:
            ax.text(left[i] + v / 2, i, str(int(v)), ha="center", va="center", color="white",
                    fontweight="bold", fontsize=11)
    left = [l + v for l, v in zip(left, vals)]
for i, tot in enumerate(left):
    ax.text(tot + 0.12, i, f"{int(tot)} Pods", va="center", fontweight="bold")
ax.invert_yaxis()
ax.set_xlim(0, 9.6)
ax.set_xlabel("Number of kube-system Pods (all 1/1 Running)")
ax.grid(axis="y", visible=False)
ax.legend(loc="lower right", ncol=2, fontsize=10, frameon=True)
ax.set_title("Fig. 2 - Kubernetes System Pods on Each Node (Step 4.5, 12 Pods in total)")
save(fig, "02_system_pods_per_node.png")

# ----------------------------------------------- 03 web Pod placement -----
stages = [("S2", "3 replicas\n(Step 5.3)"), ("S3", "6 replicas\n(Step 6.2)"),
          ("S4", "after deleting 1 Pod\n(Step 6.4)")]
fig, ax = plt.subplots(figsize=(11.5, 5.6))
w = 0.26
for j, n in enumerate(NODES):
    vals = [node_counts(s)[j] for s, _ in stages]
    xs = [i + (j - 1) * w for i in range(len(stages))]
    bars = ax.bar(xs, vals, w, color=C_NODE[n], edgecolor="black", label=n)
    for k, (b, v) in enumerate(zip(bars, vals)):
        if stages[k][0] == "S4" and n == "kind-worker":
            b.set_hatch("//")
        ax.text(b.get_x() + b.get_width() / 2, v + 0.06, str(v), ha="center", fontweight="bold")
ax.set_xticks(range(len(stages)))
ax.set_xticklabels([l for _, l in stages])
ax.set_ylim(0, 4)
ax.set_ylabel("NGINX Pods on the node")
ax.legend(loc="upper left")
ax.text(2 - w * 0, 3.55, "hatched: the replacement Pod's node is not shown in Step 6.4;\n"
        "Experiment 4 (screenshot 01) shows it on kind-worker", ha="center", fontsize=9, color=GREY)
ax.set_title("Fig. 3 - Where the Scheduler Placed the NGINX Pods")
save(fig, "03_web_pod_placement.png")

# ----------------------------------------- 04 desired vs running ---------
fig, ax = plt.subplots(figsize=(12, 5.4))
x = range(len(checks))
ax.bar([i - 0.2 for i in x], checks.desired, 0.4, color="#CBD5E1", edgecolor="black", label="Desired replicas")
ax.bar([i + 0.2 for i in x], checks.running, 0.4, color=GREEN, edgecolor="black", label="Running / Ready")
for i, r in checks.iterrows():
    ax.text(i - 0.2, r.desired + 0.08, str(r.desired), ha="center", fontweight="bold")
    ax.text(i + 0.2, r.running + 0.08, str(r.running), ha="center", fontweight="bold", color=GREEN)
ax.set_xticks(list(x))
ax.set_xticklabels([f"{r.command.replace('kubectl ', '')}\n{r.when}" for r in checks.itertuples()], fontsize=9.5)
ax.set_ylim(0, 7.2)
ax.set_ylabel("Pods")
ax.axvspan(-0.5, 1.5, color=AMBER, alpha=0.08)
ax.text(0.5, 6.6, "image still downloading\n(ContainerCreating)", ha="center", fontsize=9.5, color="#92400E")
ax.legend(loc="upper left", bbox_to_anchor=(0.32, 1.0))
ax.set_title("Fig. 4 - Desired vs Running Pods at Each Check (Kubernetes closes the gap)")
save(fig, "04_desired_vs_running.png")

# --------------------------------------- 05 Pod start-up time ------------
pull = float(events.loc[events.event == "Pulled", "seconds_after_start"].iloc[0])
start = float(events.loc[events.event == "Started", "seconds_after_start"].iloc[0])
fig, (a1, a2) = plt.subplots(2, 1, figsize=(12.5, 6.4), gridspec_kw={"height_ratios": [1, 1.2]})
a1.barh([0], [pull], 0.5, color="#EA580C", edgecolor="black", label=f"Image pull: {pull:.1f} s")
a1.barh([0], [start - pull], 0.5, left=[pull], color=GREEN, edgecolor="black",
        label=f"Create + start container: about {start - pull:.1f} s")
for t in (0, pull, start):
    a1.axvline(t, color=DARK, lw=1, ls=":")
a1.text(0.5, 0.36, "Scheduled + Pulling  18:45:05", fontsize=9.5)
a1.text(start - 0.5, 0.36, "Started  18:46:42", fontsize=9.5, ha="right")
a1.set_yticks([])
a1.set_xlim(0, 104)
a1.set_ylim(-1.0, 0.75)
a1.set_xlabel("Seconds after the Pod was scheduled")
a1.legend(loc="lower center", ncol=2, fontsize=10)
a1.set_title("(a) First Pod web-...-6bm4p: 97 s from scheduling to Running", fontsize=12)

labels = ["First Pods (image not on the node yet)", "3 Pods added by scaling (image already pulled)",
          "Replacement Pod after delete"]
vals = [start, 10, 14]
cols_ = ["#EA580C", "#2563EB", GREEN]
bars = a2.barh(labels, vals, color=cols_, edgecolor="black")
for b, h in zip(bars[1:], ["//", "//"]):
    b.set_hatch(h)
a2.text(start + 1, 0, f"{start:.0f} s (from describe pod)", va="center", fontweight="bold")
a2.text(11, 1, "Running when 10 s old  (<= 10 s)", va="center", fontweight="bold")
a2.text(15, 2, "Running when 14 s old  (<= 14 s)", va="center", fontweight="bold")
a2.invert_yaxis()
a2.set_xlim(0, 125)
a2.set_xlabel("Seconds until the Pod was Running  (hatched = upper limit read from the AGE column)")
a2.grid(axis="y", visible=False)
a2.set_title("(b) Start-up time with and without the image already on the node", fontsize=12)
fig.suptitle("Fig. 5 - Where the Pod Start-up Time Went: 99 % Was Downloading the nginx Image (63.9 MB)",
             fontsize=14, fontweight="bold")
fig.tight_layout()
save(fig, "05_pod_startup_time.png")

# ---------------------------------------- 06 Pod lifetimes ---------------
# Times are seconds before the last check (t = 0). AGE values >10 min are rounded down by kubectl.
life = [("web-...-6bm4p", "kind-worker", -1140, -14, "deleted in Step 6.3"),
        ("web-...-8d6dj", "kind-worker2", -1140, 0, ""),
        ("web-...-wtrbg", "kind-worker2", -1140, 0, ""),
        ("web-...-j7cfp", "kind-worker", -50, 0, "added by scale"),
        ("web-...-pxgnr", "kind-worker", -50, 0, "added by scale"),
        ("web-...-vflfn", "kind-worker2", -50, 0, "added by scale"),
        ("web-...-bkrvs", "kind-worker", -14, 0, "replacement (self-healing)")]
fig, axes = plt.subplots(1, 2, figsize=(15, 5.6), gridspec_kw={"width_ratios": [1.25, 1]}, sharey=True)
for ax, xmin, unit, title in [(axes[0], -1200, 60, "(a) Whole run (minutes)"),
                              (axes[1], -60, 1, "(b) Last 60 seconds (seconds)")]:
    for i, (p, n, s, e, note) in enumerate(life):
        s2, e2 = max(s, xmin), e
        ax.barh(i, (e2 - s2) / unit, left=s2 / unit, color=C_NODE[n], edgecolor="black",
                hatch="xx" if "deleted" in note else None, alpha=0.55 if "deleted" in note else 1)
        if unit == 1 and note:
            ax.text(e2 / unit + 0.6 if e2 < 0 else 0.6, i, note, va="center", fontsize=9)
    ax.set_xlim(xmin / unit, (6 if unit == 1 else 0.1))
    ax.axvline(-50 / unit, color=DARK, ls="--", lw=1)
    ax.axvline(-14 / unit, color="#DC2626", ls="--", lw=1)
    ax.set_title(title, fontsize=12)
    ax.grid(axis="y", visible=False)
axes[1].set_xlim(-60, 25)
axes[0].set_yticks(range(len(life)))
axes[0].set_yticklabels([l[0] for l in life])
axes[0].set_ylim(6.6, -1.1)
axes[1].text(-49, -0.75, "scale to 6", fontsize=9.5)
axes[1].text(-13, -0.75, "delete 6bm4p", fontsize=9.5, color="#DC2626")
axes[0].set_xlabel("Minutes before the final check")
axes[1].set_xlabel("Seconds before the final check")
axes[0].legend(handles=[Patch(color=C_NODE[n], label=n) for n in NODES[1:]], loc="lower left")
fig.suptitle("Fig. 6 - Pod Lifetimes: Scaling Adds Pods, Self-Healing Replaces a Deleted One",
             fontsize=15, fontweight="bold")
fig.tight_layout()
save(fig, "06_pod_lifetimes_self_healing.png")

# ---------------------------------------------- 07 dashboard -------------
fig = plt.figure(figsize=(14, 7.6))
gs = fig.add_gridspec(2, 4, height_ratios=[0.75, 1.25], hspace=0.38, wspace=0.3)
kpis = [("Nodes Ready", "3 / 3", "1 control plane + 2 workers", "#7C3AED"),
        ("System Pods Running", f"{len(sysp)} / {len(sysp)}", "kube-system namespace", "#0D9488"),
        ("NGINX replicas", "3 -> 6", "kubectl scale", "#2563EB"),
        ("Self-healing", "6 / 6", "replacement Running at 14 s", GREEN)]
for i, (title, big, small, c) in enumerate(kpis):
    ax = fig.add_subplot(gs[0, i])
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor="#F9FAFB", edgecolor=c, lw=2.5))
    ax.text(0.5, 0.77, title.upper(), ha="center", fontsize=10, color="#374151", transform=ax.transAxes)
    ax.text(0.5, 0.43, big, ha="center", fontsize=21, fontweight="bold", color=c, transform=ax.transAxes)
    ax.text(0.5, 0.14, small, ha="center", fontsize=10, color="#374151", transform=ax.transAxes)
ax = fig.add_subplot(gs[1, :])
ax.axis("off")
rows = []
for s, lbl in [("S1", "Step 5.3 - 20 s after create"), ("S2", "Step 5.3 - about 15 min later"),
               ("S3", "Step 6.2 - after scale to 6"), ("S4", "Step 6.4 - after deleting one Pod")]:
    d = snaps[snaps.snapshot == s]
    c = node_counts(s)
    rows.append([lbl, str(len(d)), str(int((d.status == "Running").sum())), str(c[1]), str(c[2]), str(c[0])])
tbl = ax.table(cellText=rows, colLabels=["Check", "Pods", "Running", "kind-worker", "kind-worker2",
                                         "control-plane"], loc="center", cellLoc="center",
               colWidths=[0.34, 0.1, 0.1, 0.14, 0.14, 0.14])
tbl.auto_set_font_size(False)
tbl.set_fontsize(11.5)
tbl.scale(1, 2.2)
for (r, c), cell in tbl.get_celld().items():
    if r == 0:
        cell.set_facecolor("#1F2937")
        cell.set_text_props(color="white", fontweight="bold")
    elif r == 4:
        cell.set_facecolor("#F0FDF4")
ax.set_title("NGINX Deployment 'web' at each check", fontweight="bold")
fig.suptitle("Fig. 7 - Experiment 3 Summary: kind Cluster, Deployment, Scaling and Self-Healing",
             fontsize=15, fontweight="bold")
save(fig, "07_summary_dashboard.png")

print("All figures written to", OUT)
