# Phase 1 Infrastructure Deployment Guide

**Phase:** 1 Data Audit  
**Timeline:** Oct 9-23, 2026  
**Deployment Models:** Docker Compose (local) | Kubernetes (cloud)

---

## Quick Start (Docker Compose - Local)

### Prerequisites

- Docker & Docker Compose installed
- 100GB free disk space
- Network access to:
  - https://api.coingecko.com (rate limit: 100 req/min)
  - https://api.glassnode.com (requires API key)
  - AWS S3 or Google Cloud Storage (optional, for backup)

### 1. Environment Setup

```bash
# Navigate to project root
cd /home/user/crypto-agent

# Create environment file
cp .env.phase1.template .env.phase1

# Edit with your API keys
nano .env.phase1
# Required:
# GLASSNODE_API_KEY=your_key_here
# Optional:
# AWS_ACCESS_KEY_ID=your_key_here
# AWS_SECRET_ACCESS_KEY=your_key_here
# GCS_PROJECT_ID=your_project_id

# Load environment
export $(cat .env.phase1 | xargs)
```

### 2. Build Docker Images

```bash
# Build collector image
docker build -f infrastructure/Dockerfile.collector -t igwt/collector:phase1 .

# Build QA image
docker build -f infrastructure/Dockerfile.qa -t igwt/qa:phase1 .
```

### 3. Start Infrastructure

```bash
# Start all services (DuckDB, Redis, PostgreSQL, Minio, Prometheus, Grafana)
docker-compose -f infrastructure/docker-compose.phase1.yml up -d

# Verify services are running
docker-compose -f infrastructure/docker-compose.phase1.yml ps
```

### 4. Run Data Collection

```bash
# Option A: Using Docker service
docker-compose -f infrastructure/docker-compose.phase1.yml run collector

# Option B: Direct Python execution
python3 scripts/phase_1/orchestrate_phase1.py
```

### 5. Monitor Progress

```bash
# Watch collection progress
watch -n 5 'python3 scripts/phase_1/monitor_collection.py'

# View Grafana dashboard
# Open browser: http://localhost:3000
# Login: admin / admin

# View Prometheus metrics
# Open browser: http://localhost:9090
```

### 6. Quality Assurance

```bash
# Run audit (automated in orchestrate_phase1.py)
python3 src/phase_1_qa/audit_completeness.py

# Create immutable snapshot
python3 src/phase_1_qa/create_immutable_snapshot.py

# Verify snapshot integrity
python3 src/phase_1_qa/verify_snapshot.py
```

### 7. Cleanup & Backup

```bash
# Backup data locally
aws s3 sync data/raw/phase_1 s3://crypto-agent-backups/phase_1/ \
  --sse AES256 \
  --storage-class STANDARD_IA

# Stop and remove containers
docker-compose -f infrastructure/docker-compose.phase1.yml down

# Keep volumes for next phase (data persists)
# To remove volumes: add --volumes flag
```

---

## Kubernetes Deployment (Cloud)

### Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Helm (optional)
- Container registry access (Docker Hub, ECR, GCR, etc)

### 1. Prepare Images

```bash
# Tag images for registry
docker tag igwt/collector:phase1 your-registry/igwt/collector:phase1
docker tag igwt/qa:phase1 your-registry/igwt/qa:phase1

# Push to registry
docker push your-registry/igwt/collector:phase1
docker push your-registry/igwt/qa:phase1
```

### 2. Update K8s Manifest

```bash
# Edit k8s-phase1.yaml
# Replace image references:
# - image: igwt/collector:phase1
# + image: your-registry/igwt/collector:phase1

# Set secrets
kubectl create namespace igwt-phase1
kubectl create secret generic phase1-secrets \
  --from-literal=GLASSNODE_API_KEY=$GLASSNODE_API_KEY \
  --from-literal=AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  --from-literal=AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -n igwt-phase1
```

### 3. Deploy

```bash
# Apply manifest
kubectl apply -f infrastructure/k8s-phase1.yaml

# Verify deployment
kubectl get pods -n igwt-phase1
kubectl get pvc -n igwt-phase1

# Monitor collector
kubectl logs -f deployment/igwt-collector -n igwt-phase1

# Monitor QA job
kubectl logs -f job/igwt-qa-audit -n igwt-phase1
```

### 4. Scale Collection

```bash
# If needed, scale to multiple replicas
kubectl scale deployment igwt-collector --replicas=3 -n igwt-phase1

# Note: Ensure different coin ranges to avoid duplicates
# Modify environment variables per pod:
# PHASE1_COIN_START=0
# PHASE1_COIN_END=1000
# PHASE1_COIN_START=1000
# PHASE1_COIN_END=2000
# etc.
```

### 5. Monitor with Prometheus

```bash
# Port-forward to Prometheus
kubectl port-forward svc/prometheus 9090:9090 -n igwt-phase1

# Port-forward to Grafana
kubectl port-forward svc/grafana 3000:3000 -n igwt-phase1

# Access dashboards
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

### 6. Export Data

```bash
# Copy data from PVC
kubectl cp igwt-phase1/igwt-collector-0:/app/data/raw/phase_1 \
  /local/backup/phase_1 -n igwt-phase1

# Or use S3
kubectl exec -it deployment/igwt-collector -n igwt-phase1 -- bash
# Inside pod:
aws s3 sync data/raw/phase_1 s3://bucket/phase_1/ --sse AES256
```

### 7. Cleanup

```bash
# Delete namespace (removes all resources)
kubectl delete namespace igwt-phase1

