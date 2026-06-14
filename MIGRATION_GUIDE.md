# Migration Guide

Comprehensive guide for database migrations and version upgrades.

## Table of Contents

1. [Database Migrations](#database-migrations)
2. [Migration Workflow](#migration-workflow)
3. [Creating Migrations](#creating-migrations)
4. [Running Migrations](#running-migrations)
5. [Rollback Procedures](#rollback-procedures)
6. [Data Migrations](#data-migrations)
7. [Schema Changes](#schema-changes)
8. [Version Upgrades](#version-upgrades)

---

## Database Migrations

### Overview

Viraly uses Alembic for database migrations with SQLAlchemy as the ORM.

### Migration Files Location

```
alembic/
├── versions/
│   ├── 001_initial_schema.py
│   ├── 002_add_users_table.py
│   └── ...
├── env.py
└── script.py.mako
```

### Current Schema

| Table | Description |
|-------|-------------|
| users | User accounts |
| organizations | Multi-tenant organizations |
| businesses | Business profiles |
| instagram_accounts | Connected Instagram accounts |
| dm_threads | DM conversations |
| dm_messages | Individual messages |
| comments | Post comments |
| leads | Lead records |
| audit_logs | Action audit trail |
| subscriptions | Billing subscriptions |

---

## Migration Workflow

### Standard Workflow

1. **Create Migration** - Auto-generate or write manually
2. **Test in Development** - Verify migration works locally
3. **Test in Staging** - Apply to staging environment
4. **Apply to Production** - During maintenance window
5. **Monitor** - Watch for errors post-migration

### Pre-Migration Checklist

- [ ] Migration tested in local environment
- [ ] Migration tested in staging environment
- [ ] Database backup created
- [ ] Rollback procedure documented
- [ ] Migration approved by team
- [ ] Maintenance window scheduled
- [ ] On-call engineer notified

---

## Creating Migrations

### Auto-Generate Migration

```bash
# Detect model changes and generate migration
flask db migrate -m "Add instagram_business_id to businesses table"
```

### Manual Migration

```python
# alembic/versions/20240115_123456_add_instagram_business_id.py
"""Add instagram_business_id to businesses table

Revision ID: abc123def456
Revises: previous_revision_id
Create Date: 2024-01-15 12:34:56.789012

"""
from alembic import op
import sqlalchemy as sa

revision = 'abc123def456'
down_revision = 'previous_revision_id'
branch_labels = None
depends_on = None


def upgrade():
    """Add instagram_business_id column."""
    op.add_column(
        'businesses',
        sa.Column('instagram_business_id', sa.String(100), nullable=True)
    )
    
    op.create_index(
        'ix_businesses_instagram_business_id',
        'businesses',
        ['instagram_business_id'],
        unique=False
    )


def downgrade():
    """Remove instagram_business_id column."""
    op.drop_index('ix_businesses_instagram_business_id', 'businesses')
    op.drop_column('businesses', 'instagram_business_id')
```

### Data Migration

```python
# alembic/versions/20240115_234567_migrate_lead_scores.py
"""Migrate lead scores to new format

Revision ID: def789ghi012
Revises: abc123def456
Create Date: 2024-01-15 23:45:67.890123

"""
from alembic import op
import sqlalchemy as sa

revision = 'def789ghi012'
down_revision = 'abc123def456'
branch_labels = None
depends_on = None


def upgrade():
    """Migrate lead scores to new 0-100 scale."""
    op.add_column(
        'leads',
        sa.Column('score_normalized', sa.Integer(), nullable=True)
    )
    
    op.execute("""
        UPDATE leads 
        SET score_normalized = score * 10 
        WHERE score IS NOT NULL
    """)
    
    op.alter_column('leads', 'score_normalized', nullable=False)
    op.drop_column('leads', 'score')


def downgrade():
    """Rollback lead score migration."""
    op.add_column(
        'leads',
        sa.Column('score', sa.Float(), nullable=True)
    )
    
    op.execute("""
        UPDATE leads 
        SET score = score_normalized / 10.0 
        WHERE score_normalized IS NOT NULL
    """)
    
    op.alter_column('leads', 'score', nullable=False)
    op.drop_column('leads', 'score_normalized')
```

### Complex Schema Changes

```python
# alembic/versions/20240115_345678_create_ai_processing_logs.py
"""Create AI processing logs table

Revision ID: ghi345jkl678
Revises: def789ghi012
Create Date: 2024-01-15 34:56:78.901234

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'ghi345jkl678'
down_revision = 'def789ghi012'
branch_labels = None
depends_on = None


def upgrade():
    """Create ai_processing_logs table."""
    op.create_table(
        'ai_processing_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('organization_id', sa.String(36), nullable=True),
        sa.Column('instagram_account_id', sa.String(36), nullable=True),
        sa.Column('content_type', sa.String(50), nullable=False),
        sa.Column('content_id', sa.String(36), nullable=True),
        sa.Column('ai_model', sa.String(100), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('response_data', postgresql.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['instagram_account_id'], ['instagram_accounts.id'], ondelete='SET NULL'),
    )
    
    op.create_index('ix_ai_processing_logs_user_id', 'ai_processing_logs', ['user_id'])
    op.create_index('ix_ai_processing_logs_created_at', 'ai_processing_logs', ['created_at'])


def downgrade():
    """Drop ai_processing_logs table."""
    op.drop_index('ix_ai_processing_logs_created_at', 'ai_processing_logs')
    op.drop_index('ix_ai_processing_logs_user_id', 'ai_processing_logs')
    op.drop_table('ai_processing_logs')
```

---

## Running Migrations

### Development Environment

```bash
# Check current migration status
flask db current

# Show migration history
flask db history

# Generate new migration
flask db migrate -m "Description of changes"

# Apply pending migrations
flask db upgrade

# Apply specific migration
flask db upgrade abc123def456

# Show pending migrations
flask db heads
```

### Staging/Production Environment

```bash
# 1. Create database backup
pg_dump -Fc viraly > backup_$(date +%Y%m%d_%H%M%S).dump

# 2. Verify backup
pg_restore --list backup_20240115_020000.dump | head -20

# 3. Apply migrations
flask db upgrade

# 4. Verify migration
flask db current
flask db history

# 5. Check application health
curl https://api.viraly.io/health
```

### Docker Deployment

```bash
# Build and deploy
docker-compose build app
docker-compose up -d

# Run migrations in container
docker-compose exec app flask db upgrade

# Check migration status
docker-compose exec app flask db current
```

### Kubernetes Deployment

```yaml
# k8s/migration-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: viraly-migration
  namespace: viraly
spec:
  template:
    spec:
      containers:
      - name: migration
        image: viraly/app:latest
        command: ["flask", "db", "upgrade"]
        env:
        - name: FLASK_ENV
          value: "production"
        envFrom:
        - secretRef:
            name: viraly-secrets
      restartPolicy: OnFailure
```

---

## Rollback Procedures

### Application Rollback

```bash
# Docker
docker-compose pull viraly/app:previous-version
docker-compose up -d app

# Kubernetes
kubectl rollout undo deployment/viraly-app -n viraly
```

### Database Rollback

```bash
# Rollback one migration
flask db downgrade

# Rollback to specific revision
flask db downgrade abc123def456

# Rollback all migrations
flask db downgrade base
```

### Emergency Rollback Script

```bash
#!/bin/bash
# emergency_rollback.sh

set -e

BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

echo "Starting emergency rollback..."

# Stop application
docker-compose stop app

# Restore database
echo "Restoring database from $BACKUP_FILE..."
docker-compose exec -T db pg_restore \
    --clean \
    --if-exists \
    --dbname=viraly \
    --username=postgres \
    "$BACKUP_FILE"

# Restart application
docker-compose start app

# Verify
echo "Verifying restoration..."
sleep 5
curl -f https://api.viraly.io/health || echo "Health check failed"

echo "Rollback complete"
```

---

## Data Migrations

### Large Table Migrations

For tables with millions of rows, use batch processing:

```python
BATCH_SIZE = 10000

def upgrade():
    """Archive audit logs older than 2 years."""
    connection = op.get_bind()
    
    while True:
        result = connection.execute(
            sa.text("""
                DELETE FROM audit_logs 
                WHERE created_at < NOW() - INTERVAL '2 years'
                AND id IN (
                    SELECT id FROM audit_logs 
                    WHERE created_at < NOW() - INTERVAL '2 years'
                    LIMIT :batch_size
                )
            """),
            {"batch_size": BATCH_SIZE}
        )
        
        if result.rowcount == 0:
            break
            
        print(f"Deleted {result.rowcount} old audit logs")
    
    connection.execute(sa.text("ANALYZE audit_logs"))
```

### Zero-Downtime Migration Pattern

```python
def upgrade():
    """Add nullable column first (Phase 1)."""
    op.add_column(
        'users',
        sa.Column('preferences', sa.JSON(), nullable=True)
    )
```

Application code handles null values during the transition period.

---

## Schema Changes

### Adding a New Table

```python
def upgrade():
    """Create notifications table."""
    op.create_table(
        'notifications',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('data', postgresql.JSON(), nullable=True),
        sa.Column('read', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('read_at', sa.DateTime(), nullable=True),
    )
    
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])


def downgrade():
    op.drop_table('notifications')
```

### Adding a Column

```python
def upgrade():
    op.add_column('users', sa.Column('avatar_url', sa.String(500), nullable=True))
    op.create_index('ix_users_avatar_url', 'users', ['avatar_url'])


def downgrade():
    op.drop_index('ix_users_avatar_url', 'users')
    op.drop_column('users', 'avatar_url')
```

### Renaming a Column

```python
def upgrade():
    """Rename old_name to new_name."""
    op.add_column('table_name', sa.Column('new_name', sa.String(100)))
    op.execute("UPDATE table_name SET new_name = old_name")
    op.drop_column('table_name', 'old_name')


def downgrade():
    """Rename new_name back to old_name."""
    op.add_column('table_name', sa.Column('old_name', sa.String(100)))
    op.execute("UPDATE table_name SET old_name = new_name")
    op.drop_column('table_name', 'new_name')
```

### Adding an Index

```python
def upgrade():
    """Add composite index for common query patterns."""
    op.create_index(
        'ix_audit_logs_user_action_created',
        'audit_logs',
        ['user_id', 'action', 'created_at']
    )


def downgrade():
    op.drop_index('ix_audit_logs_user_action_created', 'audit_logs')
```

---

## Version Upgrades

### Python Version Upgrade

```bash
# 1. Update Dockerfile
# FROM python:3.11-slim -> FROM python:3.12-slim

# 2. Update base image
docker-compose build --no-cache app

# 3. Test in staging
docker-compose up -d
flask db upgrade
pytest tests/ -v

# 4. Deploy to production
docker-compose up -d
docker-compose exec app flask db upgrade
```

### PostgreSQL Version Upgrade

```bash
# 1. Create backup
pg_dump -Fc viraly > pre_upgrade_backup.dump

# 2. Stop application
docker-compose stop app

# 3. Upgrade PostgreSQL container
# Update docker-compose.yml: postgres:14-alpine -> postgres:15-alpine

# 4. Start new database
docker-compose up -d db

# 5. Verify upgrade
docker-compose exec db psql --version

# 6. Run migrations
flask db upgrade

# 7. Start application
docker-compose up -d app
```

### Flask Version Upgrade

```bash
# 1. Update requirements.txt
# Flask==3.0.0 -> Flask==3.1.0

# 2. Update dependencies
pip install -r requirements.txt

# 3. Run tests
pytest tests/ -v

# 4. Deploy
docker-compose build app
docker-compose up -d
```

---

## Migration Best Practices

### Do's

- [ ] Test migrations locally first
- [ ] Create backups before applying migrations
- [ ] Use batch processing for large tables
- [ ] Make columns nullable before adding constraints
- [ ] Document migration purpose and impact
- [ ] Monitor migration progress in production
- [ ] Have rollback plan ready
- [ ] Test rollback procedure

### Don'ts

- [ ] Don't modify existing migration files
- [ ] Don't use `ALTER TABLE` directly in production
- [ ] Don't drop columns without verification
- [ ] Don't run migrations during peak hours
- [ ] Don't ignore migration failures
- [ ] Don't skip testing in staging

### Performance Considerations

| Operation | Impact | Mitigation |
|-----------|--------|------------|
| Add column | Low | Safe operation |
| Add index | Medium | Use CONCURRENTLY |
| Drop column | Medium | Remove in separate migration |
| Add NOT NULL | High | Migrate data first |
| Change type | High | Use temp column |
| Drop table | High | Archive data first |
