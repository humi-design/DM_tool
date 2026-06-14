# Security Checklist

Comprehensive security hardening checklist for the Viraly platform.

## Table of Contents

1. [Authentication Security](#authentication-security)
2. [Session Security](#session-security)
3. [API Security](#api-security)
4. [Data Protection](#data-protection)
5. [Infrastructure Security](#infrastructure-security)
6. [Network Security](#network-security)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [Compliance](#compliance)

---

## Authentication Security

### Password Security

| Check | Status | Notes |
|-------|--------|-------|
| Password hashing uses bcrypt with 14 rounds | ☐ | Production requirement |
| Password hashing uses Argon2 as fallback | ☐ | Stronger than bcrypt |
| Minimum password length: 8 characters | ☐ | Enforce in registration |
| Password complexity requirements enabled | ☐ | Upper, lower, number, special |
| Common password blacklist implemented | ☐ | Check against known breaches |
| Password reset flow is secure | ☐ | Token-based, time-limited |

### Password Configuration

```python
# config.py - Production settings
class ProductionConfig(Config):
    PASSWORD_BCRYPT_ROUNDS = 14  # Higher than development
    PASSWORD_ARGON2_MEMORY_COST = 65536
    PASSWORD_ARGON2_TIME_COST = 4
    PASSWORD_ARGON2_PARALLELISM = 4
```

### JWT Security

| Check | Status | Notes |
|-------|--------|-------|
| JWT secret key is 256+ bits | ☐ | Generated with `openssl rand -hex 32` |
| Access token expiry: 15 minutes | ☐ | Short-lived tokens |
| Refresh token expiry: 30 days | ☐ | With rotation |
| JWT signature algorithm: RS256 or HS256 | ☐ | Avoid weak algorithms |
| Tokens stored securely (httpOnly cookie) | ☐ | Not in localStorage |

### JWT Configuration

```python
# config.py
class ProductionConfig(Config):
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")  # Must be set
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"
    JWT_ALGORITHM = "HS256"
```

### Multi-Factor Authentication

| Check | Status | Notes |
|-------|--------|-------|
| TOTP support implemented | ☐ | Google Authenticator compatible |
| SMS OTP as fallback option | ☐ | Less secure but accessible |
| Backup codes generated | ☐ | One-time use codes |
| MFA enforced for admin accounts | ☐ | Critical for privileged access |
| MFA enrollment process secure | ☐ | Verify before enabling |

### Login Security

| Check | Status | Notes |
|-------|--------|-------|
| Account lockout after 5 failed attempts | ☐ | 15-minute lockout |
| IP-based rate limiting on login | ☐ | 5 attempts per minute |
| Login attempt tracking implemented | ☐ | Record success/failure |
| Suspicious login detection | ☐ | New device/location alert |
|CAPTCHA on failed attempts | ☐ | After 3 failures |

---

## Session Security

### Cookie Configuration

| Check | Status | Notes |
|-------|--------|-------|
| `SECURE` flag: True | ☐ | HTTPS only |
| `HTTPONLY` flag: True | ☐ | No JavaScript access |
| `SAMESITE` flag: Lax or Strict | ☐ | CSRF protection |
| Cookie domain properly configured | ☐ | Production domain only |
| Session ID regenerated on login | ☐ | Prevent session fixation |

### Session Configuration

```python
# config.py - Production settings
class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_DOMAIN = "viraly.io"  # Production domain only
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
```

### CSRF Protection

| Check | Status | Notes |
|-------|--------|-------|
| CSRF tokens on all state-changing forms | ☐ | POST, PUT, DELETE, PATCH |
| CSRF token validated on server | ☐ | Every request |
| CSRF tokens rotated on login | ☐ | Session fixation prevention |
| Custom header requirement | ☐ | X-CSRFToken header |
| Double-submit cookie pattern | ☐ | Defense in depth |

### CSRF Configuration

```python
# config.py
class ProductionConfig(Config):
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour validity
    WTF_CSRF_HEADERS = ["X-CSRFToken", "X-CSRF-Token"]
    WTF_CSRF_FIELD_NAME = "csrf_token"
```

---

## API Security

### Rate Limiting

| Check | Status | Notes |
|-------|--------|-------|
| Rate limiting enabled | ☐ | Redis-backed for production |
| Default limit: 100 requests/minute | ☐ | Authenticated users |
| Strict limits on auth endpoints | ☐ | 5 login attempts/minute |
| Rate limit headers returned | ☐ | X-RateLimit-* headers |
| Rate limit bypass blocked | ☐ | No X-Forwarded-For trust |

### Rate Limit Configuration

```python
# config.py
class ProductionConfig(Config):
    RATELIMIT_STORAGE_URL = os.getenv("REDIS_URL")
    RATELIMIT_DEFAULT = "100 per minute"
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_HEADER_RETRY_AFTER = "Retry-After"

# auth/rate_limiting.py - Auth-specific limits
login_rate_limit = "5 per minute"
register_rate_limit = "3 per hour"
password_reset_rate_limit = "3 per hour"
otp_request_rate_limit = "5 per minute"
```

### Input Validation

| Check | Status | Notes |
|-------|--------|-------|
| All user input validated | ☐ | Type, length, format |
| SQL injection prevention | ☐ | Parameterized queries (SQLAlchemy) |
| XSS prevention | ☐ | Input sanitization, output encoding |
| Command injection prevention | ☐ | No shell execution with user input |
| Path traversal prevention | ☐ | Validate file paths |

### Input Sanitization

```python
# middleware/security.py
class InputSanitizer:
    @staticmethod
    def sanitize_html(text: str) -> str:
        """Remove potentially dangerous HTML."""
        import bleach
        allowed_tags = []
        allowed_attributes = {}
        return bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes, strip=True)
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        import re
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))
```

### API Authentication

| Check | Status | Notes |
|-------|--------|-------|
| JWT validation on all protected routes | ☐ | Decorators or middleware |
| API key authentication supported | ☐ | For programmatic access |
| OAuth 2.0 flow implemented | ☐ | Google OAuth |
| Token revocation supported | ☐ | Logout functionality |
| Cross-origin requests controlled | ☐ | CORS configuration |

---

## Data Protection

### Data at Rest

| Check | Status | Notes |
|-------|--------|-------|
| Database encryption enabled | ☐ | PostgreSQL encryption |
| File system encryption | ☐ | Encrypted volumes |
| Backup encryption | ☐ | GPG or AWS KMS |
| Sensitive data encrypted | ☐ | PII, credentials, tokens |
| Encryption key management | ☐ | Use key management service |

### Data in Transit

| Check | Status | Notes |
|-------|--------|-------|
| TLS 1.2+ enforced | ☐ | No TLS 1.0/1.1 |
| HTTPS on all endpoints | ☐ | No HTTP fallback |
| Certificate pinning | ☐ | For mobile apps |
| HSTS header configured | ☐ | max-age=31536000 |
| Secure WebSocket (WSS) | ☐ | If WebSockets used |

### TLS Configuration

```nginx
# nginx.conf
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 1d;
ssl_stapling on;
ssl_stapling_verify on;
```

### Data Retention

| Check | Status | Notes |
|-------|--------|-------|
| Data retention policy defined | ☐ | Documented |
| PII minimization | ☐ | Don't collect unnecessary PII |
| Right to deletion implemented | ☐ | GDPR compliance |
| Data anonymization for analytics | ☐ | Remove PII |
| Secure deletion | ☐ | Overwrite before deletion |

---

## Infrastructure Security

### Container Security

| Check | Status | Notes |
|-------|--------|-------|
| Minimal base image | ☐ | python:3.11-slim |
| No root user in container | ☐ | USER directive in Dockerfile |
| Secrets not in Dockerfile | ☐ | Environment variables |
| Health check configured | ☐ | For orchestration |
| Resource limits set | ☐ | CPU, memory limits |

### Dockerfile Security

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r viraly && useradd -r -g viraly viraly

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set ownership
COPY --chown=viraly:viraly . .

# Switch to non-root user
USER viraly

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

EXPOSE 5000
CMD ["gunicorn", "wsgi:app"]
```

### Image Scanning

| Check | Status | Notes |
|-------|--------|-------|
| Base image vulnerability scan | ☐ | Trivy, Snyk |
| Dependencies scanned | ☐ | Known CVEs checked |
| No critical vulnerabilities | ☐ | Remediate before deploy |
| Image signed | ☐ | Docker Content Trust |
| Registry access controlled | ☐ | Private registry |

### Secrets Management

| Check | Status | Notes |
|-------|--------|-------|
| Secrets in environment variables | ☐ | Not in code |
| Secrets encrypted at rest | ☐ | .env file encrypted |
| Secrets rotated regularly | ☐ | 90-day rotation |
| No secrets in logs | ☐ | Filter sensitive data |
| Key management service used | ☐ | AWS KMS, HashiCorp Vault |

### Secrets Configuration

```bash
# Generate secrets
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
DATABASE_PASSWORD=$(openssl rand -hex 32)
REDIS_PASSWORD=$(openssl rand -hex 32)

# Use in docker-compose
# docker-compose.yml
services:
  app:
    env_file:
      - .env  # Encrypted in production
    environment:
      - SECRET_KEY=${SECRET_KEY}
```

---

## Network Security

### Firewall Configuration

| Check | Status | Notes |
|-------|--------|-------|
| Default deny policy | ☐ | Only allow necessary |
| Port 22 limited | ☐ | Specific IPs only |
| Database not exposed | ☐ | Internal network only |
| Redis not exposed | ☐ | Internal network only |
| Load balancer public | ☐ | Port 80, 443 only |

### Firewall Rules

```bash
# UFW rules
ufw default deny incoming
ufw default allow outgoing
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow from 10.0.0.0/8 to any port 5432  # PostgreSQL
ufw allow from 10.0.0.0/8 to any port 6379  # Redis
```

### DDoS Protection

| Check | Status | Notes |
|-------|--------|-------|
| Rate limiting at network edge | ☐ | CloudFlare, AWS Shield |
| Traffic filtering | ☐ | Block malicious IPs |
| CAPTCHA for bots | ☐ | On login/registration |
| CDN for static assets | ☐ | Offload traffic |
| Auto-scaling for traffic spikes | ☐ | Handle legitimate spikes |

---

## Monitoring and Logging

### Security Logging

| Check | Status | Notes |
|-------|--------|-------|
| Authentication events logged | ☐ | Login, logout, failures |
| Authorization failures logged | ☐ | 403 errors |
| Admin actions logged | ☐ | Sensitive operations |
| Data access logged | ☐ | Audit trail |
| Errors logged securely | ☐ | No sensitive data |

### Audit Log Implementation

```python
# middleware/audit.py
class AuditMiddleware:
    AUDIT_ACTIONS = {
        "POST": "create",
        "PUT": "update",
        "PATCH": "update",
        "DELETE": "delete",
    }
    
    def log_request(self) -> None:
        """Log incoming request details."""
        g.audit_request_data = {
            "method": request.method,
            "path": request.path,
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", ""),
        }

# models/audit_log.py
def log_audit(
    action: str,
    resource_type: str = None,
    resource_id: str = None,
    user_id: str = None,
    organization_id: str = None,
    status: str = "success",
    error_message: str = None,
    old_values: dict = None,
    new_values: dict = None,
) -> None:
    """Log an audit event."""
    audit_log = AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        organization_id=organization_id,
        ip_address=request.remote_addr if request else None,
        status=status,
        error_message=error_message,
        old_values=old_values,
        new_values=new_values,
    )
    db.session.add(audit_log)
    db.session.commit()
```

### Security Headers

| Check | Status | Notes |
|-------|--------|-------|
| X-Frame-Options: DENY | ☐ | Clickjacking protection |
| X-Content-Type-Options: nosniff | ☐ | MIME sniffing prevention |
| X-XSS-Protection: 1; mode=block | ☐ | XSS filter |
| Strict-Transport-Security | ☐ | HSTS header |
| Content-Security-Policy | ☐ | Whitelist resources |
| Referrer-Policy | ☐ | Referrer control |
| Permissions-Policy | ☐ | Feature restrictions |

### Security Headers Configuration

```python
# middleware/security.py
class SecureHeaders:
    HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "X-Permitted-Cross-Domain-Policies": "none",
        "X-Download-Options": "noopen",
        "X-DNS-Prefetch-Control": "on",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';",
    }
    
    @classmethod
    def add_headers(cls, response: Response) -> Response:
        for header, value in cls.HEADERS.items():
            response.headers[header] = value
        return response
```

### Intrusion Detection

| Check | Status | Notes |
|-------|--------|-------|
| Failed login monitoring | ☐ | Alert on pattern |
| Anomalous access detection | ☐ | Unusual patterns |
| File integrity monitoring | ☐ | Detect tampering |
| Network intrusion detection | ☐ | Unusual traffic |
| Log aggregation | ☐ | Centralized logging |

---

## Compliance

### GDPR Compliance

| Check | Status | Notes |
|-------|--------|-------|
| Privacy policy published | ☐ | Clear data practices |
| Cookie consent | ☐ | Before setting cookies |
| Data subject rights | ☐ | Access, deletion, portability |
| Data Processing Agreement | ☐ | With third parties |
| Data Protection Impact Assessment | ☐ | For high-risk processing |

### PCI DSS (if handling payments)

| Check | Status | Notes |
|-------|--------|-------|
| Card data not stored | ☐ | Use payment provider |
| Secure payment integration | ☐ | Stripe, Razorpay |
| PCI compliant hosting | ☐ | Host compliance |
| Regular security scans | ☐ | Quarterly |

### SOC 2 Readiness

| Check | Status | Notes |
|-------|--------|-------|
| Access controls documented | ☐ | Role-based access |
| Change management process | ☐ | Documented changes |
| Incident response plan | ☐ | Security incidents |
| Vendor management | ☐ | Third-party risks |
| Risk assessment | ☐ | Annual review |

---

## Security Review Schedule

| Review | Frequency | Owner |
|--------|-----------|-------|
| Code security review | Per release | Security Team |
| Penetration testing | Quarterly | External Vendor |
| Vulnerability scan | Monthly | DevOps |
| Access audit | Quarterly | Security Team |
| Policy review | Annually | Security Lead |
| Incident response test | Semi-annually | Security Team |

---

## Security Contacts

| Role | Name | Email |
|------|------|-------|
| Security Lead | | |
| CISO | | |
| DevOps Lead | | |
| On-Call Security | | |

---

## Training

| Training | Frequency | Audience |
|----------|-----------|----------|
| Security awareness | Annually | All employees |
| Secure coding | Annually | Developers |
| Incident response | Semi-annually | Operations |
| Data protection | Annually | All users |
