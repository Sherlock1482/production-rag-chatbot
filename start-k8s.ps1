# Script to deploy and start the Production RAG Chatbot on Kubernetes
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Starting RAG Chatbot on Kubernetes...    " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Ensure namespace exists
kubectl create namespace ta-rag --dry-run=client -o yaml | kubectl apply -f -

# 2. Update code overrides ConfigMap with latest local code
Write-Host "`n[1/4] Updating backend code overrides ConfigMap..." -ForegroundColor Yellow
kubectl create configmap ta-backend-code-overrides `
  --from-file=backend/utils/datetime_extractor.py `
  --from-file=backend/utils/datetime_normalizer.py `
  --from-file=backend/utils/scheduling_request.py `
  --from-file=backend/utils/candidate_resolver.py `
  --from-file=backend/utils/context_manager.py `
  --from-file=backend/utils/schedule_details.py `
  --from-file=backend/utils/intent_detector.py `
  --from-file=backend/utils/parser.py `
  --from-file=backend/utils/indexer.py `
  --from-file=backend/google_calendar.py `
  --from-file=backend/main.py `
  -n ta-rag --dry-run=client -o yaml | kubectl apply -f -

# 3. Apply all Kubernetes manifests
Write-Host "`n[2/4] Applying manifests in k8s/..." -ForegroundColor Yellow
kubectl apply -f k8s/
kubectl scale deployment --all --replicas=1 -n ta-rag

# 4. Wait for deployments to be ready
Write-Host "`n[3/4] Waiting for services to become ready..." -ForegroundColor Yellow
kubectl rollout status deployment qdrant -n ta-rag --timeout=60s
kubectl rollout status deployment ta-frontend -n ta-rag --timeout=60s
Write-Host "Waiting for backend models (embedding + reranker) to load..." -ForegroundColor Yellow
kubectl rollout status deployment ta-backend -n ta-rag --timeout=180s

# 5. Check if Qdrant ta_documents collection is present in PVC
Write-Host "`n[4/4] Verifying vector database collection..." -ForegroundColor Yellow
$qdrantPod = kubectl get pods -l app=qdrant -n ta-rag -o jsonpath="{.items[0].metadata.name}"
$hasCollection = kubectl exec -n ta-rag $qdrantPod -- test -d /qdrant/storage/collections/ta_documents 2>&1
if ($LASTEXITCODE -ne 0 -and (Test-Path "qdrant/storage/collections/ta_documents")) {
    Write-Host "Syncing local ta_documents collection to Qdrant PVC..." -ForegroundColor Cyan
    kubectl cp qdrant/storage/collections/ta_documents "ta-rag/${qdrantPod}:/qdrant/storage/collections/ta_documents"
    kubectl rollout restart deployment qdrant -n ta-rag
    kubectl rollout status deployment qdrant -n ta-rag --timeout=60s
}

Write-Host "`n==========================================" -ForegroundColor Green
Write-Host " All services are up and running!         " -ForegroundColor Green
Write-Host " Frontend: http://localhost:3000           " -ForegroundColor Green
Write-Host " Backend:  http://localhost:8000           " -ForegroundColor Green
Write-Host " Qdrant:   http://localhost:6333 (internal)" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
kubectl get pods,svc -n ta-rag
