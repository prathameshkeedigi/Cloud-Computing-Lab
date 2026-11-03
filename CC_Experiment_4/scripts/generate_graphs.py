"""
Cloud Computing - Experiment 4
Resource Allocation, Scheduling and Load Balancing in a Three-Node Kubernetes Cluster

Reads  : ../results/processed/*.csv
Writes : ../graphs/*.png
         ../results/processed/requested_resources_per_node.csv (calculated from the YAML + placement)

Usage  : python scripts/generate_graphs.py   (run from the CC_Experiment_4 folder)
"""

import os
import textwrap
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Patch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PRO = os.path.join(ROOT, "results", "processed")
OUT = os.path.join(ROOT, "graphs")
os.makedirs(OUT, exist_ok=True)

pods = pd.read_csv(os.path.join(PRO, "pod_snapshots.csv"), keep_default_na=False)
spec = pd.read_csv(os.path.join(PRO, "resource_spec.csv")).iloc[0]
svc = pd.read_csv(os.path.join(PRO, "service_endpoints.csv")).set_index("item").value
status = pd.read_csv(os.path.join(PRO, "step_status.csv"), keep_default_na=False)
obs = pd.read_csv(os.path.join(PRO, "observation_table.csv"))

NODES = ["kind-control-plane", "kind-worker", "kind-worker2"]
C_NODE = {"kind-control-plane": "#7C3AED", "kind-worker": "#2563EB", "kind-worker2": "#EA580C"}
C_FIRST, C_ADDED, C_WEB = "#2563EB", "#16A34A", "#9CA3AF"
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


def box(ax, x, y, w, h, text, fc, ec="black", tc="black", fs=10, bold=False, lw=1.0, r=0.12, ls="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.02,rounding_size={r}",
                                facecolor=fc, edgecolor=ec, lw=lw, linestyle=ls))
    if text:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc,
                fontweight="bold" if bold else "normal")


def count(snapshot, deployment, node):
    d = pods[(pods.snapshot == snapshot) & (pods.deployment == deployment)]
    return int((d.node == node).sum())


rd6 = {n: count("R6", "resource-demo", n) for n in NODES}
rd12 = {n: count("R12", "resource-demo", n) for n in NODES}
web = {n: count("R12", "web", n) for n in NODES}

# requested / limited resources per node, calculated from the Deployment spec and the measured placement
rows = []
for reps, placed in [(6, rd6), (12, rd12)]:
    for n in NODES:
        k = placed[n]
        rows.append(dict(replicas=reps, node=n, resource_demo_pods=k,
                         cpu_request_m=k * spec.cpu_request_m, cpu_limit_m=k * spec.cpu_limit_m,
                         memory_request_Mi=k * spec.memory_request_Mi, memory_limit_Mi=k * spec.memory_limit_Mi))
req = pd.DataFrame(rows)
req.to_csv(os.path.join(PRO, "requested_resources_per_node.csv"), index=False)

# ------------------------------------------- 01 Service architecture -----
fig, ax = plt.subplots(figsize=(16, 9.6))
ax.set_xlim(0, 16)
ax.set_ylim(0, 9.6)
ax.axis("off")

box(ax, 0.2, 5.6, 3.3, 1.3, "test-curl Pod\n(curlimages/curl)\ninside the cluster", "#DCFCE7", ec=GREEN, fs=10, bold=True, lw=1.8)
box(ax, 0.2, 1.4, 3.3, 1.5, "Windows browser\nhttp://localhost:30080\n(kubectl port-forward)", "#FEF3C7", ec=AMBER, fs=10, bold=True, lw=1.8)

box(ax, 4.3, 3.3, 3.4, 3.6, "", "#EFF6FF", ec="#2563EB", lw=2.2)
ax.text(6.0, 6.45, "Service  nginx-service", ha="center", fontsize=12, fontweight="bold", color="#1E3A8A")
for i, t in enumerate([f"type {svc['Type']}", f"ClusterIP {svc['ClusterIP']}:80",
                       f"NodePort {svc['Ports']}", f"selector {svc['Selector']}",
                       f"{svc['Endpoints total']} endpoints (Pod IP:80)"]):
    ax.text(6.0, 5.85 - i * 0.48, t, ha="center", fontsize=10.2, fontweight="bold" if i == 4 else "normal")

ax.annotate("", xy=(4.28, 5.6), xytext=(3.52, 6.2), arrowprops=dict(arrowstyle="-|>", lw=2, color=GREEN))
ax.text(3.0, 7.15, "http://nginx-service:80\n(DNS name -> ClusterIP)", fontsize=9.5, color="#166534")

