"""
Problem 07 - Pod Scheduling Using Taints and Tolerations  (GPU-node scenario)

Story: taints-lab-worker2 is an expensive GPU node. It is reserved for ML training
jobs with a taint; the company website must stay on the general-purpose node
taints-lab-worker.

Runs every scenario (S1-S8) on the kind cluster "taints-lab" and records the evidence.

Usage (from the CC_lab_evaluation_2 folder, after the cluster exists):
    python scripts/run_experiment.py

Writes:
    results/raw/NN_<step>.txt   terminal-style transcript of every command and its output
    results/*.csv               nodes, placement, events, step timings, NoExecute timeline

Safety:
    * every kubectl call uses  --context kind-taints-lab , so no other cluster is touched
    * the script stops if the cluster's node names are not the expected three
    * only the two workers are tainted / labelled, and everything is removed in step 12
"""
import csv
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CONTEXT = "kind-taints-lab"
NS = "gpu-lab"
CP = "taints-lab-control-plane"
GEN = "taints-lab-worker"      # general-purpose node
GPU = "taints-lab-worker2"     # "GPU node"
GPU_TAINT = "hardware=gpu:NoSchedule"
ROOT = Path(__file__).resolve().parent.parent
K8S = ROOT / "k8s"
RAW = ROOT / "results" / "raw"
RES = ROOT / "results"
RAW.mkdir(parents=True, exist_ok=True)

placement_rows, step_rows, all_events = [], [], {}
raw_file = None
_step_start = None


def now():
    return datetime.now(timezone.utc)


def log(text=""):
    print(text)
    if raw_file:
        raw_file.write(text + "\n")
        raw_file.flush()


def kubectl(*args, show=True, check=True, timeout=180):
    cmd = ["kubectl", "--context", CONTEXT, *args]
    shown = "kubectl " + " ".join(a.replace(str(ROOT) + "\\", "").replace("\\", "/") for a in args)
    if show:
        log(f"PS> {shown}")
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = (p.stdout or "") + (p.stderr or "")
    if show:
        log(out.rstrip())
        log()
    if check and p.returncode != 0:
        raise RuntimeError(f"command failed: {shown}\n{out}")
    return p.stdout


def kjson(*args):
    return json.loads(kubectl(*args, "-o", "json", show=False))


def f(name):
    return str(K8S / name)


def begin_step(num, name, title):
    global raw_file, _step_start
    if raw_file:
        raw_file.close()
    raw_file = open(RAW / f"{num:02d}_{name}.txt", "w", encoding="utf-8")
    _step_start = now()
    log("=" * 78)
    log(f"Step {num:02d} - {title}")
    log(f"Started (UTC): {_step_start.isoformat(timespec='seconds')}")
    log("=" * 78)
    log()
    step_rows.append({"step": num, "name": name, "title": title,
                      "start_utc": _step_start.isoformat(timespec="seconds")})


def end_step(**extra):
    end = now()
    step_rows[-1]["end_utc"] = end.isoformat(timespec="seconds")
    step_rows[-1]["duration_s"] = round((end - _step_start).total_seconds(), 1)
    step_rows[-1].update(extra)


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def pods(selector=None):
    args = ["get", "pods", "-n", NS]
    if selector:
        args += ["-l", selector]
    return [p for p in kjson(*args)["items"]]


def live(selector):
    return [p for p in pods(selector) if not p["metadata"].get("deletionTimestamp")]


def is_ready(p):
    return any(c["type"] == "Ready" and c["status"] == "True" for c in p["status"].get("conditions", []))


def wait_for(selector, want_scheduled, want_ready, timeout=240):
    t0 = time.time()
    while time.time() - t0 < timeout:
        items = live(selector)
        sched = sum(1 for p in items if p["spec"].get("nodeName"))
        ready = sum(1 for p in items if is_ready(p))
        if len(items) >= max(want_scheduled, want_ready, 1) and sched >= want_scheduled and ready >= want_ready:
            return round(time.time() - t0, 1)
        time.sleep(2)
    log(f"(warning) timeout waiting for {selector}")
    return None


