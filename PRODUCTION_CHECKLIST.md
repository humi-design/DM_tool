# Production Checklist

Comprehensive pre-deployment checklist for the Viraly platform.

## Table of Contents

1. [Security](#security)
2. [Configuration](#configuration)
3. [Infrastructure](#infrastructure)
4. [Database](#database)
5. [Monitoring](#monitoring)
6. [Backup](#backup)
7. [Documentation](#documentation)
8. [Testing](#testing)
9. [Deployment](#deployment)
10. [Post-Deployment](#post-deployment)

---

## Security

### Authentication & Authorization

- [ ] All default passwords changed
- [ ] `SECRET_KEY` generated with `openssl rand -hex 32`
- [ ] `JWT_SECRET_KEY` generated with `openssl rand -hex 32`
- [ ] Password hashing uses bcrypt with 14 rounds
- [ ] Session cookies configured with:
  - `SECURE=True`
  - `HTTPONLY=True`
  - `SAMESITE=Lax`
- [ ] CSRF protection enabled (`WTF_CSRF_ENABLED=True`)
- [ ] Rate limiting configured for all endpoints
- [ ] Admin accounts use strong, unique passwords

### API Security

- [ ] API keys rotated from development
- [ ] OAuth credentials updated for production
- [ ] Meta/Facebook app configured for production domain
- [ ] Stripe/Razorpay keys are live keys (not test)
- [ ] Webhook secrets configured and verified
- [ ] No API keys or secrets in code or version control
- [ ] Environment variables used for all secrets

### Network Security

- [ ] HTTPS enforced on all endpoints
- [ ] SSL certificates installed and valid
- [ ] SSL configured with TLS 1.2 or higher
- [ ] Database not exposed to public internet
- [ ] Redis not exposed to public internet
- [ ] Firewall rules configured
- [ ] Non-essential ports closed

### Application Security

- [ ] Debug mode disabled (`FLASK_DEBUG=False`)
- [ ] Error pages don't expose stack traces
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (input sanitization)
- [ ] Security headers configured (see Security Checklist)

---

## Configuration

### Application Settings

```bash
# Required production settings
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=<64-char-hex-string>
JWT_SECRET_KEY=<64-char-hex-string>
```

### Database Settings

- [ ] PostgreSQL configured with production settings
- [ ] Connection pooling configured
- [ ] `SQLALCHEMY_DATABASE_URI` set correctly
- [ ] Database user has minimal required permissions
- [ ] Database backups configured

### Redis Settings

- [ ] Redis password configured
- [ ] Redis persistence enabled (AOF)
- [ ] Memory limit set appropriately
- [ ] `REDIS_URL` correctly configured

### Mail Settings

- [ ] SMTP credentials configured
- [ ] From address set correctly
- [ ] Email delivery tested

### External Services

- [ ] Sentry DSN configured
- [ ] New Relic license key configured
- [ ] Meta/Facebook app configured
- [ ] Stripe/Razorpay credentials configured
- [ ] AWS credentials configured (if using S3)

---

## Infrastructure

### Server Requirements

- [ ] CPU: 4+ cores
- [ ] RAM: 8+ GB
- [ ] Storage: 100+ GB SSD
- [ ] Network: 1 Gbps

### Docker Setup

- [ ] Docker 24.0+ installed
- [ ] Docker Compose 2.20+ installed
- [ ] Container images built
- [ ] Health checks configured
- [ ] Resource limits set

### Container Configuration

```yaml
# Verify docker-compose.yml settings
services:
  app:
    restart: always
    deploy:
      resources:
        limits:
          memory: 2G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      
  db:
    image: postgres:14-alpine
    restart: always
    
  redis:
    image: redis:7-alpine
    restart: always
```

### Load Balancer

- [ ] Load balancer configured
- [ ] SSL termination at load balancer
- [ ] Health checks configured
- [ ] Session affinity if needed
- [ ] Connection draining enabled

### DNS

- [ ] Domain configured
- [ ] DNS records pointing to correct IPs
- [ ] SSL certificate covers all subdomains
- [ ] DNSSEC enabled (recommended)

---

## Database

### PostgreSQL Configuration

- [ ] Version 14+ installed
- [ ] `max_connections` set to 200
- [ ] `shared_buffers` set to 512MB
- [ ] `effective_cache_size` set to 1GB
- [ ] `work_mem` set to 4MB
- [ ] WAL configured for durability
- [ ] Point-in-time recovery enabled

### Migration Status

```bash
# Check migration status
flask db current
flask db history
```

- [ ] All migrations applied
- [ ] Migration backup created
- [ ] Rollback procedure documented

### Performance

- [ ] Slow query log enabled
- [ ] Indexes created for common queries
- [ ] Connection pool size appropriate
- [ ] Query analysis completed

### Security

- [ ] Database user has minimal permissions
- [ ] SSL connections required
- [ ] Passwords stored securely
- [ ] No default passwords

---

## Monitoring

### Sentry

- [ ] Sentry DSN configured
- [ ] Source maps uploaded
- [ ] Error tracking verified
- [ ] Alerts configured

### New Relic (Optional)

- [ ] License key configured
- [ ] APM agent installed
- [ ] Custom metrics added
- [ ] Dashboards created

### Health Checks

```bash
# Verify health endpoint
curl https://api.viraly.io/health
# Response: {"status": "healthy", "timestamp": "..."}

# Verify readiness endpoint
curl https://api.viraly.io/ready
# Response: {"status": "ready", "services": {...}}
```

- [ ] `/health` endpoint returns 200
- [ ] `/ready` endpoint returns 200
- [ ] Kubernetes probes configured
- [ ] Monitoring dashboards created

### Logging

- [ ] Application logs configured
- [ ] Log level set to WARNING
- [ ] Log rotation configured
- [ ] Log aggregation set up
- [ ] Error log alerts configured

### Metrics

- [ ] Request rate tracked
- [ ] Response time tracked
- [ ] Error rate tracked
- [ ] Database query time tracked
- [ ] Cache hit rate tracked

---

## Backup

### Database Backup

- [ ] Automated daily backups configured
- [ ] Backup verification tested
- [ ] Backup retention policy set
- [ ] Point-in-time recovery tested

### File Backup

- [ ] Uploaded files backed up
- [ ] Static files backed up
- [ ] Configuration files backed up

### Backup Schedule

| Type | Frequency | Retention |
|------|-----------|-----------|
| Full database | Daily | 30 days |
| Incremental | Every 6 hours | 7 days |
| Point-in-time | Continuous | 7 days |
| Files | Daily | 14 days |

### Restore Testing

- [ ] Backup restore tested
- [ ] Point-in-time recovery tested
- [ ] Restore documentation created
- [ ] Team trained on restore procedure

---

## Documentation

### Deployment Documentation

- [ ] Deployment guide created
- [ ] Environment variables documented
- [ ] Configuration options documented
- [ ] Troubleshooting guide created

### Runbooks

- [ ] Deployment runbook created
- [ ] Rollback runbook created
- [ ] Scaling runbook created
- [ ] Incident response runbook created

### Architecture

- [ ] System architecture documented
- [ ] Data flow documented
- [ ] Security architecture documented
- [ ] Third-party dependencies documented

---

## Testing

### Unit Tests

```bash
# Run unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

- [ ] All unit tests pass
- [ ] Test coverage > 80%
- [ ] Critical paths covered

### Integration Tests

- [ ] Database integration tests pass
- [ ] Redis integration tests pass
- [ ] External API tests pass
- [ ] Authentication tests pass

### End-to-End Tests

- [ ] User registration works
- [ ] User login works
- [ ] API endpoints respond correctly
- [ ] Error handling works

### Performance Tests

- [ ] Load test completed
- [ ] Stress test completed
- [ ] Response times acceptable
- [ ] No memory leaks detected

### Security Tests

- [ ] OWASP ZAP scan completed
- [ ] SQL injection tests passed
- [ ] XSS tests passed
- [ ] CSRF tests passed

---

## Deployment

### Pre-Deployment

- [ ] Code reviewed and approved
- [ ] All tests passing
- [ ] Migration tested in staging
- [ ] Rollback plan prepared
- [ ] Deployment window scheduled
- [ ] Team notified

### Deployment Steps

1. **Backup database**
   ```bash
   pg_dump -Fc viraly > backup_$(date +%Y%m%d_%H%M%S).dump
   ```

2. **Enable maintenance mode**
   ```bash
   # Configure load balancer to show maintenance page
   ```

3. **Deploy application**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

4. **Run migrations**
   ```bash
   docker-compose exec app flask db upgrade
   ```

5. **Verify deployment**
   ```bash
   curl https://api.viraly.io/health
   curl https://api.viraly.io/ready
   ```

6. **Disable maintenance mode**
   ```bash
   # Update load balancer configuration
   ```

### Post-Deployment

- [ ] Health check passed
- [ ] Key functionality verified
- [ ] No new errors in Sentry
- [ ] Performance metrics normal
- [ ] Team notified of completion

---

## Verification Checklist

### Functionality Verification

- [ ] User can register
- [ ] User can login
- [ ] User can reset password
- [ ] Dashboard loads correctly
- [ ] Instagram account can be connected
- [ ] DMs can be sent
- [ ] Comments can be managed
- [ ] Analytics data displays

### Performance Verification

- [ ] Page load time < 2 seconds
- [ ] API response time < 500ms
- [ ] No database connection errors
- [ ] No Redis connection errors
- [ ] Memory usage stable

### Security Verification

- [ ] HTTPS working on all endpoints
- [ ] Security headers present
- [ ] CSRF protection working
- [ ] Rate limiting working
- [ ] No sensitive data in logs

---

## Sign-Off

### Pre-Deployment Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| DevOps | | | |
| Security | | | |
| Product Owner | | | |

### Post-Deployment Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| DevOps | | | |
| Security | | | |

---

## Emergency Contacts

| Role | Name | Phone | Email |
|------|------|-------|-------|
| On-Call Engineer | | | |
| DevOps Lead | | | |
| Security Lead | | | |
| Product Manager | | | |

---

## Notes

_Add any additional deployment notes here._