# nodes
box(ax, 8.4, 7.9, 7.4, 1.4, "", "white", ec=C_NODE["kind-control-plane"], lw=2.2)
ax.text(12.1, 8.85, "kind-control-plane  (172.18.0.4)", ha="center", fontsize=11.5, fontweight="bold",
        color=C_NODE["kind-control-plane"])
ax.text(12.1, 8.3, "0 application Pods  -  port 30080 is still open here (kube-proxy runs on every node)",
        ha="center", fontsize=9.5, color=GREY)

r12 = pods[pods.snapshot == "R12"]
for n, y0, ip in [("kind-worker", 4.1, "172.18.0.2"), ("kind-worker2", 0.2, "172.18.0.3")]:
    box(ax, 8.4, y0, 7.4, 3.5, "", "white", ec=C_NODE[n], lw=2.2)
    ax.text(12.1, y0 + 3.15, f"{n}  ({ip})", ha="center", fontsize=11.5, fontweight="bold", color=C_NODE[n])
    d = r12[(r12.deployment == "resource-demo") & (r12.node == n)].sort_values("batch", ascending=False)
    for k, p in enumerate(d.itertuples()):
        cx, cy = 8.65 + (k % 3) * 2.42, y0 + 2.2 - (k // 3) * 0.72
        label = p.pod.replace("resource-demo-54dfb4bddc-", "rd-") + ("\n" + p.ip if p.ip else "\n(starting)")
        box(ax, cx, cy, 2.25, 0.6, label, "#DBEAFE" if p.batch == "first 6" else "#DCFCE7", fs=8.6)
    ax.text(8.7, y0 + 0.62, f"+ {web[n]} 'web' Pods from Experiment 3 (label app=web -> NOT behind this Service)",
            fontsize=9, color=GREY)
    ax.annotate("", xy=(8.38, y0 + 1.8), xytext=(7.72, 5.1 if n == "kind-worker" else 4.1),
                arrowprops=dict(arrowstyle="-|>", lw=2, color="#2563EB"))
ax.text(4.35, 2.85, "kube-proxy on every node spreads\nnew connections over the endpoints",
        fontsize=9.3, color="#1E3A8A", ha="left")

ax.annotate("", xy=(8.38, 1.2), xytext=(3.52, 2.0),
            arrowprops=dict(arrowstyle="-|>", lw=1.8, color=AMBER, ls="--"))
ax.text(3.7, 0.35, "port-forward connects to ONE Pod chosen by kubectl\n(bypasses the Service's load balancing)",
        fontsize=9.3, color="#92400E")
ax.legend(handles=[Patch(facecolor="#DBEAFE", edgecolor="black", label="first 6 replicas"),
                   Patch(facecolor="#DCFCE7", edgecolor="black", label="added when scaled to 12")],
          loc="upper left", bbox_to_anchor=(0.01, 0.5), fontsize=10)
ax.set_title("Fig. 1 - How Traffic Reached the resource-demo Pods (12 replicas, Steps 6-9)", fontsize=15, pad=8)
save(fig, "01_service_architecture.png")

# ----------------------------------------- 02 distribution 6 vs 12 ------
fig, ax = plt.subplots(figsize=(12, 5.8))
groups = [("6 replicas (Step 4)", rd6), ("12 replicas (Step 6)", rd12)]
w = 0.26
for gi, (glabel, placed) in enumerate(groups):
    for j, n in enumerate(NODES):
        x = gi + (j - 1) * w
        ax.bar(x, placed[n], w, color=C_NODE[n], edgecolor="black", label=n if gi == 0 else None)
        ax.bar(x, web[n], w, bottom=placed[n], color=C_WEB, edgecolor="black", hatch="..",
               label="'web' Pods (Experiment 3)" if gi == 0 and j == 1 else None)
        if placed[n]:
            ax.text(x, placed[n] / 2, str(placed[n]), ha="center", va="center", color="white",
                    fontweight="bold", fontsize=12)
        ax.text(x, placed[n] + web[n] + 0.15, f"total {placed[n] + web[n]}", ha="center", fontsize=9.5)
ax.set_xticks([0, 1])
ax.set_xticklabels([g for g, _ in groups])
ax.set_ylim(0, 11)
ax.set_ylabel("Pods on the node")
ax.legend(loc="upper left", ncol=2)
ax.set_title("Fig. 2 - resource-demo Pods per Node: an Even 3 + 3, then 6 + 6 Split")
save(fig, "02_pod_distribution_6_vs_12.png")

# ----------------------------------------------- 03 placement map -------
fig, ax = plt.subplots(figsize=(14, 7.4))
ax.set_xlim(0, 14)
ax.set_ylim(0, 9.4)
ax.axis("off")
for j, n in enumerate(NODES):
    x0 = 0.3 + j * 4.6
    box(ax, x0, 0.3, 4.2, 8.3, "", "white", ec=C_NODE[n], lw=2.2)
    ax.text(x0 + 2.1, 8.15, n, ha="center", fontsize=13, fontweight="bold", color=C_NODE[n])
    d = r12[r12.node == n].copy()
    d["order"] = d.batch.map({"Experiment 3": 0, "first 6": 1, "added by scale": 2})
    d = d.sort_values(["order", "pod"])
    if d.empty:
        ax.text(x0 + 2.1, 4.4, "no application Pods\n(control-plane node\nis kept for the cluster)",
                ha="center", fontsize=11, color=GREY, style="italic")
    for k, p in enumerate(d.itertuples()):
        fc = {"Experiment 3": "#E5E7EB", "first 6": "#DBEAFE", "added by scale": "#DCFCE7"}[p.batch]
        name = p.pod.replace("resource-demo-54dfb4bddc-", "resource-demo-...").replace("web-5fc9f4bf66-", "web-...")
        box(ax, x0 + 0.25, 7.35 - k * 0.6, 3.7, 0.5, f"{name}   {p.ip or '(starting)'}", fc, fs=9)
ax.legend(handles=[Patch(facecolor="#E5E7EB", edgecolor="black", label="'web' Pods from Experiment 3 (BestEffort)"),
                   Patch(facecolor="#DBEAFE", edgecolor="black", label="resource-demo: first 6 (Step 3)"),
                   Patch(facecolor="#DCFCE7", edgecolor="black", label="resource-demo: added by scaling to 12 (Step 6)")],
          loc="lower center", bbox_to_anchor=(0.5, -0.08), ncol=3, fontsize=10)
ax.set_title("Fig. 3 - Every Pod and Its Node after Scaling to 12 (kubectl get pods -o wide)", fontsize=15)
save(fig, "03_pod_placement_map.png")

# ------------------------------------- 04 requested resources ----------
fig, axes = plt.subplots(1, 2, figsize=(15, 5.8))
for ax, (rq, lm, unit, title) in zip(axes, [("cpu_request_m", "cpu_limit_m", "millicores (1000m = 1 core)", "(a) CPU"),
                                            ("memory_request_Mi", "memory_limit_Mi", "MiB", "(b) Memory")]):
    w = 0.2
    series = [(6, rq, "request, 6 replicas", "#93C5FD", None), (6, lm, "limit, 6 replicas", "#DBEAFE", "//"),
              (12, rq, "request, 12 replicas", "#2563EB", None), (12, lm, "limit, 12 replicas", "#BFDBFE", "//")]
    for s, (reps, col, lab, fc, hatch) in enumerate(series):
        vals = req[req.replicas == reps].set_index("node").reindex(NODES)[col]
        xs = [i + (s - 1.5) * w for i in range(len(NODES))]
        bars = ax.bar(xs, vals, w, color=fc, edgecolor="black", hatch=hatch, label=lab)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + max(req[lm]) * 0.015, f"{int(v)}", ha="center", fontsize=8.8)
    ax.set_xticks(range(len(NODES)))
    ax.set_xticklabels(NODES)
    ax.set_ylabel(unit)
    ax.set_title(title, fontsize=12.5)
