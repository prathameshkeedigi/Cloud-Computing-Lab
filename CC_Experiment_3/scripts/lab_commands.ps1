# Experiment 3 - Kubernetes lab on Windows (kind, 1 control plane + 2 workers)
# Run in PowerShell (not Git Bash), one command at a time, with Docker Desktop running.
# Lines that need a real Pod name are marked <pod-name>: copy one from the previous output.

# ---- Part 1: install the tools (once, as Administrator) ----------------------
# wsl --install                                   # WSL 2, then restart Windows
# Docker Desktop: install from docker.com, keep "Use WSL 2 instead of Hyper-V"
# winget install -e --id Kubernetes.kubectl
# winget install -e --id Kubernetes.kind
# exit                                            # reopen PowerShell so the new tools are found

# ---- Part 2: check the tools --------------------------------------------------
docker version                                    # Client and Server (Engine) sections
docker run hello-world                            # "Hello from Docker!"
kubectl version --client                          # kubectl client version
kind version                                      # kind version

# ---- Part 3: cluster configuration file --------------------------------------
mkdir k8s-lab
cd k8s-lab
notepad kind-config.yaml                          # paste k8s/kind-config.yaml, save
Get-ChildItem                                     # kind-config.yaml must be listed

# ---- Part 4: build the three-node cluster ------------------------------------
kind create cluster --config kind-config.yaml     # ends with: Set kubectl context to "kind-kind"
kubectl cluster-info --context kind-kind          # control plane + CoreDNS addresses
kubectl get nodes                                 # 3 nodes, STATUS Ready
docker ps                                         # 3 kindest/node containers
kubectl get pods -n kube-system -o wide           # etcd, apiserver, scheduler, controller-manager, ...

# ---- Part 5: deploy NGINX ------------------------------------------------------
kubectl create deployment web --image=nginx --replicas=3
kubectl get deployments                           # wait for READY 3/3
kubectl get pods -o wide                          # NODE column = scheduler's placement
kubectl describe pod <pod-name>                   # Events: "Successfully assigned ... to kind-worker"

# ---- Part 6: scale and self-heal ----------------------------------------------
kubectl scale deployment web --replicas=6
kubectl get pods -o wide                          # 6 Pods spread over the two workers
# optional, in a second window: kubectl get pods -w
kubectl delete pod <pod-name>                     # delete one Pod on purpose
kubectl get pods                                  # 6 Pods again, one with a new name and small AGE

# ---- Clean up (only when finished - Experiment 4 reuses this cluster) --------
# kubectl delete deployment web
# kind delete cluster
