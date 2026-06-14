# Scaling Guide

Comprehensive guide for scaling the Viraly platform to handle increased load.

## Table of Contents

1. [Scaling Strategies](#scaling-strategies)
2. [Horizontal Scaling](#horizontal-scaling)
3. [Vertical Scaling](#vertical-scaling)
4. [Database Scaling](#database-scaling)
5. [Caching Strategy](#caching-strategy)
6. [Load Balancing](#load-balancing)
7. [Auto-Scaling](#auto-scaling)
8. [Performance Monitoring](#performance-monitoring)

---

## Scaling Strategies

### Scaling Types

| Type | Description | Use Case |
|------|-------------|----------|
| **Horizontal** | Add more instances | High traffic, stateless services |
| **Vertical** | Increase instance size | Moderate traffic, stateful services |
| **Database** | Read replicas, sharding | Database bottlenecks |
| **Caching** | Reduce database load | Repeated queries, static data |

### Scaling Triggers

| Metric | Warning Threshold | Critical Threshold |
|--------|-------------------|-------------------|
| CPU Usage | 70% | 85% |
| Memory Usage | 75% | 90% |
| Request Latency | 500ms | 1000ms |
| Error Rate | 1% | 5% |
| Database Connections | 80% | 95% |

---

## Horizontal Scaling

### Application Scaling

#### Docker Swarm

```yaml
# docker-compose.swarm.yml
version: '3.8'

services:
  app:
    image: viraly/app:latest
    deploy:
      replicas: 4
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    environment:
      - FLASK_ENV=production
      - FLASK_WORKERS=2
```

```bash
# Deploy to swarm
docker stack deploy -c docker-compose.swarm.yml viraly

# Scale manually
docker service scale viraly_app=8

# Check status
docker service ls
docker service ps viraly_app
```

#### Kubernetes

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: viraly-app
  namespace: viraly
spec:
  replicas: 4
  selector:
    matchLabels:
      app: viraly-app
  template:
    metadata:
      labels:
        app: viraly-app
    spec:
      containers:
      - name: app
        image: viraly/app:latest
        ports:
        - containerPort: 5000
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        env:
        - name: FLASK_WORKERS
          value: "2"
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
```

```bash
# Apply deployment
kubectl apply -f k8s/deployment.yaml

# Scale deployment
kubectl scale deployment viraly-app --replicas=8

# Check status
kubectl get pods -n viraly -l app=viraly-app
```

### Gunicorn Scaling

```bash
# Recommended worker count formula
workers = (2 * CPU cores) + 1

# Example for 4 CPU cores
gunicorn \
    --workers 9 \
    --worker-class sync \
    --worker-connections 1000 \
    --max-requests 10000 \
    --max-requests-jitter 1000 \
    --timeout 60 \
    --keep-alive 5 \
    wsgi:app
```

---

## Vertical Scaling

### Instance Sizes

| Size | CPU | Memory | Max Connections | Use Case |
|------|-----|--------|-----------------|----------|
| Small | 2 | 4 GB | 100 | Development, staging |
| Medium | 4 | 8 GB | 200 | Small production |
| Large | 8 | 16 GB | 400 | Medium production |
| XLarge | 16 | 32 GB | 800 | Large production |
| 2XLarge | 32 | 64 GB | 1600 | Enterprise |

### Resource Configuration

#### Application Container

```yaml
# docker-compose.prod.yml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 1G
```

#### PostgreSQL Container

```yaml
services:
  db:
    image: postgres:14-alpine
    command: >
      postgres
      -c max_connections=400
      -c shared_buffers=2GB
      -c effective_cache_size=6GB
      -c maintenance_work_mem=512MB
      -c checkpoint_completion_target=0.9
      -c wal_buffers=32MB
      -c default_statistics_target=200
      -c random_page_cost=1.1
      -c effective_io_concurrency=200
      -c work_mem=10MB
      -c min_wal_size=4GB
      -c max_wal_size=16GB
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
```

---

## Database Scaling

### Read Replicas

```bash
# Create read replica
aws rds create-db-instance-read-replica \
    --db-instance-identifier viraly-read-replica \
    --source-db-instance-identifier viraly-primary \
    --db-instance-class db.r5.large
```

### Connection Pooling with PgBouncer

```yaml
# PgBouncer configuration
[databases]
viraly = host=primary.db.example.com port=5432 dbname=viraly

[pgbouncer]
listen_port = 6432
listen_addr = 0.0.0.0
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 50
min_pool_size = 10
reserve_pool_size = 10
reserve_pool_timeout = 5
max_db_connections = 200
max_connections = 1000
server_lifetime = 3600
server_idle_timeout = 600
```

### PostgreSQL Partitioning

```sql
-- Create partitioned table for audit logs
CREATE TABLE audit_logs (
    id UUID NOT NULL,
    user_id UUID,
    action VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create monthly partitions
CREATE TABLE audit_logs_2024_01 PARTITION OF audit_logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

---

## Caching Strategy

### Redis Cache Configuration

```yaml
# docker-compose.yml
redis:
  image: redis:7-alpine
  command: >
    redis-server
    --requirepass ${REDIS_PASSWORD}
    --maxmemory 2gb
    --maxmemory-policy allkeys-lru
    --appendonly yes
    --appendfsync everysec
```

### Cache Patterns

```python
# services/cache_service.py
from functools import wraps
from flask import current_app
import json

def cached(key, timeout=300):
    """Cache decorator for functions."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            cache_key = f"{key}:{args}:{kwargs}"
            
            # Try to get from cache
            cached_value = current_app.cache.get(cache_key)
            if cached_value:
                return json.loads(cached_value)
            
            # Execute function
            result = f(*args, **kwargs)
            
            # Store in cache
            current_app.cache.set(cache_key, json.dumps(result), timeout=timeout)
            
            return result
        return decorated
    return decorator
```

---

## Load Balancing

### Nginx Load Balancer

```nginx
upstream viraly_backend {
    least_conn;
    server app-1.example.com:5000 weight=5;
    server app-2.example.com:5000 weight=5;
    server app-3.example.com:5000 weight=5;
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name api.viraly.io;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://viraly_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
    }

    location /health {
        proxy_pass http://viraly_backend;
        access_log off;
    }
}
```

---

## Auto-Scaling

### Kubernetes HPA

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: viraly-app-hpa
  namespace: viraly
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: viraly-app
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
    scaleUp:
      stabilizationWindowSeconds: 0
```

---

## Performance Monitoring

### Key Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Request Rate | Requests per second | Monitor for spikes |
| Response Time | P50, P95, P99 latency | P95 < 500ms |
| Error Rate | 4xx and 5xx responses | < 1% |
| CPU Usage | Application CPU | < 70% |
| Memory Usage | Application memory | < 80% |
| Database Queries | Query count and time | < 100ms avg |
| Cache Hit Rate | Redis cache efficiency | > 90% |

---

## Capacity Planning

### Traffic Estimates

| Scenario | Concurrent Users | Requests/sec | DB Queries/sec |
|----------|------------------|--------------|----------------|
| Normal | 1,000 | 100 | 50 |
| Peak | 10,000 | 1,000 | 500 |
| Extreme | 50,000 | 5,000 | 2,500 |

### Resource Requirements

| Load Level | App Instances | DB Connections | Redis Memory |
|------------|---------------|----------------|--------------|
| Normal | 2 | 50 | 512 MB |
| Peak | 8 | 150 | 2 GB |
| Extreme | 20 | 400 | 4 GB |

### Scaling Recommendations

1. **Start with vertical scaling** up to medium instances
2. **Add horizontal scaling** when CPU/memory limits reached
3. **Implement caching** before adding more instances
4. **Add read replicas** when database becomes bottleneck
5. **Use auto-scaling** for handling traffic spikes
6. **Monitor and adjust** based on actual usage patterns