axes[0].legend(loc="upper left", fontsize=9.5)
fig.suptitle(f"Fig. 4 - Resources Reserved (requests) and Capped (limits) on Each Node\n"
             f"per Pod: request {spec.cpu_request_m}m CPU / {spec.memory_request_Mi}Mi, "
             f"limit {spec.cpu_limit_m}m / {spec.memory_limit_Mi}Mi  x  Pods placed on the node",
             fontsize=14, fontweight="bold")
fig.text(0.5, -0.03, "Calculated from deployment.yaml and the measured Pod placement. The nodes' allocatable "
         "capacity was not captured (kubectl describe nodes was not run), so no percentage is shown.",
         ha="center", fontsize=9.5, color=GREY)
fig.tight_layout()
save(fig, "04_requested_resources_per_node.png")

# ----------------------------------------- 05 start-up at first check ---
r6 = pods[(pods.snapshot == "R6") & (pods.deployment == "resource-demo")]
new = r12[r12.batch == "added by scale"]
cases = [("Exp 3: first 3 'web' Pods\n(image NOT on nodes) - 20 s", 0, 3),
         ("Exp 4: 6 replicas applied\n(image on nodes) - 6 s", int((r6.status == "Running").sum()), len(r6)),
         ("Exp 4: 6 Pods added by scale\n(image on nodes) - 5 s", int((new.status == "Running").sum()), len(new))]
