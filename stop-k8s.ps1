param (
    [switch]$Delete
)

if ($Delete) {
    Write-Host "Tearing down all Kubernetes resources in namespace ta-rag..." -ForegroundColor Yellow
    kubectl delete -f k8s/
    Write-Host "All resources deleted." -ForegroundColor Green
} else {
    Write-Host "Freeing up ports 8000 and 3000 & pausing Kubernetes pods..." -ForegroundColor Yellow
    # 1. Scale down deployments to 0 (frees CPU and RAM)
    kubectl scale deployment --all --replicas=0 -n ta-rag

    # 2. Delete LoadBalancer services (frees ports 8000 and 3000 in Windows/Docker)
    kubectl delete svc backend-service frontend-service -n ta-rag --ignore-not-found

    Write-Host "`nPorts 8000 and 3000 are now completely FREE for local use!" -ForegroundColor Green
    Write-Host "To turn Kubernetes back ON at any time, simply run: .\start-k8s.ps1" -ForegroundColor Cyan
}