# Delete PVCs separately if needed
kubectl delete pvc -n igwt-phase1 --all
```

---

## Monitoring & Observability

### Prometheus Metrics

Key metrics automatically collected:

```
igwt_collection_total_coins{source="coingecko"}
igwt_collection_bytes{source="coingecko"}
igwt_collection_duration_seconds
igwt_collection_errors{source="coingecko"}
igwt_api_requests_total{endpoint="coingecko"}
igwt_api_rate_limit_remaining
igwt_data_completeness_percent
igwt_data_gaps_detected
igwt_qa_audit_duration_seconds
```

### Grafana Dashboards

Pre-configured dashboards:

1. **Collection Progress** — Coins collected, data size, API rate limiting
2. **Quality Audit** — Completeness %, gap distribution, outlier detection
3. **Infrastructure Health** — CPU, memory, disk, network
4. **Backup Status** — Location coverage, verification status

### Alerting

```yaml
# Example alert rules
groups:
  - name: phase1
    rules:
      - alert: HighErrorRate
        expr: rate(igwt_collection_errors[5m]) > 0.1
        for: 10m
        annotations:
          summary: "Collection error rate >10%"
      
      - alert: LowCompleteness
        expr: igwt_data_completeness_percent < 95
        for: 1h
        annotations:
          summary: "Completeness below 95% threshold"
      
      - alert: LargeLargeGap
        expr: max(igwt_data_gaps_detected) > 14
        for: 10m
        annotations:
          summary: "Data gap exceeds 14 days"
```

---

## Troubleshooting

### Issue: CoinGecko Rate Limiting

**Symptom:** API errors, 429 responses  
**Solution:**
```bash
# Check rate limit
curl -H "Content-Type: application/json" \
  https://api.coingecko.com/api/v3/ping

# Reduce collection speed
# Modify collect_coingecko.py:
# RATE_LIMIT_DELAY = 1.0  # 60 req/min → 1 req/sec
```

### Issue: Disk Space Exhaustion

**Symptom:** "No space left on device"  
**Solution:**
```bash
# Check disk usage
du -sh data/raw/phase_1

# Clean old backups
rm -rf data/raw/phase_1/*.parquet.old

# Migrate to larger volume
docker-compose stop
# Increase volume size in docker-compose.yml
docker-compose up -d
```

### Issue: Database Connection Errors

**Symptom:** "Failed to connect to DuckDB"  
**Solution:**
```bash
# Verify DuckDB container is running
docker ps | grep duckdb

# Check logs
docker logs igwt-duckdb

# Reset database
rm -rf data/duckdb/*
docker-compose restart duckdb
```

### Issue: Incomplete Data Collection

**Symptom:** <3000 coins collected  
**Solution:**
```bash
# Check failed coin list
grep "Failed to fetch" logs/phase_1/coingecko_*.log | wc -l

# Retry failed coins
# Modify collect_coingecko.py to read from failed list

# Verify API key
echo $GLASSNODE_API_KEY
```

---

## Performance Tuning

### Memory Optimization

```bash
# Reduce batch size for lower-memory systems
# In collect_coingecko.py:
# BATCH_SIZE = 50  # Default: 250

# Increase for faster collection:
# BATCH_SIZE = 500
```

### Network Optimization

```bash
# Use local DNS cache
# docker-compose.yml:
# dns:
#   - 8.8.8.8
#   - 1.1.1.1

# Reduce concurrent requests
# CONCURRENT_REQUESTS = 5  # Default: 10
```

### Storage Optimization

```bash
# Compress Parquet files
# parquet.compression = 'snappy'  # Default: 'zstd'

# Use SSD for DuckDB
# Mount /data/duckdb on fast storage
```

---

## Post-Collection

### Data Validation

```bash
# Run comprehensive audit
python3 src/phase_1_qa/audit_completeness.py

# Verify backup integrity
python3 src/phase_1_qa/verify_snapshot.py

# Generate report
python3 src/phase_1_qa/generate_audit_report.py > reports/phase1_audit.txt
```

### Archive & Retention

```bash
# Create immutable snapshot
python3 src/phase_1_qa/create_immutable_snapshot.py

# Move to cold storage
aws s3 mv s3://active-backups/phase_1 \
  s3://archive-storage/phase_1 \
  --storage-class GLACIER

# Set retention policy
# S3 Object Lock: 90 days minimum retention
```

---

## Rollback Procedures

### If Collection Fails

```bash
# Stop everything
docker-compose -f infrastructure/docker-compose.phase1.yml down

# Restore from backup
aws s3 sync s3://crypto-agent-backups/phase_1 data/raw/phase_1/

# Resume collection
python3 scripts/phase_1/orchestrate_phase1.py --resume
```

### If QA Fails

```bash
# Re-run audit
python3 src/phase_1_qa/audit_completeness.py

# If issues found, investigate specific coins
python3 -c "
import pandas as pd
df = pd.read_parquet('data/raw/phase_1/BTC_bitcoin.parquet')
print(df.describe())
print(df.isna().sum())
"

# Fix data issues and retry QA
```

---

**Status:** Ready for Oct 9, 2026 deployment  
**Support:** Contact Phase 1 Lead for issues  
**Next:** Phase 2 ground truth labeling (Oct 24, 2026)
