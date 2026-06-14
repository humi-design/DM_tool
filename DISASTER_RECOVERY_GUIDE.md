# Disaster Recovery Guide

Comprehensive guide for disaster recovery procedures for the Viraly platform.

## Table of Contents

1. [Recovery Objectives](#recovery-objectives)
2. [Backup Strategy](#backup-strategy)
3. [Backup Procedures](#backup-procedures)
4. [Restore Procedures](#restore-procedures)
5. [Disaster Scenarios](#disaster-scenarios)
6. [Failover Procedures](#failover-procedures)
7. [Post-Recovery](#post-recovery)
8. [Testing](#testing)

---

## Recovery Objectives

### Recovery Point Objective (RPO)

| Data Type | RPO | Description |
|-----------|-----|-------------|
| User data | 1 hour | Maximum acceptable data loss |
| Transaction data | 1 hour | Financial and business transactions |
| Configuration | 24 hours | System configuration |
| Media files | 24 hours | Uploaded images and documents |

### Recovery Time Objective (RTO)

| Severity | RTO | Description |
|----------|-----|-------------|
| Critical | 1 hour | Complete system outage |
| High | 4 hours | Major feature unavailable |
| Medium | 24 hours | Minor features affected |
| Low | 72 hours | Non-critical issues |

### Backup Retention

| Backup Type | Retention | Storage Location |
|-------------|-----------|------------------|
| Hourly | 24 hours | Local + Cloud |
| Daily | 30 days | Cloud |
| Weekly | 12 weeks | Cloud (Glacier) |
| Monthly | 12 months | Cloud (Glacier) |
| Yearly | 7 years | Cloud (Glacier Deep Archive) |

---

## Backup Strategy

### Backup Components

1. **Database Backup**
   - Full PostgreSQL dump (daily)
   - WAL archiving (continuous)
   - Point-in-time recovery capability

2. **Application Backup**
   - Source code (Git)
   - Configuration files
   - Environment variables (encrypted)
   - Docker images

3. **File Backup**
   - User uploads
   - Static assets
   - SSL certificates

4. **State Backup**
   - Redis data (if persistent)
   - Session data
   - Cache data

### Backup Architecture

```
┌─────────────────┐
│   PostgreSQL    │
│   (Primary)     │
└────────┬────────┘
         │ Continuous WAL
         ▼
┌─────────────────┐
│   PostgreSQL    │
│   (Replica)     │
└────────┬────────┘
         │ Daily Full Backup
         ▼
┌─────────────────┐
│   S3 Bucket     │
│   (viraly-backup)│
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐  ┌────────┐
│Standard│  │ Glacier │
│ IA     │  │Archive │
└───────┘  └────────┘
```

---

## Backup Procedures

### Automated Database Backup

Create the backup script `/opt/viraly/backup.sh`:

```bash
#!/bin/bash
set -e

# Configuration
BACKUP_DIR="/backups"
DB_NAME="viraly"
DB_USER="viraly_user"
S3_BUCKET="s3://viraly-backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# PostgreSQL backup
pg_dump -Fc -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_DIR/pg_backup_$DATE.sql.gz"

# Upload to S3
aws s3 cp "$BACKUP_DIR/pg_backup_$DATE.sql.gz" "$S3_BUCKET/database/daily/"

# Create point-in-time backup marker
aws s3api put-object --bucket viraly-backups --key "database/pit/$DATE" --body /dev/null

# Cleanup old backups
find "$BACKUP_DIR" -name "pg_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
aws s3 ls "$S3_BUCKET/database/daily/" | while read -r line; do
    backup_date=$(echo "$line" | awk '{print $4}' | sed 's/pg_backup_//;s/.sql.gz//')
    if [ $(date -d "$backup_date" +%s) -lt $(date -d "-$RETENTION_DAYS days" +%s) ]; then
        aws s3 rm "$S3_BUCKET/database/daily/pg_backup_$backup_date.sql.gz"
    fi
done

# Upload logs
echo "Backup completed at $(date)" >> /var/log/viraly-backup.log
```

Set up cron job:

```bash
# Add to crontab
sudo crontab -e

# Daily backup at 2 AM
0 2 * * * /opt/viraly/backup.sh >> /var/log/viraly-backup-cron.log 2>&1

# Hourly incremental at :15 past
15 * * * * /opt/viraly/incremental_backup.sh >> /var/log/viraly-backup-cron.log 2>&1
```

### Docker Volume Backup

```bash
#!/bin/bash
# Backup Docker volumes

docker run --rm \
    -v viraly_postgres_data:/data \
    -v /backups:/backup \
    alpine tar czf /backup/postgres_volume_$(date +%Y%m%d).tar.gz -C /data .

docker run --rm \
    -v viraly_redis_data:/data \
    -v /backups:/backup \
    alpine tar czf /backup/redis_volume_$(date +%Y%m%d).tar.gz -C /data .
```

### Application Configuration Backup

```bash
#!/bin/bash
# Backup application configuration

CONFIG_DIR="/app/viraly"
BACKUP_DIR="/backups/config"
DATE=$(date +%Y%m%d_%H%M%S)

# Encrypt and backup .env file
gpg --encrypt --recipient backup@viraly.io "$CONFIG_DIR/.env"
cp "$CONFIG_DIR/.env.gpg" "$BACKUP_DIR/env_$DATE.gpg"

# Backup nginx configuration
tar czf "$BACKUP_DIR/nginx_$DATE.tar.gz" /etc/nginx/

# Backup systemd services
cp /etc/systemd/system/viraly.service "$BACKUP_DIR/viraly.service.$DATE"
```

---

## Restore Procedures

### Database Restore

#### Full Restore

```bash
#!/bin/bash
# Full database restore

# Stop the application
docker-compose stop app

# Drop and recreate database
docker-compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS viraly;"
docker-compose exec db psql -U postgres -c "CREATE DATABASE viraly;"

# Restore from backup
gunzip < /backups/pg_backup_20240115_020000.sql.gz | \
    docker-compose exec -T db psql -U postgres viraly

# Verify restore
docker-compose exec db psql -U postgres viraly -c "SELECT COUNT(*) FROM users;"

# Restart application
docker-compose start app
```

#### Point-in-Time Recovery

```bash
#!/bin/bash
# Point-in-time recovery

PIT_TIMESTAMP="2024-01-15 14:30:00"

# Stop application
docker-compose stop app

# Create recovery.conf
docker-compose exec db bash -c "cat > /var/lib/postgresql/data/recovery.conf << EOF
restore_command = 'cp /var/lib/postgresql/wal/%f %p'
recovery_target_time = '$PIT_TIMESTAMP'
recovery_target_action = 'promote'
EOF"

# Restart PostgreSQL
docker-compose restart db

# Monitor recovery
docker-compose exec db bash -c "tail -f /var/lib/postgresql/data/log/*.log"

# Verify data
docker-compose exec db psql -U postgres viraly -c "SELECT * FROM audit_logs WHERE created_at < '$PIT_TIMESTAMP' LIMIT 10;"
```

### Docker Volume Restore

```bash
#!/bin/bash
# Restore Docker volumes

# Stop containers
docker-compose down

# Restore PostgreSQL volume
docker volume rm viraly_postgres_data
docker volume create viraly_postgres_data

docker run --rm \
    -v viraly_postgres_data:/data \
    -v /backups:/backup \
    alpine tar xzf /backup/postgres_volume_20240115.tar.gz -C /data

# Restore Redis volume
docker volume rm viraly_redis_data
docker volume create viraly_redis_data

docker run --rm \
    -v viraly_redis_data:/data \
    -v /backups:/backup \
    alpine tar xzf /backup/redis_volume_20240115.tar.gz -C /data

# Start containers
docker-compose up -d
```

### Configuration Restore

```bash
#!/bin/bash
# Restore configuration from encrypted backup

# Decrypt and restore .env file
gpg --decrypt /backups/config/env_20240115.gpg > /app/viraly/.env

# Restore nginx configuration
tar xzf /backups/config/nginx_20240115.tar.gz -C /

# Reload nginx
systemctl reload nginx

# Restore systemd service
cp /backups/config/viraly.service.20240115 /etc/systemd/system/viraly.service
systemctl daemon-reload
systemctl restart viraly
```

---

## Disaster Scenarios

### Database Failure

**Symptoms:**
- Application returns 500 errors
- Database connection refused
- Corrupted data

**Response:**

1. **Immediate Assessment**
   ```bash
   # Check database status
   docker-compose ps db
   docker-compose logs db --tail=50
   
   # Check disk space
   df -h
   docker-compose exec db df -h
   
   # Check connections
   docker-compose exec db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
   ```

2. **If PostgreSQL is running but corrupted:**
   ```bash
   # Try to repair
   docker-compose exec db pg_ctl stop -m fast
   docker-compose exec db pg_resetwal /var/lib/postgresql/data
   docker-compose exec db pg_ctl start
   
   # If repair fails, restore from backup
   ```

3. **If PostgreSQL won't start:**
   ```bash
   # Restore from latest backup
   LATEST_BACKUP=$(ls -t /backups/pg_backup_*.sql.gz | head -1)
   gunzip < "$LATEST_BACKUP" | docker-compose exec -T db psql -U postgres viraly
   ```

### Redis Failure

**Symptoms:**
- Rate limiting not working
- Cache misses
- Session errors

**Response:**

1. **Check Redis status**
   ```bash
   docker-compose logs redis
   docker-compose exec redis redis-cli -a "$REDIS_PASSWORD" ping
   ```

2. **If Redis is corrupted:**
   ```bash
   # Clear Redis and restart
   docker-compose stop redis
   docker volume rm viraly_redis_data
   docker volume create viraly_redis_data
   docker-compose up -d redis
   
   # Note: Cache will be rebuilt automatically
   ```

### Application Failure

**Symptoms:**
- Application pods crashing
- Memory exhaustion
- Worker failures

**Response:**

1. **Check application logs**
   ```bash
   docker-compose logs app --tail=100
   docker-compose exec app ps aux
   ```

2. **Restart application**
   ```bash
   docker-compose restart app
   
   # If still failing, check resources
   docker-compose exec app free -h
   docker-compose exec app df -h
   ```

3. **If deployment is corrupted:**
   ```bash
   # Rebuild and redeploy
   docker-compose down
   docker-compose build --no-cache app
   docker-compose up -d
   ```

### Data Center Failure

**Symptoms:**
- All services unavailable
- Network connectivity lost
- Hardware failure

**Response:**

1. **Activate disaster recovery site**
   ```bash
   # Deploy to DR environment
   docker-compose -f docker-compose.dr.yml up -d
   
   # Restore latest backup
   LATEST_BACKUP=$(aws s3 ls s3://viraly-backups/database/daily/ | sort | tail -1 | awk '{print $4}')
   aws s3 cp "s3://viraly-backups/database/daily/$LATEST_BACKUP" /tmp/
   gunzip < /tmp/$LATEST_BACKUP | docker-compose exec -T db psql -U postgres viraly
   ```

2. **Update DNS**
   ```bash
   # Switch DNS to DR site
   aws route53 change-resource-record-sets \
       --hosted-zone-id Z1234567890ABC \
       --change-batch file://dns-failover.json
   ```

### Ransomware Attack

**Symptoms:**
- Files encrypted
- Ransom demand displayed
- Unusual file extensions

**Response:**

1. **ISOLATE IMMEDIATELY**
   ```bash
   # Stop all containers
   docker-compose down
   
   # Disconnect from network
   # (Manual action required)
   ```

2. **Forensic Analysis**
   ```bash
   # Preserve evidence
   tar czf forensics_$(date +%Y%m%d).tar.gz /app/viraly
   aws s3 cp forensics_$(date +%Y%m%d).tar.gz s3://viraly-forensics/
   ```

3. **Restore from Clean Backup**
   ```bash
   # Use backup from before attack
   LAST_CLEAN_BACKUP="pg_backup_20240110_020000.sql.gz"
   
   # Rebuild infrastructure
   docker-compose up -d db redis
   
   # Restore database
   gunzip < /backups/$LAST_CLEAN_BACKUP | docker-compose exec -T db psql -U postgres viraly
   
   # Rebuild and restart application
   docker-compose up -d
   ```

---

## Failover Procedures

### Database Failover (PostgreSQL Streaming Replication)

**Setup:**
```bash
# Primary database configuration
docker-compose exec db bash -c "cat >> /var/lib/postgresql/data/postgresql.conf << EOF
wal_level = replica
max_wal_senders = 3
wal_keep_size = 1GB
hot_standby = on
EOF"

# Create replication user
docker-compose exec db psql -U postgres -c "CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'replication_password';"

# Create replication slot
docker-compose exec db psql -U postgres -c "SELECT pg_create_physical_replication_slot('replica_slot');"
```

**Manual Failover:**
```bash
# On replica server
docker-compose exec db pg_ctl promote

# Update application to use new primary
# (Update DATABASE_URL environment variable)
docker-compose up -d
```

### Application Failover

**Using Docker Swarm:**
```bash
# Deploy to swarm
docker stack deploy -c docker-compose.swarm.yml viraly

# Scale services
docker service scale viraly_app=3
docker service scale viraly_worker=2
```

---

## Post-Recovery

### Verification Checklist

- [ ] All services running
- [ ] Health checks passing
- [ ] Database accessible
- [ ] Users can log in
- [ ] Key features functional
- [ ] No error spike in Sentry
- [ ] Performance normal

### Communication

1. **Internal Notification**
   ```markdown
   ## Incident Report: [Date]
   
   **Severity:** [Critical/High/Medium/Low]
   **Duration:** [X hours Y minutes]
   **Impact:** [Description]
   **Root Cause:** [Description]
   **Resolution:** [Steps taken]
   **Action Items:** [Preventive measures]
   ```

2. **Customer Communication**
   ```markdown
   ## Service Update
   
   We experienced a service disruption on [date] from [time] to [time].
   The issue has been resolved and all systems are now operating normally.
   
   We apologize for any inconvenience this may have caused.
   ```

### Post-Incident Review

| Item | Description |
|------|-------------|
| Timeline | Detailed incident timeline |
| Impact | User impact analysis |
| Root Cause | Technical root cause |
| Lessons Learned | What we learned |
| Action Items | Preventive actions with owners |

---

## Testing

### Backup Verification

```bash
#!/bin/bash
# Verify backup integrity

BACKUP_FILE="/backups/pg_backup_latest.sql.gz"

# Check if backup exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found"
    exit 1
fi

# Verify gzip integrity
if ! gzip -t "$BACKUP_FILE"; then
    echo "ERROR: Backup file is corrupted"
    exit 1
fi

# Verify PostgreSQL format
gunzip < "$BACKUP_FILE" | head -1 | grep -q "PGDMP" || {
    echo "ERROR: Invalid backup format"
    exit 1
}

# Test restore to temporary database
gunzip < "$BACKUP_FILE" | \
    docker-compose exec -T db psql -U postgres -c "CREATE DATABASE viraly_test;"
gunzip < "$BACKUP_FILE" | \
    docker-compose exec -T db psql -U postgres viraly_test

echo "Backup verification successful"
```

### Restore Testing Schedule

| Test | Frequency | Owner |
|------|-----------|-------|
| Backup integrity | Daily | Automated |
| Restore to test env | Weekly | DevOps |
| Full DR drill | Quarterly | DevOps + Security |
| Chaos engineering | Monthly | Platform Team |

### Chaos Engineering

Use tools like Chaos Monkey or Litmus to simulate failures:

```bash
# Simulate database failure
chaos-cli database-failure --duration=5m

# Simulate network partition
chaos-cli network-partition --service=app --duration=5m

# Simulate resource exhaustion
chaos-cli resource-exhaustion --service=app --memory=true
```

---

## Emergency Contacts

| Role | Name | Phone | Email |
|------|------|-------|-------|
| Primary On-Call | | | |
| Secondary On-Call | | | |
| DevOps Lead | | | |
| CTO | | | |
| AWS Support | | | 1-866-726-3390 |

---

## Documentation Updates

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-01-15 | DevOps | Initial version |
