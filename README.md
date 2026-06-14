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

## Tech Stack

### Backend
- **Flask 3.0** - Python web framework
- **SQLAlchemy 2.0** - ORM for database operations
- **Alembic** - Database migrations
- **PostgreSQL** - Primary database
- **Gunicorn** - Production WSGI server

### Frontend
- **Jinja2** - Template engine
- **TailwindCSS** - Utility-first CSS framework
- **HTMX** - Hyperscript extensions
- **Alpine.js** - JavaScript framework

### Security
- **JWT** - JSON Web Tokens for authentication
- **bcrypt/Argon2** - Password hashing
- **CSRF Protection** - Cross-Site Request Forgery protection
- **Rate Limiting** - Request throttling
- **Secure Cookies** - Session security

## Project Structure

```
viraly/
├── app.py                 # Flask application factory
├── config.py              # Configuration management
├── wsgi.py                # WSGI entry point
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variables template
│
├── auth/                  # Authentication module
│   ├── __init__.py
│   └── routes.py
│
├── users/                 # User management module
│   ├── __init__.py
│   └── routes.py
│
├── organizations/         # Multi-tenancy module
│   ├── __init__.py
│   └── routes.py
│
├── businesses/            # Business management module
│   ├── __init__.py
│   └── routes.py
│
├── instagram/             # Instagram integration module
│   ├── __init__.py
│   └── routes.py
│
├── comments/              # Comment management module
│   ├── __init__.py
│   └── routes.py
│
├── dm/                    # Direct messages module
│   ├── __init__.py
│   └── routes.py
│
├── resources/             # File resources module
│   ├── __init__.py
│   └── routes.py
│
├── leads/                 # Lead management module
│   ├── __init__.py
│   └── routes.py
│
├── dashboard/             # Dashboard module
│   ├── __init__.py
│   └── routes.py
│
├── analytics/             # Analytics module
│   ├── __init__.py
│   └── routes.py
│
├── billing/               # Billing module
│   ├── __init__.py
│   └── routes.py
│
├── settings/              # Settings module
│   ├── __init__.py
│   └── routes.py
│
├── admin/                 # Admin panel module
│   ├── __init__.py
│   └── routes.py
│
├── middleware/            # Custom middleware
│   ├── security.py
│   └── audit.py
│
├── models/                # Database models
│   ├── __init__.py
│   ├── base.py
│   ├── user.py
│   ├── organization.py
│   ├── business.py
│   ├── auth.py
│   └── instagram.py
│
├── repositories/          # Data access layer
│
├── services/              # Business logic layer
│
├── utils/                 # Utility functions
│   ├── __init__.py
│   ├── jwt.py
│   ├── security.py
│   ├── validators.py
│   └── template.py
│
├── templates/             # Jinja2 templates
│   ├── base.html
│   ├── auth/
│   ├── dashboard/
│   ├── dm/
│   ├── comments/
│   ├── leads/
│   ├── analytics/
│   ├── settings/
│   ├── instagram/
│   ├── billing/
│   └── partials/
│
└── static/                # Static files
    ├── css/
    ├── js/
    └── images/
```

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis (for caching and rate limiting)
- Node.js 18+ (optional, for asset building)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-org/viraly.git
cd viraly
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Create database**
```bash
# Log in to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE viraly;
CREATE DATABASE viraly_test;

# Create user (optional)
CREATE USER viraly_user WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE viraly TO viraly_user;
```

6. **Run migrations**
```bash
flask db init
flask db migrate
flask db upgrade
```

7. **Seed initial data (optional)**
```bash
flask seed
```

8. **Run the development server**
```bash
flask run
# Or for production:
gunicorn wsgi:app -w 4 -b 0.0.0.0:5000
```

### Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `FLASK_ENV` - `development`, `production`, or `testing`
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - Flask secret key
- `JWT_SECRET_KEY` - JWT signing key
- `SENTRY_DSN` - Sentry error tracking (optional)

## Configuration

### Development
```bash
FLASK_ENV=development
DEBUG=True
```

### Production
```bash
FLASK_ENV=production
DEBUG=False

# Increase security settings
PASSWORD_BCRYPT_ROUNDS=14
RATELIMIT_DEFAULT=100 per minute
```

### Testing
```bash
FLASK_ENV=testing
SQLALCHEMY_DATABASE_URI=sqlite:///:memory:
```

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/logout` - User logout
- `POST /auth/forgot-password` - Password reset request
- `POST /auth/reset-password` - Reset password
- `POST /auth/verify-otp` - Verify OTP code
- `GET /auth/oauth/google` - Google OAuth login

### Users
- `GET /api/users` - List users
- `GET /api/users/<id>` - Get user details
- `PUT /api/users/<id>` - Update user
- `GET /api/me` - Get current user

### Organizations
- `GET /api/organizations` - List organizations
- `POST /api/organizations` - Create organization
- `GET /api/organizations/<id>` - Get organization
- `PUT /api/organizations/<id>` - Update organization
- `DELETE /api/organizations/<id>` - Delete organization
- `POST /api/organizations/<id>/members` - Add member

### Instagram
- `GET /api/instagram/accounts` - List connected accounts
- `POST /api/instagram/accounts` - Connect account
- `POST /api/instagram/accounts/<id>/sync` - Sync account data

### DMs
- `GET /api/dm/threads` - List DM threads
- `GET /api/dm/threads/<id>` - Get thread details
- `POST /api/dm/threads/<id>/send` - Send message
- `GET /api/dm/templates` - List message templates

### Comments
- `GET /api/comments` - List comments
- `POST /api/comments/<id>/reply` - Reply to comment
- `POST /api/comments/<id>/hide` - Hide comment
- `PUT /api/auto-reply` - Configure auto-reply

### Leads
- `GET /api/leads` - List leads
- `GET /api/leads/<id>` - Get lead details
- `PUT /api/leads/<id>/status` - Update lead status
- `GET /api/segments` - List lead segments

## Security Features

### Authentication
- JWT-based authentication with access/refresh tokens
- Secure password hashing (Argon2/Bcrypt)
- Email/Mobile OTP verification ready
- Google OAuth integration ready

### Protection
- CSRF protection on all forms
- Rate limiting on API endpoints
- SQL injection prevention (parameterized queries)
- XSS prevention (input sanitization)
- Secure session cookies

### Audit
- Complete audit logging
- Login attempt tracking
- Action history

## Deployment

### Docker (Recommended)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN flask db upgrade

CMD ["gunicorn", "wsgi:app", "-w", "4", "-b", "0.0.0.0:5000"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/viraly
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=viraly
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Manual Deployment

1. Set up PostgreSQL and Redis
2. Configure environment variables
3. Install dependencies: `pip install -r requirements.txt`
4. Run migrations: `flask db upgrade`
5. Start Gunicorn: `gunicorn wsgi:app -w 4 -b 0.0.0.0:5000`

## Monitoring

### Sentry Integration
```bash
SENTRY_DSN=https://key@sentry.io/project
```

### New Relic Integration
```bash
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

Built with ❤️ by the Viraly Team