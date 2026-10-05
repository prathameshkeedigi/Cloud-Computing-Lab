"""
Runs the five workload levels (W1-W5 = 1, 2, 4, 8, 16 concurrent users) with Locust
in headless mode, while sampling `docker stats` for all four microservice containers.

Outputs (in results/):
    raw/W<n>_<users>u_stats.csv    Locust statistics for each workload
    raw/docker_stats_samples.csv   every docker stats sample, tagged with its workload
    observation_table.csv          one row per workload (the table the manual asks for)
    container_usage.csv            average CPU % and memory per container per workload

Usage (from the CC_lab_evaluation folder, with `docker compose up -d` running):
    python loadtest/run_workloads.py                 # 60 s per workload (default)
    python loadtest/run_workloads.py --duration 30
"""

import argparse
import csv
import json
import os
import subprocess
import sys
import threading
import time

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")
RAW = os.path.join(RESULTS, "raw")
LOCUSTFILE = os.path.join(HERE, "locustfile.py")

WORKLOADS = [("W1", 1), ("W2", 2), ("W3", 4), ("W4", 8), ("W5", 16)]
CONTAINERS = ["book-service", "member-service", "borrow-service", "notification-service"]


def to_mib(text):
    """'45.2MiB' -> 45.2 ; '1.1GiB' -> 1126.4 ; '800KiB' -> 0.78"""
    text = text.strip()
    for unit, factor in [("GiB", 1024), ("MiB", 1), ("KiB", 1 / 1024), ("GB", 953.67),
                         ("MB", 0.9537), ("kB", 0.000954), ("B", 1 / 1048576)]:
        if text.endswith(unit):
            return float(text[: -len(unit)]) * factor
    return float("nan")


class StatsSampler(threading.Thread):
    """Calls `docker stats --no-stream` in a loop and stores one row per container."""

    def __init__(self):
        super().__init__(daemon=True)
        self.label = None
        self.rows = []
        self.running = True

    def run(self):
        while self.running:
            label = self.label
            out = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "{{json .}}", *CONTAINERS],
                capture_output=True, text=True).stdout
            if label is None:
                continue
            ts = time.strftime("%H:%M:%S")
            for line in out.splitlines():
                try:
                    s = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self.rows.append({
                    "time": ts, "workload": label, "container": s["Name"],
                    "cpu_pct": float(s["CPUPerc"].rstrip("%")),
                    "mem_mib": to_mib(s["MemUsage"].split("/")[0]),
                    "mem_pct": float(s["MemPerc"].rstrip("%")),
                })


def run_locust(label, users, duration, host):
    prefix = os.path.join(RAW, f"{label}_{users}u")
    cmd = [sys.executable, "-m", "locust", "-f", LOCUSTFILE, "--headless",
           "-u", str(users), "-r", str(users), "-t", f"{duration}s",
           "--host", host, "--csv", prefix, "--only-summary", "--stop-timeout", "5"]
    subprocess.run(cmd, check=False)
    stats = pd.read_csv(prefix + "_stats.csv")
    agg = stats[stats["Name"] == "Aggregated"].iloc[0]
    return {
        "workload": label,
        "concurrency": users,
        "total_requests": int(agg["Request Count"]),
        "failed_requests": int(agg["Failure Count"]),
        "avg_response_ms": round(float(agg["Average Response Time"]), 2),
        "median_response_ms": round(float(agg["Median Response Time"]), 2),
        "p95_response_ms": round(float(agg["95%"]), 2),
        "max_response_ms": round(float(agg["Max Response Time"]), 2),
        "throughput_rps": round(float(agg["Requests/s"]), 2),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=int, default=60, help="seconds per workload level")
    ap.add_argument("--host", default="http://127.0.0.1:8003", help="Borrow Service URL")
    ap.add_argument("--cooldown", type=int, default=10, help="idle seconds between levels")
    args = ap.parse_args()
    os.makedirs(RAW, exist_ok=True)

    sampler = StatsSampler()
    sampler.start()
    results = []
    for label, users in WORKLOADS:
        print(f"\n=== {label}: {users} concurrent user(s), {args.duration} s ===", flush=True)
        sampler.label = label
        results.append(run_locust(label, users, args.duration, args.host))
        sampler.label = None
        print(results[-1], flush=True)
        if label != WORKLOADS[-1][0]:
            time.sleep(args.cooldown)
    sampler.running = False
    sampler.join(timeout=10)

    samples = pd.DataFrame(sampler.rows)
    samples.to_csv(os.path.join(RAW, "docker_stats_samples.csv"), index=False)
    usage = (samples.groupby(["workload", "container"])
             .agg(avg_cpu_pct=("cpu_pct", "mean"), max_cpu_pct=("cpu_pct", "max"),
                  avg_mem_mib=("mem_mib", "mean"), samples=("cpu_pct", "size"))
             .round(2).reset_index())
    usage.to_csv(os.path.join(RESULTS, "container_usage.csv"), index=False)

    obs = pd.DataFrame(results)
    totals = usage.groupby("workload").agg(total_cpu_pct=("avg_cpu_pct", "sum"),
                                           total_mem_mib=("avg_mem_mib", "sum")).round(2)
    obs = obs.merge(totals, left_on="workload", right_index=True, how="left")
    obs.to_csv(os.path.join(RESULTS, "observation_table.csv"), index=False, quoting=csv.QUOTE_MINIMAL)

    print("\n================ OBSERVATION TABLE ================")
    print(obs.to_string(index=False))
    print("\nSaved to", RESULTS)


if __name__ == "__main__":
    main()
