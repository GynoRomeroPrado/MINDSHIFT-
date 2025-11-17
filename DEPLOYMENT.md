# MindShift Deployment Guide

## Overview

This guide covers deploying MindShift to production environments (AWS, GCP, or Azure).

## Architecture

```
┌─────────────────┐
│   CloudFlare    │  ← CDN + DDoS Protection
└────────┬────────┘
         │
┌────────▼────────┐
│  Load Balancer  │  ← AWS ALB / GCP LB
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼───┐
│ API  │  │ API  │  ← Kubernetes Pods (Auto-scaling)
└───┬──┘  └──┬───┘
    │         │
┌───▼─────────▼───┐
│   PostgreSQL    │  ← RDS / Cloud SQL (Multi-AZ)
└─────────────────┘
┌─────────────────┐
│     Redis       │  ← ElastiCache / Memorystore
└─────────────────┘
┌─────────────────┐
│   S3 / GCS      │  ← Static files, models, backups
└─────────────────┘
```

## Prerequisites

- Docker & Docker Compose
- Kubernetes cluster (EKS, GKE, or AKS)
- kubectl configured
- helm installed
- Domain name configured
- SSL certificate (Let's Encrypt or ACM)

## Environment Variables

Create `.env.production` file:

```bash
# Application
APP_NAME=MindShift
APP_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=false

# API Keys (CRITICAL: Use secrets management)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
PINECONE_API_KEY=...

# Database (Use managed service)
DATABASE_URL=postgresql://user:pass@db-host:5432/mindshift
REDIS_URL=redis://redis-host:6379

# Security (Generate strong secrets!)
JWT_SECRET=<64-char-random-string>
ENCRYPTION_KEY=<32-char-random-string>

# Features
ENABLE_VOICE=true
ENABLE_CRISIS_DETECTION=true
AI_MODEL_PRIMARY=gpt-4-turbo-preview
AI_MODEL_FALLBACK=claude-3-sonnet-20240229

# Monitoring
SENTRY_DSN=https://...@sentry.io/...
ENABLE_PROMETHEUS=true

# Email (for alerts)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG....

# CORS
CORS_ORIGINS=["https://app.mindshift.ai","https://mindshift.ai"]

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Privacy
DATA_RETENTION_DAYS=90
ENABLE_DIFFERENTIAL_PRIVACY=true
```

## AWS Deployment

### 1. Infrastructure Setup (Terraform)

```bash
cd infrastructure/terraform/aws
terraform init
terraform plan -var-file=production.tfvars
terraform apply
```

This creates:
- VPC with public/private subnets
- RDS PostgreSQL (Multi-AZ, encrypted)
- ElastiCache Redis
- EKS cluster
- S3 buckets (models, backups)
- IAM roles and security groups
- Application Load Balancer
- Route53 DNS records
- ACM SSL certificate

### 2. Database Migration

```bash
# Run migrations
kubectl apply -f k8s/jobs/db-migration.yaml

# Verify
kubectl logs job/db-migration
```

### 3. Secrets Management

```bash
# Store secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name mindshift/production/openai-key \
  --secret-string "sk-..."

# Or use Kubernetes secrets
kubectl create secret generic mindshift-secrets \
  --from-env-file=.env.production \
  --namespace=mindshift
```

### 4. Deploy Application

```bash
# Deploy backend
kubectl apply -f k8s/backend/deployment.yaml
kubectl apply -f k8s/backend/service.yaml
kubectl apply -f k8s/backend/hpa.yaml  # Auto-scaling

# Deploy frontend
kubectl apply -f k8s/frontend/deployment.yaml
kubectl apply -f k8s/frontend/service.yaml

# Configure ingress
kubectl apply -f k8s/ingress.yaml
```

### 5. Monitoring Setup

```bash
# Install Prometheus + Grafana
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace

# Access Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
# Default: admin/prom-operator
```

### 6. Configure Auto-scaling

```yaml
# k8s/backend/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mindshift-backend
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mindshift-backend
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## GCP Deployment

### 1. Setup GKE Cluster

```bash
gcloud container clusters create mindshift-cluster \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-4 \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 10 \
  --enable-autorepair \
  --enable-autoupgrade
```

### 2. Create Cloud SQL Instance

```bash
gcloud sql instances create mindshift-db \
  --database-version=POSTGRES_15 \
  --tier=db-n1-standard-2 \
  --region=us-central1 \
  --backup-start-time=03:00 \
  --enable-bin-log \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=04
```

### 3. Setup Cloud Memorystore (Redis)

```bash
gcloud redis instances create mindshift-redis \
  --size=5 \
  --region=us-central1 \
  --redis-version=redis_7_0
```

### 4. Deploy Application

```bash
# Build and push images
gcloud builds submit --config cloudbuild.yaml

# Deploy to GKE
kubectl apply -f k8s/
```

## Docker Compose (Simple Deployment)

For smaller deployments or development:

```bash
# Production Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose logs -f backend

# Scale API servers
docker-compose up -d --scale backend=3
```

## Database Management

### Backup Strategy

**Automated Backups**:
- Daily full backups (retained 30 days)
- Point-in-time recovery enabled
- Cross-region replication for DR

```bash
# Manual backup
pg_dump -h $DB_HOST -U $DB_USER mindshift > backup_$(date +%Y%m%d).sql

# Upload to S3
aws s3 cp backup_$(date +%Y%m%d).sql s3://mindshift-backups/
```

### Database Migrations

```bash
# Create migration
alembic revision -m "add_new_feature"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## SSL/TLS Configuration

### Let's Encrypt (Free)

```yaml
# cert-manager installation
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# ClusterIssuer
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@mindshift.ai
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

## Monitoring & Alerting

### Key Metrics to Monitor

**Application**:
- Request rate (req/sec)
- Response time (p50, p95, p99)
- Error rate (%)
- Active users

**Infrastructure**:
- CPU utilization (%)
- Memory usage (%)
- Disk I/O
- Network throughput

**Business**:
- Daily active users
- Conversations per day
- Burnout predictions generated
- Crisis alerts triggered

### Alerting Rules

```yaml
# Prometheus alerts
groups:
- name: mindshift_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"

  - alert: HighResponseTime
    expr: http_request_duration_seconds{quantile="0.95"} > 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "95th percentile response time > 2s"
```

## Security Hardening

### 1. Network Security
- Enable VPC firewall rules
- Use private subnets for databases
- Configure security groups (minimal access)
- Enable DDoS protection (CloudFlare)

### 2. Application Security
- Enable rate limiting
- Use HTTPS only (HSTS)
- Implement CORS properly
- Sanitize all inputs
- Use parameterized queries

### 3. Secrets Management
- Never commit secrets to git
- Use AWS Secrets Manager / GCP Secret Manager
- Rotate secrets quarterly
- Use IAM roles instead of API keys where possible

### 4. Compliance
- Enable audit logging
- Implement HIPAA controls:
  - Encryption at rest (AES-256)
  - Encryption in transit (TLS 1.3)
  - Access logs
  - Regular security audits
  - Business Associate Agreements (BAA)

## Performance Optimization

### Database
- Add indexes on frequently queried columns
- Use connection pooling
- Enable query caching (Redis)
- Partition large tables
- Regular VACUUM and ANALYZE

### API
- Implement response caching
- Use CDN for static assets
- Enable gzip compression
- Optimize N+1 queries
- Use async/await for I/O

### Frontend
- Code splitting
- Lazy loading
- Image optimization
- Bundle size optimization
- Service worker for offline support

## Disaster Recovery

### RTO & RPO Goals
- **Recovery Time Objective (RTO)**: 4 hours
- **Recovery Point Objective (RPO)**: 1 hour

### DR Plan

**Scenario 1: Database Failure**
1. Promote read replica to primary (automatic)
2. Update connection string
3. Verify data integrity
4. Resume normal operations
**Expected downtime**: <15 minutes

**Scenario 2: Region Failure**
1. Activate DR region (us-west-2)
2. Restore from latest backup
3. Update DNS (Route53)
4. Verify all services
**Expected downtime**: 2-4 hours

**Scenario 3: Data Corruption**
1. Identify corruption timestamp
2. Restore from point-in-time backup
3. Apply recent transactions
4. Validate data
**Expected downtime**: 1-2 hours

## Cost Optimization

### AWS Estimated Monthly Costs (1000 users)

| Service | Instance Type | Cost/Month |
|---------|--------------|------------|
| EKS Control Plane | - | $73 |
| EC2 (worker nodes) | 3x t3.large | $190 |
| RDS PostgreSQL | db.t3.medium | $120 |
| ElastiCache Redis | cache.t3.medium | $60 |
| ALB | - | $25 |
| S3 | 100GB | $3 |
| Data Transfer | 500GB | $45 |
| OpenAI API | ~10M tokens | $200 |
| **Total** | | **~$716/month** |

**Per User**: ~$0.72/month infrastructure cost

### Cost Optimization Tips
- Use Spot Instances for non-critical workloads
- Enable S3 lifecycle policies
- Use CloudFront CDN
- Optimize AI model usage (caching, prompt engineering)
- Right-size instances based on actual usage

## Rollout Strategy

### Blue-Green Deployment

```bash
# Deploy green (new version)
kubectl apply -f k8s/backend-green.yaml

# Test green
curl https://green.mindshift.ai/health

# Switch traffic (update service selector)
kubectl patch service mindshift-backend \
  -p '{"spec":{"selector":{"version":"green"}}}'

# Monitor for 10 minutes

# If issues, rollback
kubectl patch service mindshift-backend \
  -p '{"spec":{"selector":{"version":"blue"}}}'
```

### Canary Deployment

```bash
# Deploy canary (10% traffic)
kubectl apply -f k8s/backend-canary.yaml

# Monitor metrics for 1 hour

# If successful, increase to 50%
kubectl scale deployment mindshift-backend-canary --replicas=5

# Full rollout
kubectl scale deployment mindshift-backend-canary --replicas=10
kubectl scale deployment mindshift-backend --replicas=0
```

## Troubleshooting

### Common Issues

**Issue**: High memory usage
```bash
# Check pod memory
kubectl top pods

# Increase memory limits
kubectl edit deployment mindshift-backend
# Update: resources.limits.memory: "2Gi"
```

**Issue**: Database connection pool exhausted
```bash
# Increase pool size in config
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=10
```

**Issue**: Slow API responses
```bash
# Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

# Add missing indexes
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
```

## Maintenance Windows

**Recommended Schedule**:
- Minor updates: Wednesday 2-4 AM ET (low traffic)
- Major updates: Sunday 1-5 AM ET
- Database maintenance: Sunday 3-4 AM ET

**Communication**:
- Announce 7 days in advance
- Send reminder 24 hours before
- Status page updates during maintenance

---

## Support

For deployment issues:
- Email: devops@mindshift.ai
- Slack: #deployment-support
- On-call: PagerDuty rotation

**Document Version**: 1.0
**Last Updated**: January 2025
