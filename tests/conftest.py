"""Test configuration and fixtures."""

import pytest
import os

os.environ["FLASK_ENV"] = "testing"


@pytest.fixture
def app():
    """Create test application."""
    from app import create_app, db
    
    test_app = create_app("testing")
    test_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "JWT_SECRET_KEY": "test-secret-key-for-testing",
        "JWT_ACCESS_TOKEN_EXPIRES": 900,
        "JWT_REFRESH_TOKEN_EXPIRES": 2592000,
        "SECRET_KEY": "test-secret-key",
        "CACHE_TYPE": "simple",
    })
    
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """Create application context."""
    with app.app_context():
        yield


@pytest.fixture
def db_session(app):
    """Create database session."""
    from app import db
    with app.app_context():
        yield db.session


@pytest.fixture
def sample_user(app):
    """Create sample user for testing."""
    from app import db
    from models.user import User
    
    with app.app_context():
        user = User(
            email="test@example.com",
            first_name="Test",
            last_name="User",
            is_active=True,
        )
        user.set_password("TestPassword123!")
        db.session.add(user)
        db.session.commit()
        
        user_id = user.id
        yield user_id


@pytest.fixture
def auth_headers(app, sample_user):
    """Create authentication headers with valid JWT."""
    from utils.jwt import JWTManager
    
    with app.app_context():
        access_token = JWTManager.create_access_token(sample_user)
        return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def admin_user(app):
    """Create admin user for testing."""
    from app import db
    from models.user import User
    
    with app.app_context():
        user = User(
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            is_active=True,
            is_admin=True,
        )
        user.set_password("AdminPassword123!")
        db.session.add(user)
        db.session.commit()
        
        yield user.id