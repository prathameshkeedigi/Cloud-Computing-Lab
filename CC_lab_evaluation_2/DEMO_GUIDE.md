# Demo Guide — GPU Node Scheduling Dashboard

**For:** anyone presenting Problem 07 who is new to Kubernetes.
**What you need running:** Docker Desktop, the cluster `taints-lab`, and the dashboard (see [README §19](README.md#19-how-to-run-this-project-prerequisites-and-full-procedure)).

```powershell
cd CC_lab_evaluation_2
kubectl get nodes                      # 3 nodes, all Ready
python -m streamlit run ui/app.py      # opens http://localhost:8501
```

---

## 1. The idea in one minute

- A **cluster** is a group of computers. Ours has **3**:
  - a **manager** (control plane) — it decides where apps run; it never runs apps itself,
  - a **general computer** (`taints-lab-worker`) — ordinary work,
  - a **GPU computer** (`taints-lab-worker2`) — expensive, meant only for AI / ML jobs.
- An app runs as one or more **Pods** (copies). Kubernetes's **scheduler** chooses a computer for each Pod.
- **The problem:** by default the scheduler puts Pods *anywhere*, even the website on the expensive GPU computer.
- **The fix:**

| Word | Simple meaning | Where it lives |
|---|---|---|
| **Taint** | a **"No entry" sign** on a computer | on the node |
| **Toleration** | a **pass** that lets a Pod ignore that sign | in the Pod's YAML |
| **nodeSelector** | an **address**: "run only on computers labelled `hardware=gpu`" | in the Pod's YAML |

> **Sign + pass + address = a computer reserved for one kind of app.**

(Our "GPU computer" has no real GPU — it is a laptop container. It is reserved exactly the way a real GPU node is: with a taint and a label. The ML job is a simulated training loop.)

---

## 2. What you see on the screen

### Top: the live cluster (refreshes every 3 s — you just watch)

```
┌──────────────┐ ┌────────────────┐ ┌────────────────┐ ┌──────────────┐
│ MANAGER      │ │ GENERAL NODE   │ │ GPU NODE       │ │ ⏳ PENDING    │
│ never runs   │ │ ordinary       │ │ expensive,     │ │ Pods that no │
│ apps         │ │ computer       │ │ for ML only    │ │ computer     │
│              │ │                │ │                │ │ accepted     │
└──────────────┘ └────────────────┘ └────────────────┘ └──────────────┘
```

| On a card | Meaning |
|---|---|
| 🔴 red badge `…:NoSchedule` | a hard "No entry" sign for **new** Pods |
| 🟠 amber badge `…:PreferNoSchedule` | a soft sign: "avoid if possible" |
| 🟣 purple badge `…:NoExecute` | the strongest sign: also **throws out** Pods already running |
| 🏷️ `label hardware=gpu` | the "address" the ML job looks for |
| blue line | one **website** Pod |
| purple line | one **ML job** Pod |

Below the cards: **📜 events table** — Kubernetes's own messages, e.g. `Scheduled` (placed), `FailedScheduling` (no computer accepted it), `TaintManagerEviction` (thrown out).

### Bottom: five tabs

| Tab | What it changes | In simple words |
|---|---|---|
| **🚀 Workloads** | the **apps** | start / stop an app |
| **▶️ Guided steps** | the **computers** | put up / take down a sign |
| 🚫 Custom taint | the computers | make any sign yourself (not needed for the demo) |
| **🔍 Why is this Pod here?** | nothing (read-only) | explains, for one Pod, why each computer is allowed or blocked |
| 🧾 Command log | nothing (read-only) | the real `kubectl` command behind every button you pressed |

### The 5 apps in **🚀 Workloads**

| Button | What it is | Pass (toleration)? | Address (nodeSelector)? | Where it should go |
|---|---|:-:|:-:|---|
| 🌐 **Website** | company website, 4 copies | ❌ | ❌ | general computer only |
| 🧠 **ML job — toleration only** | AI job, 4 copies | ✅ | ❌ | both computers (allowed, not sent) |
| ⚠️ **ML job — typo in toleration** | AI job whose pass says `gpus` instead of `gpu` | ❌ (wrong) | ❌ | general computer only |
| 🎯 **ML job — toleration + nodeSelector** | AI job, 3 copies, the correct setup | ✅ | ✅ | GPU computer only |
| 💥 **GPU-fault test Pods** | 3 small Pods for the "GPU breaks" test | special | ✅ | GPU computer |

### The buttons in **▶️ Guided steps**

| Step | What it does | Real-life meaning |
|---|---|---|
| **1 · Reserve the GPU node** | label `hardware=gpu` + sign `hardware=gpu:NoSchedule` on the GPU computer | "This computer is only for AI jobs" |
| **2 · General node into maintenance** | sign `maintenance=true:NoSchedule` on the general computer | "This computer is being repaired" |
| **3 · Maintenance finished** | removes that sign | "Repair done" |
| **4 · GPU fault (NoExecute)** | sign `gpu-fault=true:NoExecute` on the GPU computer | "GPU broke — everyone out!" |
| **5 · GPU repaired** | removes the fault sign | "GPU fixed" |
| **♻️ Reset lab** | removes **all** lab signs and the label | back to the start |

---

## 3. Before the demo (1 minute)

1. Docker Desktop shows **Engine running**; `kubectl get nodes` shows 3 × **Ready**.
2. Dashboard open at http://localhost:8501.
3. **🚀 Workloads** → scroll down → **🗑️ Delete every workload**.
4. **▶️ Guided steps** → **♻️ Reset lab**.
5. Check: the **general** and **GPU** cards say *"no taints — open to every Pod"*, and no card contains Pods.
   The **manager** card always shows its built-in red sign `node-role.kubernetes.io/control-plane:NoSchedule` — that is normal.

> Tip: after every **Delete**, wait ~5 seconds until the Pods disappear from the cards before the next **Deploy**.

---

## 4. The demo — six acts (about 6 minutes)

Each step: **Click → Watch → Say.**

### 🎬 Act 1 — Without a sign, Pods go anywhere

| | |
|---|---|
| **Click** | 🚀 Workloads → 🌐 Website → **Deploy** |
| **Watch** | 4 blue Pods, about 2 on the general computer and 2 on the GPU computer. None on the manager. |
| **Say** | "With no taint, Kubernetes puts the website anywhere — even on the expensive GPU node. The manager gets nothing because it has a built-in taint." |

### 🎬 Act 2 — Reserve the GPU computer

| | |
|---|---|
| **Click** | ▶️ Guided steps → **1 · Reserve the GPU node** → Run |
| **Watch** | red badge `hardware=gpu:NoSchedule` and label `hardware=gpu` appear on the GPU card. **The blue Pods already there stay.** |
| **Say** | "NoSchedule only blocks **new** Pods. Pods that are already running are not removed." |
| **Click** | 🚀 Workloads → Website → **Delete**, wait 5 s, → **Deploy** |
| **Watch** | all **4 blue Pods on the general computer**, 0 on the GPU computer. |
| **Say** | "The website has no toleration, so the GPU node is closed to it." |

### 🎬 Act 3 — A pass is not an address

| | |
|---|---|
| **Click** | 🚀 Workloads → 🧠 ML job — toleration only → **Deploy** |
| **Watch** | purple Pods on **both** computers (about 2 + 2). |
| **Say** | "The toleration only **allows** the job onto the GPU node — it does not **send** it there. Both nodes are allowed, so Kubernetes spreads the copies." |
| **Click** | same row → **Delete** |
| **Click** | ⚠️ ML job — typo in toleration → **Deploy** *(optional)* |
| **Watch** | all on the general computer. |
| **Say** | "One wrong letter — `gpus` instead of `gpu` — and the pass is useless. Key, value and effect must match exactly." Then **Delete** it. |

### 🎬 Act 4 — The correct setup: a dedicated GPU node ⭐ (main result)

| | |
|---|---|
| **Click** | 🚀 Workloads → 🎯 ML job — toleration + nodeSelector → **Deploy** |
| **Watch** | **all 3 purple Pods on the GPU computer**; the 4 blue website Pods stay on the general computer. |
| **Say** | "Pass plus address. The taint keeps the website out; the nodeSelector keeps the ML job in. The GPU node is now dedicated to ML." |
| **Click** | 🔍 Why is this Pod here? → choose a `website-…` Pod |
| **Watch** | GPU node: 🔴 **BLOCKED** — "taint `hardware=gpu:NoSchedule` is NOT tolerated". |
| **Click** | choose an `ml-training-…` Pod |
| **Watch** | GPU node: 🟢 **ALLOWED**; general node: 🔴 **BLOCKED** — "nodeSelector `hardware=gpu` does not match". |
| **Say** | "This tab applies the same matching rules as the Kubernetes scheduler." |

### 🎬 Act 5 — No computer allowed → Pending (optional)

| | |
|---|---|
| **Click** | ▶️ Guided steps → **2 · General node into maintenance** → Run |
| **Click** | 🚀 Workloads → Website → **Delete**, wait 5 s, → **Deploy** |
| **Watch** | the blue Pods appear in **⏳ Pending**; the events table shows **FailedScheduling** — "0/3 nodes are available: 3 node(s) had untolerated taint(s)". |
| **Say** | "Every node now has a sign the website does not tolerate, so it waits." |
| **Click** | ▶️ Guided steps → **3 · Maintenance finished** → Run |
| **Watch** | within ~5 s the Pods move from Pending to the general computer. |
| **Say** | "As soon as a node is allowed again, Kubernetes places the waiting Pods by itself." |

### 🎬 Act 6 — The GPU breaks: NoExecute (optional)

| | |
|---|---|
| **First** | 🚀 Workloads → 🎯 ML job — toleration + nodeSelector → **Delete**, wait 5 s. *(Otherwise the fault also throws out those ML Pods; they would then wait in Pending, because their address points only to the broken GPU node. Correct behaviour, but confusing on stage.)* |
| **Click** | 🚀 Workloads → 💥 GPU-fault test Pods → **Deploy** (3 Pods appear on the GPU computer) |
| **Click** | ▶️ Guided steps → **4 · GPU fault (NoExecute)** → Run |
| **Watch** | `ml-job-no-grace` disappears **at once** · `ml-job-grace-30s` disappears after **~30 s** · `gpu-monitor` **stays**. Events: `TaintManagerEviction`. |
| **Say** | "NoExecute also removes Pods that are already running. One job had no pass — out at once. One had a 30-second pass — time to save its work. The monitor has a permanent pass because it must report the fault." |
| **Click** | ▶️ Guided steps → **5 · GPU repaired** |

### End

🚀 Workloads → **🗑️ Delete every workload**, then ▶️ Guided steps → **♻️ Reset lab**.

---

## 5. If the evaluator asks…

| Question | Short answer |
|---|---|
| Where is the taint, where is the toleration? | Taint on the **node** (`kubectl taint nodes …`); toleration in the **Pod's YAML** (`tolerations:` in `k8s/03…` and `k8s/05…`). |
| Why didn't the toleration put the job on the GPU node? | A toleration only **permits**. To **send** a Pod you need a nodeSelector (or node affinity) — Act 3 vs Act 4. |
| Difference between NoSchedule and NoExecute? | NoSchedule blocks new Pods only (Act 2: old Pods stayed). NoExecute also evicts running Pods (Act 6). |
| What is PreferNoSchedule? | A soft sign: avoided when possible, used when nothing else fits. Measured in the README §10 (4/0, then 4+2). |
| Why does the manager never run Pods? | It has a built-in taint `node-role.kubernetes.io/control-plane:NoSchedule`. |
| What does `tolerationSeconds: 30` do? | The Pod may stay 30 s after a matching NoExecute taint appears, then it is evicted (measured 31.0 s). |
| Is there a real GPU? | No — kind nodes are containers. The node is reserved the same way a real GPU node is (taint + label); the ML job is simulated. |
| What do the buttons actually run? | Open the 🧾 Command log tab — every button is a normal `kubectl` command, e.g. `kubectl taint nodes taints-lab-worker2 hardware=gpu:NoSchedule`. |

---

## 6. If something goes wrong during the demo

| What you see | What to do |
|---|---|
| Red box "Cannot reach the cluster" | Docker Desktop is closed — start it, wait for "Engine running", refresh the page |
| Pods stay in Pending when they should not | a sign is still on a node → ▶️ **Reset lab** |
| A Deploy seems to do nothing | the same app is already running — **Delete** it first, wait 5 s, then **Deploy** |
| Cards look stale | wait 3 s (auto-refresh) or press **R** in the browser |
| Old Pods from an earlier act are still there | 🚀 **Delete every workload**, wait ~10 s |

> **One sentence to remember:** *A taint is a "No entry" sign on a computer, a toleration is a pass on an app, and a nodeSelector is its address — sign + pass + address = a computer reserved for one kind of app.*
