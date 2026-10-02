#!/bin/bash
# Environment preparation inside the Ubuntu VM (Steps 2-6 of the lab manual).
mkdir -p ~/vm-vs-container-performance && cd ~/vm-vs-container-performance
mkdir -p docs results/raw results/processed results/figures scripts workloads

nproc
free -h
lscpu | grep -E '^CPU\(s\)|^Core|^Socket'

sudo apt update
sudo apt install -y sysbench fio iperf3 htop iotop sysstat python3 python3-pip git curl
sysbench --version; fio --version; iperf3 --version; python3 --version; git --version

sudo apt install -y docker.io
sudo systemctl enable --now docker
sudo docker --version
sudo docker run --rm hello-world
sudo usermod -aG docker $USER      # then log out / in (or: newgrp docker)

docker build -t vm-container-benchmark -f docker/Dockerfile .
docker build -t performance-api -f api/Dockerfile api
