# Experiment 4 - Resource allocation, scheduling and load balancing (kind cluster from Experiment 3)
# Run in PowerShell from the folder that holds deployment.yaml and service.yaml.
# These are the commands that were run in the lab, in order (see screenshots 01-04).

cd C:\Users\Admin\k8s-lab

# Step 1 - verify the cluster
kubectl get nodes -o wide
# (kind create cluster --config kind-config.yaml was typed again here; it failed harmlessly
#  because the cluster from Experiment 3 already existed)

# Step 3 - Deployment with requests and limits (6 replicas)
notepad deployment.yaml                         # paste k8s/deployment.yaml
kubectl apply -f deployment.yaml

# Step 4 - where did the Pods go?
kubectl get pods -o wide

# Step 6 - more replicas
kubectl scale deployment resource-demo --replicas=12
kubectl get pods -o wide

# Step 7 - NodePort Service
notepad service.yaml                            # paste k8s/service.yaml
kubectl apply -f service.yaml

# Step 8 - Service and its backend endpoints
kubectl get services
kubectl get endpoints nginx-service

# Step 9 - test the application through the Service
# (kind node IPs are not reachable from Windows, so the test was done from inside the cluster)
kubectl run test-curl --rm -i --tty --image=curlimages/curl -- http://nginx-service:80
kubectl port-forward service/nginx-service 30080:80   # then open http://localhost:30080, Ctrl+C to stop

# Step 11 - clean up (the cluster itself stays)
kubectl delete service nginx-service
kubectl delete deployment resource-demo