def toleration_summary(spec):
    own = [t for t in spec.get("tolerations", []) if not t.get("key", "").startswith("node.kubernetes.io/")]
    if not own:
        return "none"
    out = []
    for t in own:
        s = f"{t.get('key', '*')}{'=' + t['value'] if 'value' in t else ''}:{t.get('effect', '*')}"
        if "tolerationSeconds" in t:
            s += f" ({t['tolerationSeconds']}s)"
        out.append(s)
    return "; ".join(out)


def snapshot(label, selector):
    for p in live(selector):
        st = p["status"]
        conds = {c["type"]: c for c in st.get("conditions", [])}
        created = parse_ts(p["metadata"]["creationTimestamp"])
        sc = conds.get("PodScheduled", {})
        sched_t = parse_ts(sc.get("lastTransitionTime")) if sc.get("status") == "True" else None
        rc = conds.get("Ready", {})
        ready_t = parse_ts(rc.get("lastTransitionTime")) if rc.get("status") == "True" else None
        placement_rows.append({
            "snapshot": label,
            "workload": p["metadata"]["labels"].get("app", ""),
            "pod": p["metadata"]["name"],
            "node": p["spec"].get("nodeName") or "Pending (no node)",
            "phase": st.get("phase"),
            "ready": "yes" if ready_t else "no",
            "tolerations": toleration_summary(p["spec"]),
            "node_selector": ";".join(f"{k}={v}" for k, v in (p["spec"].get("nodeSelector") or {}).items()) or "none",
            "scheduled_after_s": round((sched_t - created).total_seconds(), 1) if sched_t else "",
            "ready_after_s": round((ready_t - created).total_seconds(), 1) if ready_t else "",
        })


def collect_events():
    for e in kjson("get", "events", "-n", NS)["items"]:
        all_events[e["metadata"]["uid"]] = {
            "first_seen_utc": e.get("firstTimestamp") or e.get("eventTime") or e["metadata"]["creationTimestamp"],
            "last_seen_utc": e.get("lastTimestamp") or e.get("eventTime") or e["metadata"]["creationTimestamp"],
            "type": e.get("type"),
            "reason": e.get("reason"),
            "object": f"{e['involvedObject']['kind']}/{e['involvedObject']['name']}",
            "count": e.get("count") or 1,
            "source": (e.get("source") or {}).get("component") or e.get("reportingComponent", ""),
            "message": (e.get("message") or "").replace("\n", " "),
        }


def show_taints():
    kubectl("get", "nodes", "-L", "hardware", "-o",
            "custom-columns=NODE:.metadata.name,TAINT-KEYS:.spec.taints[*].key,"
            "VALUES:.spec.taints[*].value,EFFECTS:.spec.taints[*].effect,HARDWARE-LABEL:.metadata.labels.hardware")


def show_pods(selector=None):
    args = ["get", "pods", "-n", NS, "-o", "wide"]
    if selector:
        args += ["-l", selector]
    kubectl(*args)


def describe_section(pod_name, sections=("Node:", "Node-Selectors:", "Tolerations:", "Events:")):
    out = kubectl("describe", "pod", "-n", NS, pod_name, show=False)
    log(f"PS> kubectl describe pod -n {NS} {pod_name}    (lines: {', '.join(s.rstrip(':') for s in sections)})")
    keep = False
    for line in out.splitlines():
        if line.startswith(sections):
            keep = True
        elif line and not line.startswith(" ") and keep:
            keep = False
        if keep:
            log(line)
    log()


def delete_all_and_wait():
    kubectl("delete", "deployment,pod", "-n", NS, "--all", "--wait=true", timeout=240)
    t0 = time.time()
    while pods() and time.time() - t0 < 120:
        time.sleep(2)


