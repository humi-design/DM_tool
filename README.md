# Viraly - AI-Powered Social Media Management Platform

![Viraly Logo](https://via.placeholder.com/150x50?text=Viraly)

Viraly is a production-ready SaaS platform for managing Instagram DMs, comments, and leads with AI-powered automation.

## Features

- **Instagram Integration**: Connect and manage multiple Instagram Business/Creator accounts
- **DM Management**: View, respond, and automate direct messages
- **Comment Management**: Monitor and auto-reply to post comments
- **Lead Management**: Track and manage leads from Instagram interactions
- **Analytics**: Comprehensive analytics and reporting
- **AI Automation**: Intelligent auto-replies and lead scoring
- **Multi-tenancy**: Support for multiple organizations and businesses
- **Billing**: Integrated billing with Stripe and Razorpay

## Tech Stack

### Backend
- **Flask 3.0** - Python web framework
- **SQLAlchemy 2.0** - ORM for database operations
- **Alembic** - Database migrations
- **PostgreSQL 14+** - Primary database
- **Redis 7+** - Caching and rate limiting
- **Gunicorn** - Production WSGI server

### Frontend
- **Jinja2** - Template engine
- **TailwindCSS** - Utility-first CSS framework
- **HTMX** - Hyperscript extensions
- **Alpine.js** - JavaScript framework

### Infrastructure
- **Docker** - Containerization
- **Nginx** - Reverse proxy and SSL termination
- **Sentry** - Error tracking
- **New Relic** - Application performance monitoring

### Security
- **JWT** - JSON Web Tokens for authentication
- **bcrypt/Argon2** - Password hashing
- **CSRF Protection** - Cross-Site Request Forgery protection
- **Rate Limiting** - Request throttling
- **Secure Cookies** - Session security
- **Audit Logging** - Complete action tracking

## Quick Start

### Docker (Recommended)

```bash
# Clone and configure
git clone https://github.com/your-org/viraly.git
cd viraly

# Copy environment file
cp .env.example .env

# Generate secure keys
openssl rand -hex 32  # Use for SECRET_KEY
openssl rand -hex 32  # Use for JWT_SECRET_KEY

# Start services
docker-compose up -d

# Run migrations
docker-compose exec app flask db upgrade

# Create admin user
docker-compose exec app flask admin create-admin
```

### Manual Installation

See [Deployment Guide](DEPLOYMENT_GUIDE.md) for detailed manual installation instructions.

## Documentation

- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Complete deployment instructions
- [Environment Variable Guide](ENVIRONMENT_VARIABLE_GUIDE.md) - All environment variables
- [Production Checklist](PRODUCTION_CHECKLIST.md) - Pre-deployment checklist
- [Disaster Recovery Guide](DISASTER_RECOVERY_GUIDE.md) - Backup and recovery procedures
- [Scaling Guide](SCALING_GUIDE.md) - Horizontal and vertical scaling
- [Migration Guide](MIGRATION_GUIDE.md) - Database migrations
- [Security Checklist](SECURITY_CHECKLIST.md) - Security hardening

## Project Structure

```
viraly/
├── app.py                 # Flask application factory
├── config.py              # Configuration management
├── wsgi.py                # WSGI entry point
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Container orchestration
├── nginx.conf             # Nginx configuration
├── .env.example           # Environment variables template
│
├── auth/                  # Authentication module
├── users/                 # User management module
├── organizations/         # Multi-tenancy module
├── businesses/            # Business management module
├── instagram/             # Instagram integration module
├── comments/              # Comment management module
├── dm/                    # Direct messages module
├── resources/             # File resources module
├── leads/                 # Lead management module
├── dashboard/             # Dashboard module
├── analytics/             # Analytics module
├── billing/               # Billing module
├── settings/              # Settings module
├── admin/                 # Admin panel module
├── onboarding/            # Onboarding module
├── comment_intelligence/  # AI comment intelligence
│
├── middleware/            # Custom middleware
│   ├── security.py        # Security headers, CORS
│   └── audit.py           # Audit logging
│
├── models/                # Database models
├── repositories/          # Data access layer
├── services/              # Business logic layer
│   └── instagram_service.py
├── utils/                 # Utility functions
│
├── templates/             # Jinja2 templates
├── static/                # Static files (CSS, JS)
└── alembic/               # Database migrations
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | User login |
| POST | `/auth/register` | User registration |
| POST | `/auth/logout` | User logout |
| POST | `/auth/forgot-password` | Password reset request |
| POST | `/auth/reset-password` | Reset password |
| POST | `/auth/verify-otp` | Verify OTP code |
| GET | `/auth/oauth/google` | Google OAuth login |

### Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users` | List users |
| GET | `/api/users/<id>` | Get user details |
| PUT | `/api/users/<id>` | Update user |
| GET | `/api/me` | Get current user |

### Organizations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/organizations` | List organizations |
| POST | `/api/organizations` | Create organization |
| GET | `/api/organizations/<id>` | Get organization |
| PUT | `/api/organizations/<id>` | Update organization |
| DELETE | `/api/organizations/<id>` | Delete organization |
| POST | `/api/organizations/<id>/members` | Add member |

### Instagram
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/instagram/accounts` | List connected accounts |
| POST | `/api/instagram/accounts` | Connect account |
| POST | `/api/instagram/accounts/<id>/sync` | Sync account data |

### DMs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dm/threads` | List DM threads |
| GET | `/api/dm/threads/<id>` | Get thread details |
| POST | `/api/dm/threads/<id>/send` | Send message |
| GET | `/api/dm/templates` | List message templates |

### Comments
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/comments` | List comments |
| POST | `/api/comments/<id>/reply` | Reply to comment |
| POST | `/api/comments/<id>/hide` | Hide comment |
| PUT | `/api/auto-reply` | Configure auto-reply |

### Leads
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/leads` | List leads |
| GET | `/api/leads/<id>` | Get lead details |
| PUT | `/api/leads/<id>/status` | Update lead status |
| GET | `/api/segments` | List lead segments |

### Health Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Application health check |
| GET | `/ready` | Readiness probe |

## Monitoring

### Health Checks

```bash
# Application health
curl https://api.viraly.io/health

# Kubernetes readiness
curl https://api.viraly.io/ready
```

### Metrics Integration

```bash
# Configure Sentry
SENTRY_DSN=https://key@sentry.io/project

# Configure New Relic
NEWRELIC_LICENSE_KEY=your-license-key
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Documentation: https://docs.viraly.io
- Email: support@viraly.io
- Twitter: [@viralyio](https://twitter.com/viralyio)

---

Built with love by the Viraly Team
