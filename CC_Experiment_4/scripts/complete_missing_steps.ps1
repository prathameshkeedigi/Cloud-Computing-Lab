# Experiment 4 - commands for the manual steps that were NOT captured in the screenshots
# (Steps 2, 4-events, 5, 8-EndpointSlices, 9-load-balancing proof, 10 and the extension).
# Run in PowerShell with the kind cluster running. Results go to results\raw\extra\.

New-Item -ItemType Directory -Force results\raw\extra | Out-Null

# ---- 0. Metrics Server (needed for kubectl top; kind does not install it) --------------
kubectl get deployment metrics-server -n kube-system
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
# kind's kubelets use self-signed certificates, so allow insecure TLS to the kubelet:
kubectl patch deployment metrics-server -n kube-system --type=json `
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
kubectl rollout status deployment metrics-server -n kube-system
Start-Sleep -Seconds 60                          # first metrics need about a minute

# ---- Step 2 - utilisation BEFORE the workload ----------------------------------------
kubectl top nodes | Tee-Object results\raw\extra\step2_top_nodes_before.txt

# ---- Steps 3-4 - deploy 6 replicas and read the scheduler events ---------------------
kubectl apply -f k8s\deployment.yaml
kubectl rollout status deployment resource-demo
kubectl get pods -o wide | Tee-Object results\raw\extra\step4_pods_6.txt
kubectl get events --sort-by=.metadata.creationTimestamp | Tee-Object results\raw\extra\step4_events.txt

# ---- Step 5 - allocated resources per node + per-Pod usage ---------------------------
kubectl describe nodes | Tee-Object results\raw\extra\step5_describe_nodes.txt
kubectl top pods | Tee-Object results\raw\extra\step5_top_pods.txt

# ---- Step 6 - 12 replicas -------------------------------------------------------------
kubectl scale deployment resource-demo --replicas=12
kubectl rollout status deployment resource-demo
kubectl get pods -o wide | Tee-Object results\raw\extra\step6_pods_12.txt

# ---- Steps 7-8 - Service, Endpoints and EndpointSlices -------------------------------
kubectl apply -f k8s\service.yaml
kubectl get services | Tee-Object results\raw\extra\step8_services.txt
kubectl get endpoints nginx-service | Tee-Object results\raw\extra\step8_endpoints.txt
kubectl get endpointslices -l kubernetes.io/service-name=nginx-service -o wide |
  Tee-Object results\raw\extra\step8_endpointslices.txt

# ---- Step 9 - show HOW the Service spreads 120 requests over the Pods ----------------
# Each nginx Pod logs one line per request; count lines per Pod after the test.
kubectl run lb-test --rm -i --restart=Never --image=curlimages/curl --command -- `
  sh -c 'for i in $(seq 1 120); do curl -s -o /dev/null http://nginx-service:80; done; echo done'
kubectl get pods -l app=resource-demo -o name | ForEach-Object {
  $n = (kubectl logs $_ | Select-String '"GET / HTTP').Count
  "$_,$n"
} | Tee-Object results\raw\extra\step9_requests_per_pod.csv

# ---- Step 10 - utilisation AFTER scaling ---------------------------------------------
kubectl top nodes | Tee-Object results\raw\extra\step10_top_nodes_after.txt
kubectl top pods  | Tee-Object results\raw\extra\step10_top_pods_after.txt

# ---- Extension - a Pod that asks for more CPU than any node can give -----------------
kubectl create deployment big-request --image=nginx
kubectl set resources deployment big-request --requests=cpu=64
kubectl get pods -l app=big-request -o wide | Tee-Object results\raw\extra\ext_pending_pod.txt
kubectl describe pod -l app=big-request | Tee-Object results\raw\extra\ext_pending_describe.txt
kubectl delete deployment big-request

# ---- Step 11 - clean up ---------------------------------------------------------------
kubectl delete service nginx-service
kubectl delete deployment resource-demo
