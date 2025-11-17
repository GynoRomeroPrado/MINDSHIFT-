# MindShift Deployment Checklist

## Pre-Deployment Validation

### 1. Code Quality ✅
- [ ] Run `python backend/scripts/validate.py` - No syntax errors
- [ ] Run `./backend/scripts/lint.sh` - Code quality checks pass
- [ ] Run `./backend/scripts/pre_deploy_check.sh` - All pre-deployment checks pass
- [ ] All Python files have proper `__init__.py` in directories
- [ ] No hardcoded secrets or API keys in code

### 2. Dependencies ✅
- [ ] `requirements.txt` has no duplicate packages
- [ ] No stdlib packages (like `asyncio`) in requirements.txt
- [ ] All dependencies are pinned to specific versions
- [ ] `pip check` shows no conflicts
- [ ] All required dependencies are installed

### 3. Configuration ✅
- [ ] `.env` file configured with all required variables
- [ ] `DATABASE_URL` is set correctly
- [ ] `REDIS_URL` is set correctly
- [ ] `JWT_SECRET` is strong and unique
- [ ] `ENCRYPTION_KEY` is set
- [ ] `OPENAI_API_KEY` is valid
- [ ] `ANTHROPIC_API_KEY` is valid
- [ ] CORS origins are properly configured
- [ ] Debug mode is OFF for production

### 4. Database ✅
- [ ] Database migrations are up to date
- [ ] Run `python backend/scripts/migrate.py up` successfully
- [ ] Database backup configured (see `backend/scripts/backup.sh`)
- [ ] Database connection pool settings optimized
- [ ] Database indexes are in place

### 5. Testing ✅
- [ ] Unit tests pass: `pytest backend/tests/`
- [ ] Integration tests pass
- [ ] AI Coach tests pass
- [ ] Burnout ML tests pass
- [ ] No failing tests

### 6. Security ✅
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] CSRF protection enabled
- [ ] Rate limiting configured
- [ ] Authentication working correctly
- [ ] Authorization permissions set up
- [ ] HTTPS/TLS enabled in production
- [ ] Security headers configured
- [ ] Run security scan: `bandit -r backend/`

### 7. Docker & Containers ✅
- [ ] Backend Dockerfile builds successfully
- [ ] Frontend Dockerfile builds successfully
- [ ] Docker healthchecks working
- [ ] Multi-stage builds optimized
- [ ] No secrets in Docker images
- [ ] Images scanned for vulnerabilities

### 8. Kubernetes (if applicable) ✅
- [ ] All manifests have valid YAML syntax
- [ ] Resource limits configured (CPU/Memory)
- [ ] HorizontalPodAutoscaler configured
- [ ] Health probes (liveness/readiness) configured
- [ ] ConfigMaps and Secrets created
- [ ] Ingress configured correctly
- [ ] Service accounts configured

### 9. Infrastructure ✅
- [ ] Terraform plans validated: `terraform plan`
- [ ] RDS PostgreSQL configured
- [ ] ElastiCache Redis configured
- [ ] S3 buckets created (models, backups)
- [ ] EKS cluster ready (if using K8s)
- [ ] VPC and networking configured
- [ ] Security groups configured
- [ ] Backup policies in place

### 10. Monitoring & Logging ✅
- [ ] Prometheus metrics endpoint working (`/metrics`)
- [ ] Structured logging configured
- [ ] Error tracking (Sentry) configured
- [ ] CloudWatch logs enabled
- [ ] Alerts configured for critical errors
- [ ] Dashboard created (Grafana)

### 11. Performance ✅
- [ ] Database queries optimized
- [ ] N+1 query issues resolved
- [ ] Caching configured (Redis)
- [ ] API response times acceptable (< 500ms)
- [ ] Load testing completed
- [ ] CDN configured for static assets

### 12. Compliance & Privacy ✅
- [ ] GDPR data export working
- [ ] GDPR data deletion working
- [ ] Privacy policy updated
- [ ] Terms of service updated
- [ ] Data retention policies configured
- [ ] Audit logging enabled
- [ ] User consent flows implemented

## Deployment Steps

### Stage 1: Staging Deployment
1. [ ] Deploy to staging environment
2. [ ] Run smoke tests on staging
3. [ ] Verify all endpoints working
4. [ ] Check database migrations applied
5. [ ] Test critical user flows
6. [ ] Monitor logs for errors
7. [ ] Load test staging environment

### Stage 2: Production Deployment
1. [ ] Tag release in Git: `git tag v1.0.0`
2. [ ] Backup production database
3. [ ] Set maintenance mode (if needed)
4. [ ] Deploy backend to production
5. [ ] Deploy frontend to production
6. [ ] Run database migrations
7. [ ] Disable maintenance mode
8. [ ] Verify health endpoints: `/health`
9. [ ] Check metrics endpoint: `/metrics`
10. [ ] Monitor error rates
11. [ ] Test critical features

### Stage 3: Post-Deployment
1. [ ] Monitor application logs for 30 minutes
2. [ ] Check error rates in Sentry/monitoring
3. [ ] Verify user registrations working
4. [ ] Test AI coach conversations
5. [ ] Test burnout predictions
6. [ ] Verify email notifications
7. [ ] Check database performance
8. [ ] Monitor Redis cache hits
9. [ ] Review security logs
10. [ ] Update documentation

## Rollback Plan

### If Deployment Fails:
1. [ ] Immediately revert to previous version
2. [ ] Restore database from backup (if needed)
3. [ ] Check and fix the issue
4. [ ] Re-run pre-deployment checks
5. [ ] Attempt deployment again

### Rollback Commands:
```bash
# Kubernetes rollback
kubectl rollout undo deployment/mindshift-backend

# Database rollback
python backend/scripts/migrate.py down

# Restore from backup
./backend/scripts/restore_backup.sh <backup_file>
```

## Critical Metrics to Monitor

### Application Health
- [ ] HTTP 5xx error rate < 0.1%
- [ ] HTTP 4xx error rate < 5%
- [ ] API response time p95 < 1000ms
- [ ] API response time p50 < 300ms

### Infrastructure
- [ ] CPU usage < 70%
- [ ] Memory usage < 80%
- [ ] Database connections < 80% of pool
- [ ] Redis memory < 80%

### Business Metrics
- [ ] User registrations working
- [ ] AI coach sessions starting
- [ ] Burnout predictions generating
- [ ] Daily check-ins saving

## Emergency Contacts

- **DevOps Lead**: [Contact info]
- **Backend Lead**: [Contact info]
- **Database Admin**: [Contact info]
- **Security Team**: [Contact info]
- **On-call Engineer**: [Contact info]

## Sign-off

- [ ] Code reviewed by: _______________
- [ ] Security reviewed by: _______________
- [ ] DevOps approved by: _______________
- [ ] Product approved by: _______________

---

**Deployment Date**: _____________
**Deployed By**: _____________
**Version**: v1.0.0
**Environment**: Production
