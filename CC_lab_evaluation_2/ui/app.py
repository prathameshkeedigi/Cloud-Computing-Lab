"""
GPU Node Scheduling Dashboard  -  Problem 07: Pod Scheduling Using Taints and Tolerations
(Cloud Computing Lab Evaluation 2)

Scenario: taints-lab-worker2 is an expensive "GPU node" reserved for ML training jobs
with the taint  hardware=gpu:NoSchedule ; the company website must stay on the
general-purpose node taints-lab-worker.

The page shows the three nodes of the kind cluster "taints-lab", their taints, the Pods
placed on each node, Pending Pods and scheduling events, explains WHY a Pod may or may
not use a node, and runs every step with buttons.

Run (from the CC_lab_evaluation_2 folder):
    python -m streamlit run ui/app.py        ->  http://localhost:8501

Safety: every command is sent with  --context kind-taints-lab ; taints can only be
changed on the two worker nodes of this lab cluster, never on the control plane.
"""
import json
import subprocess
from pathlib import Path

import pandas as pd
import streamlit as st

CONTEXT = "kind-taints-lab"
NS = "gpu-lab"
CP, GEN, GPU = "taints-lab-control-plane", "taints-lab-worker", "taints-lab-worker2"
WORKERS = [GEN, GPU]
ROLE = {CP: "manager (control plane)", GEN: "🖥️ general-purpose node", GPU: "🎮 GPU node (reserved)"}
K8S = Path(__file__).resolve().parent.parent / "k8s"
LAB_TAINT_KEYS = ["hardware", "maintenance", "gpu-fault"]
DEFAULT_VALUE = {"hardware": "gpu", "maintenance": "true", "gpu-fault": "true"}

WORKLOADS = [
    ("🌐 Website (no toleration)", "02-website.yaml",
     "Ordinary NGINX website, 4 replicas. Must stay off the GPU node."),
    ("🧠 ML job — toleration only", "03-ml-training-toleration-only.yaml",
     "Allowed on the GPU node, but not sent there (spreads over both workers)."),
    ("⚠️ ML job — typo in toleration", "04-ml-training-wrong-toleration.yaml",
     "value 'gpus' instead of 'gpu' → does not match → kept off the GPU node."),
    ("🎯 ML job — toleration + nodeSelector", "05-ml-training-dedicated.yaml",
     "The correct setup: runs ONLY on the GPU node."),
    ("💥 GPU-fault test Pods", "06-gpu-fault-pods.yaml",
     "3 Pods on the GPU node for the NoExecute test (no grace / 30 s grace / monitor)."),
]
COLORS = {"website": "#2563eb", "ml-training": "#7c3aed", "ml-training-typo": "#dc2626",
          "gpu-fault-test": "#db2777"}
EFFECT_COLORS = {"NoSchedule": "#dc2626", "PreferNoSchedule": "#d97706", "NoExecute": "#7c3aed"}

st.set_page_config(page_title="GPU Node Scheduling Lab", page_icon="🎮", layout="wide")


