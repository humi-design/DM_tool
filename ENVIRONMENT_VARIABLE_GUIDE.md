# Environment Variable Guide

Complete reference for all environment variables used in the Viraly platform.

## Table of Contents

1. [Application](#application)
2. [Database](#database)
3. [Redis](#redis)
4. [Security](#security)
5. [Authentication](#authentication)
6. [Session](#session)
7. [Mail](#mail)
8. [OAuth Providers](#oauth-providers)
9. [Meta/Instagram](#metainstagram)
10. [OTP Configuration](#otp-configuration)
11. [Billing](#billing)
12. [AWS S3](#aws-s3)
13. [Monitoring](#monitoring)
14. [Logging](#logging)
15. [Cache](#cache)
16. [Rate Limiting](#rate-limiting)
17. [File Upload](#file-upload)
18. [AI Provider](#ai-provider)

---

## Application

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLASK_ENV` | Yes | `development` | Application environment: `development`, `production`, `testing` |
| `FLASK_APP` | Yes | `app.py` | Flask application module |
| `FLASK_DEBUG` | No | `False` | Enable debug mode (never in production) |
| `SECRET_KEY` | Yes | - | Flask secret key for session signing (min 32 bytes) |
| `JWT_SECRET_KEY` | Yes | - | JWT signing key (min 32 bytes) |

### Example

```bash
FLASK_ENV=production
FLASK_APP=app.py
FLASK_DEBUG=False
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
JWT_SECRET_KEY=z9y8x7w6v5u4t3s2r1q0p9o8n7m6l5k4j3i2h1g0f9e8d7c6b5a4z3y2x1w0v9u8
```

---

## Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `DB_HOST` | No | `localhost` | Database host |
| `DB_PORT` | No | `5432` | Database port |
| `DB_NAME` | No | `viraly` | Database name |
| `DB_USER` | No | `postgres` | Database username |
| `DB_PASSWORD` | No | - | Database password |

### Connection String Format

```
postgresql://username:password@host:port/database
```

### Example

```bash
# Full connection string
DATABASE_URL=postgresql://viraly_user:secure_password@db.example.com:5432/viraly

# Individual components
DB_HOST=db.example.com
DB_PORT=5432
DB_NAME=viraly
DB_USER=viraly_user
DB_PASSWORD=secure_password
```

### PostgreSQL Connection Pool Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SQLALCHEMY_POOL_SIZE` | No | `10` | Connection pool size |
| `SQLALCHEMY_POOL_RECYCLE` | No | `3600` | Pool recycle time in seconds |
| `SQLALCHEMY_POOL_PRE_PING` | No | `True` | Enable connection health check |

---

## Redis

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Yes | - | Redis connection string |
| `REDIS_PASSWORD` | No | - | Redis password |
| `REDIS_DB` | No | `0` | Redis database number |

### Connection String Format

```
redis://[:password@]host:port/db
```

### Example

```bash
# With password
REDIS_URL=redis://:redis_password@redis.example.com:6379/0

# Without password
REDIS_URL=redis://redis.example.com:6379/0
```

---

## Security

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WTF_CSRF_ENABLED` | No | `True` | Enable CSRF protection |
| `WTF_CSRF_TIME_LIMIT` | No | `3600` | CSRF token validity in seconds |
| `PASSWORD_BCRYPT_ROUNDS` | No | `12` | Bcrypt cost factor (14 in production) |
| `PASSWORD_ARGON2_MEMORY_COST` | No | `65536` | Argon2 memory cost |
| `PASSWORD_ARGON2_TIME_COST` | No | `3` | Argon2 time cost |
| `PASSWORD_ARGON2_PARALLELISM` | No | `4` | Argon2 parallelism |

### Example

```bash
# Development
WTF_CSRF_ENABLED=False
PASSWORD_BCRYPT_ROUNDS=12

# Production
WTF_CSRF_ENABLED=True
PASSWORD_BCRYPT_ROUNDS=14
PASSWORD_ARGON2_MEMORY_COST=65536
PASSWORD_ARGON2_TIME_COST=4
PASSWORD_ARGON2_PARALLELISM=4
```

---

## Authentication

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_ACCESS_TOKEN_EXPIRES` | No | `15` | Access token expiry in minutes |
| `JWT_REFRESH_TOKEN_EXPIRES` | No | `30` | Refresh token expiry in days |
| `JWT_TOKEN_LOCATION` | No | `headers` | JWT token location |
| `JWT_HEADER_NAME` | No | `Authorization` | JWT header name |
| `JWT_HEADER_TYPE` | No | `Bearer` | JWT header type |

### Example

```bash
JWT_ACCESS_TOKEN_EXPIRES=15
JWT_REFRESH_TOKEN_EXPIRES=30
JWT_TOKEN_LOCATION=headers
JWT_HEADER_NAME=Authorization
JWT_HEADER_TYPE=Bearer
```

---

## Session

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SESSION_COOKIE_SECURE` | No | `True` | Require HTTPS for cookies |
| `SESSION_COOKIE_HTTPONLY` | No | `True` | Prevent JavaScript access |
| `SESSION_COOKIE_SAMESITE` | No | `Lax` | SameSite cookie policy |
| `SESSION_COOKIE_DOMAIN` | No | - | Cookie domain |
| `PERMANENT_SESSION_LIFETIME` | No | `7` | Session lifetime in days |

### Example

```bash
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
SESSION_COOKIE_DOMAIN=viraly.io
PERMANENT_SESSION_LIFETIME=7
```

---

## Mail

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MAIL_SERVER` | Yes | `smtp.gmail.com` | SMTP server hostname |
| `MAIL_PORT` | No | `587` | SMTP port |
| `MAIL_USE_TLS` | No | `True` | Use TLS encryption |
| `MAIL_USE_SSL` | No | `False` | Use SSL encryption |
| `MAIL_USERNAME` | Yes | - | SMTP username |
| `MAIL_PASSWORD` | Yes | - | SMTP password |
| `MAIL_DEFAULT_SENDER` | Yes | - | Default from address |
| `MAIL_SUPPRESS_SEND` | No | `False` | Suppress email sending (testing) |

### Common SMTP Providers

**Gmail:**
```bash
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
```

**SendGrid:**
```bash
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=apikey
MAIL_PASSWORD=<sendgrid-api-key>
```

**AWS SES:**
```bash
MAIL_SERVER=email-smtp.us-east-1.amazonaws.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=<ses-smtp-username>
MAIL_PASSWORD=<ses-smtp-password>
```

### Example

```bash
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=apikey
MAIL_PASSWORD=SG.xYz123abc456def789
MAIL_DEFAULT_SENDER=noreply@viraly.io
```

---

## OAuth Providers

### Google OAuth

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_CLIENT_ID` | No | - | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | No | - | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | No | `/auth/oauth/google/callback` | OAuth callback URL |

### Example

```bash
GOOGLE_CLIENT_ID=123456789-abcdefghijklmnop.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abcdefghijklmnopqrstuvwxyz
GOOGLE_REDIRECT_URI=https://api.viraly.io/auth/oauth/google/callback
```

---

## Meta/Instagram

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `META_APP_ID` | Yes | - | Meta/Facebook app ID |
| `META_APP_SECRET` | Yes | - | Meta/Facebook app secret |
| `META_REDIRECT_URI` | No | `/instagram/oauth/callback` | OAuth callback URL |
| `META_WEBHOOK_VERIFY_TOKEN` | No | - | Webhook verification token |
| `META_WEBHOOK_CALLBACK_URL` | No | - | Webhook callback URL |

### Example

```bash
META_APP_ID=1234567890123456
META_APP_SECRET=abcdef1234567890abcdef1234567890
META_REDIRECT_URI=https://api.viraly.io/instagram/oauth/callback
META_WEBHOOK_VERIFY_TOKEN=a1b2c3d4e5f6g7h8i9j0
META_WEBHOOK_CALLBACK_URL=https://api.viraly.io/instagram/webhook
```

---

## OTP Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OTP_ISSUER_NAME` | No | `Viraly` | OTP issuer name |
| `OTP_SECRET_KEY` | Yes | - | Base32 encoded secret key |
| `OTP_DIGITS` | No | `6` | Number of OTP digits |
| `OTP_INTERVAL` | No | `300` | OTP validity interval in seconds |

### Example

```bash
OTP_ISSUER_NAME=Viraly
OTP_SECRET_KEY=JBSWY3DPEHPK3PXP
OTP_DIGITS=6
OTP_INTERVAL=300
```

---

## Billing

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BILLING_PROVIDER` | No | `stripe` | Billing provider: `stripe`, `razorpay` |

### Stripe

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `STRIPE_API_KEY` | Yes | - | Stripe secret API key |
| `STRIPE_PUBLISHABLE_KEY` | Yes | - | Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | Yes | - | Stripe webhook signing secret |

### Example

```bash
BILLING_PROVIDER=stripe
STRIPE_API_KEY=sk_live_XXXXX
STRIPE_PUBLISHABLE_KEY=pk_live_XXXXX
STRIPE_WEBHOOK_SECRET=whsec_XXXXX
```

### Razorpay

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RAZORPAY_API_KEY` | Yes | - | Razorpay API key ID |
| `RAZORPAY_SECRET_KEY` | Yes | - | Razorpay API secret |
| `RAZORPAY_WEBHOOK_SECRET` | Yes | - | Razorpay webhook secret |

### Example

```bash
BILLING_PROVIDER=razorpay
RAZORPAY_API_KEY=rzp_live_abcdefghijklmnop
RAZORPAY_SECRET_KEY=abcdefghijklmnopqrstuvwxyz
RAZORPAY_WEBHOOK_SECRET=abcdefghijklmnopqrstuvwxyz
```

---

## AWS S3

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AWS_ACCESS_KEY_ID` | No | - | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | No | - | AWS secret key |
| `AWS_S3_BUCKET` | No | - | S3 bucket name |
| `AWS_REGION` | No | `us-east-1` | AWS region |
| `AWS_S3_ENDPOINT_URL` | No | - | S3 endpoint URL (for S3-compatible storage) |

### Example

```bash
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_S3_BUCKET=viraly-uploads
AWS_REGION=us-east-1
```

---

## Monitoring

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SENTRY_DSN` | No | - | Sentry DSN for error tracking |
| `NEWRELIC_LICENSE_KEY` | No | - | New Relic license key |
| `NEWRELIC_APP_NAME` | No | `viraly` | New Relic application name |

### Example

```bash
SENTRY_DSN=https://abcdef1234567890@sentry.io/1234567
NEWRELIC_LICENSE_KEY=eu01xxabcd1234efgh5678ijkl9012
NEWRELIC_APP_NAME=viraly-production
```

---

## Logging

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_LEVEL` | No | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FORMAT` | No | See config | Log message format |
| `LOG_FILE` | No | `logs/viraly.log` | Log file path |
| `LOG_MAX_BYTES` | No | `10485760` | Max log file size (10MB) |
| `LOG_BACKUP_COUNT` | No | `10` | Number of log backups |

### Example

```bash
# Development
LOG_LEVEL=DEBUG
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s

# Production
LOG_LEVEL=WARNING
LOG_FILE=/app/logs/viraly.log
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=10
```

---

## Cache

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CACHE_TYPE` | No | `simple` | Cache backend: `simple`, `redis`, `memcached` |
| `CACHE_REDIS_URL` | No | - | Redis cache URL |
| `CACHE_DEFAULT_TIMEOUT` | No | `300` | Default cache timeout in seconds |

### Example

```bash
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://:redis_password@redis:6379/1
CACHE_DEFAULT_TIMEOUT=300
```

---

## Rate Limiting

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RATELIMIT_STORAGE_URL` | No | `memory://` | Rate limit storage backend |
| `RATELIMIT_DEFAULT` | No | `200 per minute` | Default rate limit |
| `RATELIMIT_ENABLED` | No | `True` | Enable rate limiting |
| `RATELIMIT_HEADERS_ENABLED` | No | `True` | Return rate limit headers |

### Example

```bash
# Development
RATELIMIT_ENABLED=False

# Production
RATELIMIT_STORAGE_URL=redis://:redis_password@redis:6379/0
RATELIMIT_DEFAULT=100 per minute
RATELIMIT_ENABLED=True
RATELIMIT_HEADERS_ENABLED=True
```

---

## File Upload

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MAX_CONTENT_LENGTH` | No | `16777216` | Max upload size in bytes (16MB) |
| `UPLOAD_FOLDER` | No | `uploads` | Upload directory path |
| `ALLOWED_EXTENSIONS` | No | See config | Allowed file extensions |

### Example

```bash
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=/app/uploads
ALLOWED_EXTENSIONS=png,jpg,jpeg,gif,pdf,csv
```

---

## AI Provider

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AI_PROVIDER` | No | `openai` | AI provider: `openai`, `anthropic`, `custom` |
| `OPENAI_API_KEY` | No | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | No | - | Anthropic API key |
| `AI_MODEL` | No | `gpt-4` | Default AI model |
| `AI_TEMPERATURE` | No | `0.7` | AI response temperature |

### Example

```bash
AI_PROVIDER=openai
OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz
AI_MODEL=gpt-4
AI_TEMPERATURE=0.7
```

---

## Example Production .env File

```bash
# =============================================================================
# VIRALY PRODUCTION ENVIRONMENT VARIABLES
# =============================================================================

# Application
FLASK_ENV=production
FLASK_APP=app.py
FLASK_DEBUG=False
SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>

# Database
DATABASE_URL=postgresql://viraly_user:secure_password@db.example.com:5432/viraly
DB_HOST=db.example.com
DB_PORT=5432
DB_NAME=viraly
DB_USER=viraly_user
DB_PASSWORD=<strong-password>

# Redis
REDIS_URL=redis://:redis_password@redis.example.com:6379/0

# Security
WTF_CSRF_ENABLED=True
PASSWORD_BCRYPT_ROUNDS=14

# Session
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
SESSION_COOKIE_DOMAIN=viraly.io
PERMANENT_SESSION_LIFETIME=7

# Mail
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=apikey
MAIL_PASSWORD=<sendgrid-api-key>
MAIL_DEFAULT_SENDER=noreply@viraly.io

# Meta/Instagram
META_APP_ID=<meta-app-id>
META_APP_SECRET=<meta-app-secret>
META_REDIRECT_URI=https://api.viraly.io/instagram/oauth/callback
META_WEBHOOK_VERIFY_TOKEN=<generate-random-token>
META_WEBHOOK_CALLBACK_URL=https://api.viraly.io/instagram/webhook

# OTP
OTP_ISSUER_NAME=Viraly
OTP_SECRET_KEY=<base32-encoded-secret>

# Billing
BILLING_PROVIDER=stripe
STRIPE_API_KEY=sk_live_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx

# Monitoring
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
NEWRELIC_LICENSE_KEY=xxxxx
NEWRELIC_APP_NAME=viraly-production

# Logging
LOG_LEVEL=WARNING

# Cache
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://:redis_password@redis.example.com:6379/0
CACHE_DEFAULT_TIMEOUT=300

# Rate Limiting
RATELIMIT_STORAGE_URL=redis://:redis_password@redis.example.com:6379/0
RATELIMIT_DEFAULT=100 per minute
RATELIMIT_ENABLED=True
RATELIMIT_HEADERS_ENABLED=True

# File Upload
MAX_CONTENT_LENGTH=16777216
```

---

## Generating Secure Keys

```bash
# Generate Flask secret key (64 characters)
openssl rand -hex 32

# Generate JWT secret key (64 characters)
openssl rand -hex 32

# Generate Meta webhook verify token (20 characters)
openssl rand -hex 10

# Generate OTP secret (Base32)
python3 -c "import secrets; print(secrets.token_hex(20))"
```

---

## Validation

The application validates required environment variables on startup. Missing required variables will cause the application to fail with a descriptive error message.

Always test your environment configuration before deployment:

```bash
# Validate configuration
flask check-config

# Run in test mode
FLASK_ENV=testing python -c "from app import create_app; app = create_app(); print('Configuration valid')"
```