def write_csv(path, rows):
    if not rows:
        return
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def main():
    global raw_file
    # ------------------------------------------------------------- safety check
    ctxs = subprocess.run(["kubectl", "config", "get-contexts", "-o", "name"],
                          capture_output=True, text=True).stdout.split()
    if CONTEXT not in ctxs:
        sys.exit(f"Context {CONTEXT} not found. Create the cluster first (Implementation.md, Phase 1).")
    names = sorted(n["metadata"]["name"] for n in kjson("get", "nodes")["items"])
    if names != sorted([CP, GEN, GPU]):
        sys.exit(f"Unexpected nodes {names}; stopping so that nothing else is changed.")

    # ------------------------------------------------------------- 02
    begin_step(2, "cluster_and_builtin_taint", "Cluster check and the control plane's built-in taint")
    kubectl("version")
    kubectl("get", "nodes", "-o", "wide")
    show_taints()
    out = kubectl("describe", "node", CP, show=False)
    log(f"PS> kubectl describe node {CP} | Select-String Taints,Unschedulable")
    log("\n".join(l for l in out.splitlines() if l.startswith(("Taints", "Unschedulable"))))
    log()
    rows = []
    for n in kjson("get", "nodes")["items"]:
        lab = n["metadata"]["labels"]
        rows.append({
            "node": n["metadata"]["name"],
            "role": "control-plane" if "node-role.kubernetes.io/control-plane" in lab else "worker",
            "role_in_scenario": {CP: "manager", GEN: "general-purpose node", GPU: "GPU node (reserved)"}[n["metadata"]["name"]],
            "taints_at_start": "; ".join(f"{t['key']}{'=' + t['value'] if t.get('value') else ''}:{t['effect']}"
                                         for t in n["spec"].get("taints", [])) or "none",
            "cpu": n["status"]["capacity"]["cpu"],
            "memory": n["status"]["capacity"]["memory"],
            "max_pods": n["status"]["capacity"]["pods"],
            "kubelet": n["status"]["nodeInfo"]["kubeletVersion"],
            "runtime": n["status"]["nodeInfo"]["containerRuntimeVersion"],
            "os_image": n["status"]["nodeInfo"]["osImage"],
            "kernel": n["status"]["nodeInfo"]["kernelVersion"],
            "internal_ip": next(a["address"] for a in n["status"]["addresses"] if a["type"] == "InternalIP"),
        })
    write_csv(RES / "nodes.csv", rows)
    end_step()

    # ------------------------------------------------------------- 03 S1
    begin_step(3, "S1_baseline_no_reservation", "S1 Baseline - GPU node not reserved yet; website spreads everywhere")
    kubectl("apply", "-f", f("01-namespace.yaml"))
    kubectl("apply", "-f", f("02-website.yaml"))
    wait_for("app=website", 4, 4, timeout=300)
    show_pods()
    snapshot("S1 Baseline: no taint yet", "app=website")
    collect_events()
    end_step()

    # ------------------------------------------------------------- 04 reserve GPU node
    begin_step(4, "reserve_gpu_node", "Reserve the GPU node: label + NoSchedule taint (running Pods are NOT evicted)")
    kubectl("label", "nodes", GPU, "hardware=gpu", "--overwrite")
    kubectl("taint", "nodes", GPU, GPU_TAINT)
    show_taints()
    log("Waiting 15 s to show that NoSchedule does not remove Pods that are already running ...")
    time.sleep(15)
    show_pods()
    snapshot("S1b 15 s after GPU taint: old Pods stay", "app=website")
    delete_all_and_wait()
    end_step()

    # ------------------------------------------------------------- 05 S2
    begin_step(5, "S2_website_no_toleration", "S2 Website WITHOUT toleration - kept off the GPU node")
    kubectl("apply", "-f", f("02-website.yaml"))
    wait_for("app=website", 4, 4)
    show_pods()
    snapshot("S2 Website, no toleration", "app=website")
    describe_section(live("app=website")[0]["metadata"]["name"])
    collect_events()
    delete_all_and_wait()
    end_step()

    # ------------------------------------------------------------- 06 S3
    begin_step(6, "S3_ml_toleration_only", "S3 ML job WITH toleration only - allowed on the GPU node, not forced")
    kubectl("apply", "-f", f("03-ml-training-toleration-only.yaml"))
    wait_for("app=ml-training", 4, 4, timeout=300)
    show_pods()
    snapshot("S3 ML job, toleration only", "app=ml-training")
    describe_section(live("app=ml-training")[0]["metadata"]["name"])
    collect_events()
    delete_all_and_wait()
    end_step()

    # ------------------------------------------------------------- 07 S4
    begin_step(7, "S4_ml_wrong_toleration", "S4 ML job with a TYPO in its toleration (gpus) - still blocked")
    kubectl("apply", "-f", f("04-ml-training-wrong-toleration.yaml"))
    wait_for("app=ml-training-typo", 4, 4)
    show_pods()
    snapshot("S4 ML job, wrong toleration", "app=ml-training-typo")
    describe_section(live("app=ml-training-typo")[0]["metadata"]["name"], ("Node:", "Tolerations:"))
    collect_events()
    delete_all_and_wait()
    end_step()

    # ------------------------------------------------------------- 08 S5
    begin_step(8, "S5_dedicated_gpu_node", "S5 Dedicated GPU node - ML (toleration + nodeSelector) next to the website")
    kubectl("apply", "-f", f("02-website.yaml"))
    kubectl("apply", "-f", f("05-ml-training-dedicated.yaml"))
    wait_for("app in (website,ml-training)", 7, 7)
    show_pods()
    snapshot("S5 Dedicated: website + ML job", "app in (website,ml-training)")
    ml = live("app=ml-training")[0]["metadata"]["name"]
    describe_section(ml, ("Node:", "Node-Selectors:", "Tolerations:"))
    time.sleep(6)
    kubectl("logs", "-n", NS, ml, "--tail=3")
    collect_events()
    delete_all_and_wait()
    end_step()

    # ------------------------------------------------------------- 09 S6
    begin_step(9, "S6_general_node_maintenance_pending",
               "S6 General node under maintenance (hard taint) - website has nowhere to go -> Pending")
    kubectl("taint", "nodes", GEN, "maintenance=true:NoSchedule")
    show_taints()
    kubectl("apply", "-f", f("02-website.yaml"))
    time.sleep(15)
    show_pods()
    snapshot("S6 Maintenance + GPU hard taint: Pending", "app=website")
    describe_section(live("app=website")[0]["metadata"]["name"], ("Events:",))
    collect_events()
    log("--- maintenance finished: remove the taint (the trailing '-' removes it) ---")
    kubectl("taint", "nodes", GEN, "maintenance=true:NoSchedule-")
    rec = wait_for("app=website", 4, 4)
    log(f"All Pending Pods were scheduled and Ready {rec} s after the taint was removed")
    log()
    show_pods()
    snapshot("S6b Maintenance over: Pods recover", "app=website")
    collect_events()
    delete_all_and_wait()
    end_step(recovery_after_untaint_s=rec)

    # ------------------------------------------------------------- 10 S7
    begin_step(10, "S7_soft_reservation_prefer_no_schedule",
               "S7 Soft reservation - GPU taint changed to PreferNoSchedule")
    kubectl("taint", "nodes", GPU, f"{GPU_TAINT}-")
    kubectl("taint", "nodes", GPU, "hardware=gpu:PreferNoSchedule")
    show_taints()
    kubectl("apply", "-f", f("02-website.yaml"))
    wait_for("app=website", 4, 4)
    show_pods()
    snapshot("S7 Soft: GPU node avoided", "app=website")
    log("--- general node goes into maintenance; the website is scaled from 4 to 6 ---")
    kubectl("taint", "nodes", GEN, "maintenance=true:NoSchedule")
    kubectl("scale", "deployment/website", "-n", NS, "--replicas=6")
    wait_for("app=website", 6, 6)
    show_pods()
    snapshot("S7b Soft: no other node, GPU node used", "app=website")
    collect_events()
    delete_all_and_wait()
    kubectl("taint", "nodes", GEN, "maintenance=true:NoSchedule-")
    kubectl("taint", "nodes", GPU, "hardware=gpu:PreferNoSchedule-")
    kubectl("taint", "nodes", GPU, GPU_TAINT)
    show_taints()
    end_step()

    # ------------------------------------------------------------- 11 S8
    begin_step(11, "S8_gpu_fault_noexecute", "S8 GPU fault - NoExecute evicts running Pods")
    kubectl("apply", "-f", f("06-gpu-fault-pods.yaml"))
    wait_for("app=gpu-fault-test", 3, 3)
    show_pods()
    snapshot("S8 Before the GPU fault", "app=gpu-fault-test")
    t_taint = now()
    kubectl("taint", "nodes", GPU, "gpu-fault=true:NoExecute")
    log(f"Taint applied at {t_taint.isoformat(timespec='seconds')} UTC. Checking the Pods every 1 s for up to 60 s ...")
    gone, marked = {}, {}
    names_ = ("ml-job-no-grace", "ml-job-grace-30s", "gpu-monitor")
    for _ in range(70):
        cur = {p["metadata"]["name"]: p for p in pods("app=gpu-fault-test")}
        t = round((now() - t_taint).total_seconds(), 1)
        for n in names_:
            p = cur.get(n)
            if p and p["metadata"].get("deletionTimestamp") and n not in marked:
                marked[n] = t
            if p is None and n not in gone:
                gone[n] = t
                marked.setdefault(n, t)
        if "ml-job-no-grace" in gone and "ml-job-grace-30s" in gone and t >= 60:
            break
        time.sleep(1)
    watch_end = round((now() - t_taint).total_seconds(), 1)
    show_pods()
    collect_events()
    timeline = []
    tols = {"ml-job-no-grace": "only hardware=gpu:NoSchedule (no fault toleration)",
            "ml-job-grace-30s": "gpu-fault=true:NoExecute, tolerationSeconds 30",
            "gpu-monitor": "gpu-fault:NoExecute (Exists), no time limit"}
    for n in names_:
        timeline.append({"pod": n, "toleration": tols[n],
                         "marked_for_deletion_after_s": marked.get(n, "not evicted"),
                         "gone_after_s": gone.get(n, "still running"),
                         "watched_for_s": watch_end})
        log(f"{n:17s} {tols[n]:52s} marked {marked.get(n, '-')} s | gone {gone.get(n, 'still running')}")
    write_csv(RES / "noexecute_timeline.csv", timeline)
    log()
    kubectl("taint", "nodes", GPU, "gpu-fault=true:NoExecute-")
    delete_all_and_wait()
    end_step()

    # ------------------------------------------------------------- 12 cleanup
    begin_step(12, "cleanup", "Clean-up - remove the lab taints, the label and the namespace")
    kubectl("taint", "nodes", GPU, f"{GPU_TAINT}-")
    kubectl("label", "nodes", GPU, "hardware-")
    collect_events()
    kubectl("delete", "namespace", NS, "--wait=true", timeout=300)
    show_taints()
    end_step()

    write_csv(RES / "placement.csv", placement_rows)
    write_csv(RES / "steps.csv", step_rows)
    write_csv(RES / "events.csv", sorted(all_events.values(), key=lambda r: (r["first_seen_utc"], r["object"])))
    raw_file.close()
    raw_file = None
    print("\nDone. Tables written to results/*.csv, transcripts to results/raw/")


if __name__ == "__main__":
    main()