# ------------------------------------------------------------------ kubectl helpers
def kubectl(*args, timeout=60):
    p = subprocess.run(["kubectl", "--context", CONTEXT, *args],
                       capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def kjson(*args):
    code, out = kubectl(*args, "-o", "json")
    return json.loads(out) if code == 0 else None


def run_action(label, *args):
    code, out = kubectl(*args)
    shown = " ".join(a.replace(str(K8S), "k8s").replace("\\", "/") for a in args)
    st.session_state.log.insert(0, (label, "kubectl " + shown, code, out.strip()))
    st.session_state.log = st.session_state.log[:20]


if "log" not in st.session_state:
    st.session_state.log = []


# ------------------------------------------------------------------ matching rules
def tolerates(tol, taint):
    """Kubernetes rule: does one toleration tolerate one taint?"""
    if tol.get("effect") and tol["effect"] != taint["effect"]:
        return False
    op = tol.get("operator", "Equal")
    if not tol.get("key"):
        return op == "Exists"
    if tol["key"] != taint["key"]:
        return False
    return True if op == "Exists" else tol.get("value", "") == taint.get("value", "")


def taint_str(t):
    return f"{t['key']}{'=' + t['value'] if t.get('value') else ''}:{t['effect']}"


def explain(pod, node):
    tols = pod["spec"].get("tolerations", [])
    reasons, verdict = [], "allowed"
    for taint in node["spec"].get("taints", []):
        if any(tolerates(t, taint) for t in tols):
            reasons.append(f"✅ taint `{taint_str(taint)}` is tolerated")
        elif taint["effect"] == "PreferNoSchedule":
            reasons.append(f"🟠 taint `{taint_str(taint)}` not tolerated — only a preference")
            verdict = "avoided" if verdict == "allowed" else verdict
        else:
            reasons.append(f"⛔ taint `{taint_str(taint)}` is NOT tolerated")
            verdict = "blocked"
    labels = node["metadata"].get("labels", {})
    for k, v in (pod["spec"].get("nodeSelector") or {}).items():
        if labels.get(k) == v:
            reasons.append(f"✅ nodeSelector `{k}={v}` matches")
        else:
            reasons.append(f"⛔ nodeSelector `{k}={v}` does not match this node")
            verdict = "blocked"
    if not reasons:
        reasons.append("✅ no taints and no nodeSelector — any Pod may run here")
    return verdict, reasons


def pod_chip(p):
    app = p["metadata"].get("labels", {}).get("app", "")
    phase = "terminating" if p["metadata"].get("deletionTimestamp") else p["status"].get("phase", "")
    return (f"<div style='border-left:5px solid {COLORS.get(app, '#94a3b8')};padding:1px 6px;margin:2px 0;"
            f"font-size:0.8em'>{p['metadata']['name']}<br><span style='color:#64748b'>{app} · {phase}</span></div>")


# ------------------------------------------------------------------ header
st.title("🎮 GPU Node Scheduling — Taints & Tolerations")
st.caption("Problem 07 · Cloud Computing Lab Evaluation 2 · kind cluster `taints-lab` "
           "(1 control plane + 2 workers) · namespace `gpu-lab`")
st.info("**Story:** `taints-lab-worker2` is an expensive **GPU node**. It is reserved for **ML training jobs** "
        "with the taint `hardware=gpu:NoSchedule`. The **website** has no toleration, so it must stay on the "
        "general-purpose node. *(kind nodes have no real GPU — the reservation is done by the taint and the "
        "label, exactly as on real hardware; the ML job is a simulated training loop.)*")

if kjson("get", "nodes") is None:
    st.error("Cannot reach the cluster `kind-taints-lab`. Start Docker Desktop and create it first:\n\n"
             "`kind create cluster --name taints-lab --config k8s/00-kind-cluster.yaml`")
    st.stop()


# ------------------------------------------------------------------ live view
@st.fragment(run_every=st.session_state.get("refresh", 3))
def cluster_view():
    nodes = {n["metadata"]["name"]: n for n in (kjson("get", "nodes") or {"items": []})["items"]}
    pod_list = (kjson("get", "pods", "-n", NS) or {"items": []})["items"]
    placed = [p for p in pod_list if p["spec"].get("nodeName")]
    pending = [p for p in pod_list if not p["spec"].get("nodeName")]
    gpu_taints = nodes.get(GPU, {}).get("spec", {}).get("taints", [])

    m = st.columns(4)
    m[0].metric("Nodes", len(nodes))
    m[1].metric("GPU node reserved?", "yes" if any(t["key"] == "hardware" for t in gpu_taints) else "no")
    m[2].metric("Pods placed", len(placed))
    m[3].metric("Pods Pending", len(pending))

    cols = st.columns(4)
    for col, name in zip(cols, [CP, GEN, GPU]):
        n = nodes.get(name, {})
        with col, st.container(border=True):
            st.markdown(f"**{ROLE[name]}**  \n`{name}`")
            taints = n.get("spec", {}).get("taints", [])
            if taints:
                st.markdown(" ".join(
                    f"<span style='background:{EFFECT_COLORS.get(t['effect'], '#475569')};color:white;"
                    f"padding:2px 6px;border-radius:6px;font-size:0.76em'>🚫 {taint_str(t)}</span>"
                    for t in taints), unsafe_allow_html=True)
            else:
                st.markdown("<span style='color:#16a34a'>no taints — open to every Pod</span>",
                            unsafe_allow_html=True)
            hw = n.get("metadata", {}).get("labels", {}).get("hardware")
            if hw:
                st.caption(f"🏷️ label hardware={hw}")
            here = sorted((p for p in placed if p["spec"]["nodeName"] == name), key=lambda p: p["metadata"]["name"])
            st.markdown(f"**Pods: {len(here)}**")
            st.markdown("".join(pod_chip(p) for p in here), unsafe_allow_html=True)
    with cols[3], st.container(border=True):
        st.markdown("**⏳ Pending**  \nno node accepted these Pods")
        st.markdown("".join(pod_chip(p) for p in pending) or "<span style='color:#64748b'>none</span>",
                    unsafe_allow_html=True)

    rows = []
    for e in (kjson("get", "events", "-n", NS) or {"items": []})["items"]:
        if e.get("reason") in ("Scheduled", "FailedScheduling", "TaintManagerEviction", "Killing", "Pulled"):
            rows.append({"last seen (UTC)": e.get("lastTimestamp") or e.get("eventTime") or "",
                         "type": e.get("type"), "reason": e.get("reason"),
                         "object": e["involvedObject"]["name"], "message": (e.get("message") or "")[:170]})
    with st.expander(f"📜 Scheduling events in `{NS}` ({len(rows)})", expanded=True):
        if rows:
            st.dataframe(pd.DataFrame(rows).sort_values("last seen (UTC)", ascending=False).head(25),
                         hide_index=True, width="stretch")
        else:
            st.caption("No events yet — deploy a workload.")


cluster_view()
st.divider()

tab_steps, tab_deploy, tab_taint, tab_why, tab_log = st.tabs(
    ["▶️ Guided steps", "🚀 Workloads", "🚫 Custom taint", "🔍 Why is this Pod here?", "🧾 Command log"])

with tab_steps:
    st.markdown("Click the steps in order; watch the node cards above after each click.")
    steps = [
        ("1 · Reserve the GPU node",
         "label `hardware=gpu` + taint `hardware=gpu:NoSchedule` on worker2",
         [("label", "label", "nodes", GPU, "hardware=gpu", "--overwrite"),
          ("taint", "taint", "nodes", GPU, "hardware=gpu:NoSchedule", "--overwrite")]),
        ("2 · General node into maintenance",
         "taint `maintenance=true:NoSchedule` on worker → Pods without tolerations become Pending",
         [("maintenance on", "taint", "nodes", GEN, "maintenance=true:NoSchedule", "--overwrite")]),
        ("3 · Maintenance finished",
         "remove the maintenance taint → Pending Pods are scheduled",
         [("maintenance off", "taint", "nodes", GEN, "maintenance-")]),
        ("4 · GPU fault (NoExecute)",
         "taint `gpu-fault=true:NoExecute` on worker2 → running Pods without a matching toleration are evicted",
         [("gpu fault", "taint", "nodes", GPU, "gpu-fault=true:NoExecute", "--overwrite")]),
        ("5 · GPU repaired", "remove the NoExecute taint",
         [("gpu repaired", "taint", "nodes", GPU, "gpu-fault-")]),
    ]
    for title, desc, actions in steps:
        c = st.columns([2.2, 5, 1.2])
        c[0].markdown(f"**{title}**")
        c[1].markdown(desc)
        if c[2].button("Run", key="step" + title, width="stretch"):
            for a in actions:
                run_action(a[0], *a[1:])
            st.rerun()
    if st.button("♻️ Reset lab (remove all lab taints and the label)"):
        for w in WORKERS:
            for k in LAB_TAINT_KEYS:
                kubectl("taint", "nodes", w, f"{k}-")
        run_action("reset", "label", "nodes", GPU, "hardware-")
        st.rerun()

with tab_deploy:
    for title, file, desc in WORKLOADS:
        r = st.columns([2.6, 3.4, 1, 1, 2.2])
        r[0].markdown(f"**{title}**  \n`k8s/{file}`")
        r[1].caption(desc)
        if r[2].button("Deploy", key="d" + file, width="stretch"):
            kubectl("apply", "-f", str(K8S / "01-namespace.yaml"))
            run_action("deploy " + title, "apply", "-f", str(K8S / file))
            st.rerun()
        if r[3].button("Delete", key="x" + file, width="stretch"):
            run_action("delete " + title, "delete", "-f", str(K8S / file), "--ignore-not-found", "--wait=false")
            st.rerun()
        with r[4].expander("YAML"):
            st.code((K8S / file).read_text(encoding="utf-8"), language="yaml")
    if st.button("🗑️ Delete every workload (namespace gpu-lab)"):
        run_action("delete namespace", "delete", "namespace", NS, "--wait=false")
        st.rerun()

with tab_taint:
    c = st.columns([2, 1.3, 1.3, 1.6])
    node = c[0].selectbox("Worker node", WORKERS, index=1, format_func=lambda n: f"{n}  ({ROLE[n]})")
    key = c[1].selectbox("Key", LAB_TAINT_KEYS)
    value = c[2].text_input("Value", DEFAULT_VALUE[key])
    effect = c[3].selectbox("Effect", ["NoSchedule", "PreferNoSchedule", "NoExecute"])
    b = st.columns(2)
    if b[0].button("➕ Add taint", type="primary", width="stretch"):
        run_action("add taint", "taint", "nodes", node, f"{key}={value}:{effect}", "--overwrite")
        st.rerun()
    if b[1].button("➖ Remove taint", width="stretch"):
        run_action("remove taint", "taint", "nodes", node, f"{key}:{effect}-")
        st.rerun()
    st.caption(f"Equivalent: `kubectl taint nodes {node} {key}={value}:{effect}`  ·  "
               f"remove: `kubectl taint nodes {node} {key}:{effect}-`")

with tab_why:
    pod_list = (kjson("get", "pods", "-n", NS) or {"items": []})["items"]
    if not pod_list:
        st.info("No Pods yet — deploy a workload first.")
    else:
        pick = st.selectbox("Pod", [p["metadata"]["name"] for p in pod_list])
        pod = next(p for p in pod_list if p["metadata"]["name"] == pick)
        tl = [t for t in pod["spec"].get("tolerations", []) if not t.get("key", "").startswith("node.kubernetes.io/")]
        st.markdown(f"**Placed on:** `{pod['spec'].get('nodeName') or 'Pending'}`  ·  "
                    f"**Tolerations:** {', '.join('`' + json.dumps(t) + '`' for t in tl) or 'none'}  ·  "
                    f"**nodeSelector:** `{pod['spec'].get('nodeSelector') or 'none'}`")
        nodes = {n["metadata"]["name"]: n for n in (kjson("get", "nodes") or {"items": []})["items"]}
        for col, name in zip(st.columns(3), [CP, GEN, GPU]):
            verdict, reasons = explain(pod, nodes[name])
            icon = {"allowed": "🟢 ALLOWED", "avoided": "🟠 ALLOWED, BUT AVOIDED", "blocked": "🔴 BLOCKED"}[verdict]
            with col, st.container(border=True):
                st.markdown(f"**{ROLE[name]}**  \n{icon}")
                for r_ in reasons:
                    st.markdown(f"- {r_}")
        st.caption("Kubernetes also adds two default tolerations to every Pod (`node.kubernetes.io/not-ready` "
                   "and `unreachable`, NoExecute, 300 s); they are hidden here.")

with tab_log:
    if not st.session_state.log:
        st.caption("Commands sent from this page appear here.")
    for label, cmd, code, out in st.session_state.log:
        st.markdown(f"{'✅' if code == 0 else '❌'} **{label}** — `{cmd}`")
        st.code(out or "(no output)")

with st.sidebar:
    st.header("Settings")
    st.session_state.refresh = st.slider("Auto-refresh every (s)", 2, 15, 3)
    st.markdown("**Taint effects**")
    for eff, colr in EFFECT_COLORS.items():
        st.markdown(f"<span style='background:{colr};color:white;padding:2px 6px;border-radius:6px'>{eff}</span>",
                    unsafe_allow_html=True)
    st.caption("NoSchedule: new Pods kept out · PreferNoSchedule: avoided if possible · "
               "NoExecute: running Pods evicted too")
    st.markdown("**Workloads**")
    for app, colr in COLORS.items():
        st.markdown(f"<span style='border-left:6px solid {colr};padding-left:6px'>{app}</span>",
                    unsafe_allow_html=True)
    st.caption(f"Cluster context: `{CONTEXT}`")