fig, ax = plt.subplots(figsize=(12, 5.2))
for i, (lab, run, tot) in enumerate(cases):
    ax.barh(i, run / tot * 100, color=GREEN, edgecolor="black", label="Running" if i == 0 else None)
    ax.barh(i, (tot - run) / tot * 100, left=run / tot * 100, color=AMBER, edgecolor="black",
            label="ContainerCreating" if i == 0 else None)
    ax.text(101, i, f"{run} / {tot} Running", va="center", fontweight="bold")
ax.set_yticks(range(len(cases)))
ax.set_yticklabels([c[0] for c in cases])
ax.invert_yaxis()
ax.set_xlim(0, 122)
ax.set_xlabel("% of the Pods at the first kubectl get pods after the command")
ax.grid(axis="y", visible=False)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2)
ax.set_title("Fig. 5 - How Many Pods Were Already Running at the First Check")
save(fig, "05_pods_running_at_first_check.png")

# ---------------------------------------- 06 coverage --------------------
cmap = {"Captured": "#16A34A", "Partial": "#F59E0B", "Done differently": "#F59E0B",
        "Not captured": "#E5E7EB", "Not done": "#E5E7EB"}
fig, ax = plt.subplots(figsize=(13, 6.6))
ax.axis("off")
cells = [[r.step, r.task, r.status, r.note] for r in status.itertuples()]
tbl = ax.table(cellText=cells, colLabels=["Step", "Task", "Status", "Note"], loc="center", cellLoc="left",
               colWidths=[0.06, 0.36, 0.15, 0.43])
tbl.auto_set_font_size(False)
tbl.set_fontsize(10.5)
tbl.scale(1, 1.9)
for (r, c), cell in tbl.get_celld().items():
    if r == 0:
        cell.set_facecolor("#1F2937")
        cell.set_text_props(color="white", fontweight="bold")
    elif c == 2:
        txt = cell.get_text().get_text()
        cell.set_facecolor(cmap.get(txt, "white"))
        if txt == "Captured":
            cell.set_text_props(color="white", fontweight="bold")
ax.set_title("Fig. 6 - Which Manual Steps Produced Results (from the screenshots)", fontsize=15, fontweight="bold")
save(fig, "06_experiment_coverage.png")

# ---------------------------------------------- 07 dashboard -------------
fig = plt.figure(figsize=(14, 8.2))
gs = fig.add_gridspec(2, 4, height_ratios=[0.7, 1.4], hspace=0.3, wspace=0.3)
tot12 = req[req.replicas == 12]
kpis = [("Nodes Ready", "3 / 3", "v1.37.0, containerd 2.3.4", "#7C3AED"),
        ("Spread at 12 replicas", f"{rd12['kind-worker']} | {rd12['kind-worker2']}", "kind-worker | kind-worker2", "#2563EB"),
        ("CPU requested", f"{tot12.cpu_request_m.sum() / 1000:.1f} cores", f"memory {int(tot12.memory_request_Mi.sum())} Mi", "#EA580C"),
        ("Service endpoints", str(svc["Endpoints total"]), "NodePort 30080 -> port 80", GREEN)]
for i, (title, big, small, c) in enumerate(kpis):
    ax = fig.add_subplot(gs[0, i])
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor="#F9FAFB", edgecolor=c, lw=2.5))
    ax.text(0.5, 0.77, title.upper(), ha="center", fontsize=10, color="#374151", transform=ax.transAxes)
    ax.text(0.5, 0.43, big, ha="center", fontsize=20, fontweight="bold", color=c, transform=ax.transAxes)
    ax.text(0.5, 0.14, small, ha="center", fontsize=10, color="#374151", transform=ax.transAxes)
ax = fig.add_subplot(gs[1, :])
ax.axis("off")
cells = [[r.experiment, textwrap.fill(r.result, 100)] for r in obs.itertuples()]
tbl = ax.table(cellText=cells, colLabels=["Observation (manual table)", "Result"], loc="center",
               cellLoc="left", colWidths=[0.25, 0.75])
tbl.auto_set_font_size(False)
tbl.set_fontsize(10.2)
tbl.scale(1, 2.5)
for (r, c), cell in tbl.get_celld().items():
    if r > 0 and "\n" in cells[r - 1][1]:
        cell.set_height(cell.get_height() * 1.6)
for (r, c), cell in tbl.get_celld().items():
    if r == 0:
        cell.set_facecolor("#1F2937")
        cell.set_text_props(color="white", fontweight="bold")
    elif "Not captured" in cell.get_text().get_text():
        cell.set_facecolor("#F3F4F6")
fig.suptitle("Fig. 7 - Experiment 4 Summary: Requests, Scheduling and Service Load Balancing",
             fontsize=15, fontweight="bold")
save(fig, "07_summary_dashboard.png")

print(req.to_string(index=False))
print("All figures written to", OUT)
