# Deployment Guide

This guide covers deploying the Viraly platform to production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Docker Deployment](#docker-deployment)
4. [Manual Deployment](#manual-deployment)
5. [Post-Deployment](#post-deployment)
6. [Container Orchestration](#container-orchestration)

---

## Prerequisites

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Storage | 50 GB | 100+ GB SSD |
| Network | 100 Mbps | 1 Gbps |

### Software Requirements

- **Operating System**: Ubuntu 22.04 LTS, Debian 12, or RHEL 9
- **Docker**: 24.0+
- **Docker Compose**: 2.20+
- **Python**: 3.11+
- **PostgreSQL**: 14+
- **Redis**: 7+

### Required Services

1. **PostgreSQL Database** - Primary data store
2. **Redis** - Caching and rate limiting
3. **SMTP Service** - Email delivery (SendGrid, AWS SES, etc.)
4. **SSL Certificates** - TLS/SSL for HTTPS

---

## Environment Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/viraly.git
cd viraly
```

### 2. Create Environment File

```bash
cp .env.example .env
```

### 3. Generate Secure Keys

```bash
# Generate Flask secret key
SECRET_KEY=$(openssl rand -hex 32)
echo "SECRET_KEY=${SECRET_KEY}" >> .env

# Generate JWT secret key
JWT_SECRET_KEY=$(openssl rand -hex 32)
echo "JWT_SECRET_KEY=${JWT_SECRET_KEY}" >> .env

# Generate Meta webhook verification token
META_WEBHOOK_VERIFY_TOKEN=$(openssl rand -hex 32)
echo "META_WEBHOOK_VERIFY_TOKEN=${META_WEBHOOK_VERIFY_TOKEN}" >> .env
```

### 4. Configure Database

```bash
# PostgreSQL connection string format
DATABASE_URL=postgresql://viraly_user:secure_password@db-host:5432/viraly
```

### 5. Configure Redis

```bash
# Redis connection string
REDIS_URL=redis://:redis_password@redis-host:6379/0
```

### 6. Configure SSL Certificates

```bash
# Create SSL directory
mkdir -p ssl

# For Let's Encrypt certificates
sudo apt install certbot
sudo certbot certonly --standalone -d api.viraly.io -d viraly.io

# Copy certificates
sudo cp /etc/letsencrypt/live/api.viraly.io/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/api.viraly.io/privkey.pem ssl/key.pem

# Set permissions
chmod 600 ssl/key.pem
chmod 644 ssl/cert.pem
```

---

## Docker Deployment

### Quick Start

```bash
# Build and start all services
docker-compose up -d --build

# Check service status
docker-compose ps

# View logs
docker-compose logs -f app
```

### Production docker-compose.yml

Create a production-specific compose file:

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: viraly_app
    restart: always
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - FLASK_DEBUG=False
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - app_logs:/app/logs
      - app_uploads:/app/uploads
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M

  db:
    image: postgres:14-alpine
    container_name: viraly_db
    restart: always
    environment:
      POSTGRES_DB: viraly
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    ports:
      - "5432:5432"
    command: >
      postgres
      -c max_connections=200
      -c shared_buffers=512MB
      -c effective_cache_size=1GB
      -c maintenance_work_mem=128MB
      -c checkpoint_completion_target=0.9
      -c wal_buffers=16MB
      -c default_statistics_target=100
      -c random_page_cost=1.1
      -c effective_io_concurrency=200
      -c work_mem=4MB
      -c min_wal_size=1GB
      -c max_wal_size=4GB
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d viraly"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

  redis:
    image: redis:7-alpine
    container_name: viraly_redis
    restart: always
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --maxmemory 1gb
      --maxmemory-policy allkeys-lru
      --appendonly yes
      --appendfsync everysec
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G

  nginx:
    image: nginx:alpine
    container_name: viraly_nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - ./static:/app/static:ro
    depends_on:
      - app
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  app_logs:
  app_uploads:
  postgres_data:
  redis_data:

networks:
  default:
    driver: bridge
```

### Environment Variables for Production

```bash
# Application
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=<64-char-hex-string>
JWT_SECRET_KEY=<64-char-hex-string>

# Database
DB_HOST=db
DB_PORT=5432
DB_NAME=viraly
DB_USER=viraly_user
DB_PASSWORD=<strong-password>

# Redis
REDIS_URL=redis://:redis_password@redis:6379/0

# Mail
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=apikey
MAIL_PASSWORD=<sendgrid-api-key>
MAIL_DEFAULT_SENDER=noreply@viraly.io

# Security
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_DOMAIN=viraly.io
WTF_CSRF_ENABLED=True

# Rate Limiting
RATELIMIT_STORAGE_URL=redis://:redis_password@redis:6379/0
RATELIMIT_DEFAULT=100 per minute

# Cache
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://:redis_password@redis:6379/0

# Monitoring
SENTRY_DSN=https://key@sentry.io/project
NEWRELIC_LICENSE_KEY=<newrelic-license-key>

# SSL
SSL_CERT_PATH=/etc/nginx/ssl/cert.pem
SSL_KEY_PATH=/etc/nginx/ssl/key.pem
```

---

## Manual Deployment

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    postgresql-14 \
    redis-server \
    nginx \
    certbot \
    curl \
    git

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### 2. PostgreSQL Setup

```bash
# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE viraly;
CREATE USER viraly_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE viraly TO viraly_user;
\c viraly
GRANT ALL ON SCHEMA public TO viraly_user;
EOF

# Configure PostgreSQL for production
sudo tee /etc/postgresql/14/main/conf.d/viraly.conf << EOF
max_connections = 200
shared_buffers = 512MB
effective_cache_size = 1GB
maintenance_work_mem = 128MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
EOF

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### 3. Redis Setup

```bash
# Configure Redis
sudo tee /etc/redis/redis.conf << EOF
requirepass redis_password
maxmemory 1gb
maxmemory-policy allkeys-lru
appendonly yes
appendfsync everysec
EOF

# Restart Redis
sudo systemctl restart redis-server
```

### 4. Application Setup

```bash
# Create application user
sudo useradd -m -s /bin/bash viraly
sudo mkdir -p /app/viraly
sudo chown viraly:viraly /app/viraly

# Clone repository
cd /app/viraly
sudo -u viraly git clone https://github.com/your-org/viraly.git .
sudo -u viraly git checkout production

# Create virtual environment
sudo -u viraly python3.11 -m venv venv
sudo -u viraly source venv/bin/activate
sudo -u viraly pip install --upgrade pip
sudo -u viraly pip install -r requirements.txt

# Set permissions
sudo chown -R viraly:viraly /app/viraly
```

### 5. Gunicorn Setup

Create systemd service file `/etc/systemd/system/viraly.service`:

```ini
[Unit]
Description=Viraly Flask Application
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=notify
User=viraly
Group=viraly
WorkingDirectory=/app/viraly
Environment="PATH=/app/viraly/venv/bin"
Environment="FLASK_ENV=production"
EnvironmentFile=/app/viraly/.env
ExecStart=/app/viraly/venv/bin/gunicorn \
    --workers 4 \
    --worker-class sync \
    --worker-connections 1000 \
    --max-requests 10000 \
    --max-requests-jitter 1000 \
    --timeout 60 \
    --keep-alive 5 \
    --bind unix:/app/viraly/gunicorn.sock \
    --access-logfile /app/viraly/logs/access.log \
    --error-logfile /app/viraly/logs/error.log \
    --log-level info \
    wsgi:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 6. Nginx Setup

```bash
# Copy nginx configuration
sudo cp /app/viraly/nginx.conf /etc/nginx/sites-available/viraly
sudo ln -s /etc/nginx/sites-available/viraly /etc/nginx/sites-enabled/

# Test and reload Nginx
sudo nginx -t
sudo systemctl reload nginx

# Enable and start services
sudo systemctl enable viraly postgresql redis-server nginx
sudo systemctl start viraly
```

---

## Post-Deployment

### 1. Run Database Migrations

```bash
# Development
flask db upgrade

# Production (with backup)
flask db upgrade --backup

# Check migration status
flask db current
flask db history
```

### 2. Create Admin User

```bash
# Create initial admin user
flask admin create-admin \
    --email admin@viraly.io \
    --password "SecurePassword123!" \
    --name "Admin User"
```

### 3. Verify Health Endpoints

```bash
# Health check
curl https://api.viraly.io/health
# Response: {"status": "healthy", "timestamp": "2024-01-15T10:30:00Z"}

# Readiness check
curl https://api.viraly.io/ready
# Response: {"status": "ready", "services": {"database": "connected", "redis": "connected"}}
```

### 4. Configure Monitoring

Set up Sentry error tracking:
```bash
# Install Sentry SDK is already in requirements.txt
# Configure via SENTRY_DSN environment variable
```

Set up New Relic APM:
```bash
# Add to gunicorn command
--pythonopt "-m newrelic.agent"
```

---

## Container Orchestration

### Kubernetes Deployment

Create `k8s/namespace.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: viraly
  labels:
    name: viraly
```

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: viraly-app
  namespace: viraly
spec:
  replicas: 3
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
        env:
        - name: FLASK_ENV
          value: "production"
        envFrom:
        - secretRef:
            name: viraly-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
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

Create `k8s/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: viraly-app
  namespace: viraly
spec:
  selector:
    app: viraly-app
  ports:
  - port: 80
    targetPort: 5000
  type: ClusterIP
```

Create `k8s/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: viraly-ingress
  namespace: viraly
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.viraly.io
    secretName: viraly-tls
  rules:
  - host: api.viraly.io
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: viraly-app
            port:
              number: 80
```

### Helm Chart

See [Scaling Guide](SCALING_GUIDE.md) for detailed Helm chart configuration.

---

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check PostgreSQL status
   sudo systemctl status postgresql
   
   # Test connection
   psql -h localhost -U viraly_user -d viraly
   
   # Check logs
   tail -f /var/log/postgresql/postgresql-14-main.log
   ```

2. **Redis Connection Failed**
   ```bash
   # Check Redis status
   sudo systemctl status redis-server
   
   # Test connection
   redis-cli -a redis_password ping
   
   # Check logs
   tail -f /var/log/redis/redis-server.log
   ```

3. **Application Won't Start**
   ```bash
   # Check Gunicorn status
   sudo systemctl status viraly
   
   # View logs
   sudo journalctl -u viraly -f
   
   # Check socket
   ls -la /app/viraly/gunicorn.sock
   ```

4. **SSL Certificate Issues**
   ```bash
   # Renew certificates
   sudo certbot renew
   
   # Test Nginx configuration
   sudo nginx -t
   
   # Reload Nginx
   sudo systemctl reload nginx
   ```

---

## Updates and Maintenance

### Applying Updates

```bash
# Pull latest changes
git pull origin production

# Rebuild application
docker-compose build app

# Restart services
docker-compose up -d

# Run pending migrations
docker-compose exec app flask db upgrade
```

### Rolling Back

```bash
# View available versions
docker images viraly/app

# Rollback to previous version
docker-compose pull viraly/app:previous
docker-compose up -d

# Rollback database migration
docker-compose exec app flask db downgrade -1
```

---

## Support

For deployment support, contact:
- Email: support@viraly.io
- Documentation: https://docs.viraly.io
