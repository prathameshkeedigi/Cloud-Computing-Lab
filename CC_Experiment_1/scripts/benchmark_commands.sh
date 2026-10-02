#!/usr/bin/env bash
# Experiment 1 - Hypervisor performance analysis
# Run these commands inside the Ubuntu guest VM (same steps on Type-1 and Type-2).

hostnamectl                                  # hostname, OS, kernel, virtualisation type
lscpu                                        # CPU model, number of vCPUs, hypervisor vendor
free -h                                      # memory allocation and usage
df -h                                        # disk allocation and usage
top -b -n 1 | head -20                       # one snapshot of CPU / memory / load average

sudo apt update                              # refresh package index
sudo apt install sysbench -y                 # install the benchmark tool
sysbench --version                           # verify installation

sysbench cpu --cpu-max-prime=20000 run       # CPU benchmark (1 thread, 10 seconds)
