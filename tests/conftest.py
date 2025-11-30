"""
Test configuration and fixtures for Stock Tracker
"""
import os
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from redis import Redis

from stock_tracker.database.models.base import Base
from stock_tracker.api.main import app
from stock_tracker.database.connection import get_db
from stock_tracker.cache.redis_cache import RedisCache
from stock_tracker.database.models import Tenant, User
from stock_tracker.auth.password import hash_password
from stock_tracker.auth.jwt_manager import create_access_token


# =============================================================================
# Test Database Setup
# =============================================================================

@pytest.fixture(scope="session")
def test_db_url() -> str:
    """Get test database URL"""
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://stock_tracker:stock_tracker_password@localhost:5432/stock_tracker_test"
    )


@pytest.fixture(scope="session")
def engine(test_db_url):
    """Create test database engine"""
    # Use in-memory SQLite for faster tests (optional)
    # engine = create_engine(
    #     "sqlite:///:memory:",
    #     connect_args={"check_same_thread": False},
    #     poolclass=StaticPool,
    # )
    
    # Use PostgreSQL test database
    engine = create_engine(test_db_url)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(engine) -> Generator[Session, None, None]:
    """Create a new database session for each test"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# =============================================================================
# Test Redis Setup
# =============================================================================

@pytest.fixture(scope="session")
def test_redis_url() -> str:
    """Get test Redis URL"""
    return os.getenv("TEST_REDIS_URL", "redis://localhost:6379/15")


@pytest.fixture(scope="function")
def redis_client(test_redis_url):
    """Create test Redis client"""
    client = Redis.from_url(test_redis_url, decode_responses=True)
    yield client
    client.flushdb()  # Clear test database after each test
    client.close()


@pytest.fixture(scope="function")
def cache(redis_client):
    """Create test cache instance"""
    return RedisCache(redis_client)


# =============================================================================
# FastAPI Test Client
# =============================================================================

@pytest.fixture(scope="function")
def client(db_session) -> TestClient:
    """Create FastAPI test client with overridden dependencies"""
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def test_user_data():
    """Test user data"""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User",
        "company_name": "Test Company"
    }


@pytest.fixture
def test_tenant(db_session) -> Tenant:
    """Create test tenant"""
    tenant = Tenant(
        name="Test Company",
        marketplace_type="wildberries",
        is_active=True,
        sync_interval_minutes=60
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def test_user(db_session, test_tenant, test_user_data) -> User:
    """Create test user"""
    user = User(
        email=test_user_data["email"],
        password_hash=hash_password(test_user_data["password"]),
        name=test_user_data["full_name"],
        tenant_id=test_tenant.id,
        is_active=True,
        role="owner"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_subscription(db_session, test_tenant):
    """Create test subscription (if model exists)"""
    try:
        from stock_tracker.database.models import Subscription
        from datetime import datetime, timedelta
        
        subscription = Subscription(
            tenant_id=test_tenant.id,
            plan_name="pro",
            status="active",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30),
            api_calls_limit=10000,
            sync_frequency_minutes=30
        )
        db_session.add(subscription)
        db_session.commit()
        db_session.refresh(subscription)
        return subscription
    except ImportError:
        # Subscription model not implemented yet
        return None


@pytest.fixture
def test_access_token(test_user) -> str:
    """Create test access token"""
    return create_access_token(
        user_id=str(test_user.id),
        tenant_id=str(test_user.tenant_id),
        role=test_user.role
    )


@pytest.fixture
def auth_headers(test_access_token) -> dict:
    """Create authorization headers"""
    return {"Authorization": f"Bearer {test_access_token}"}


# =============================================================================
# Mock External Services
# =============================================================================

@pytest.fixture
def mock_wildberries_api(monkeypatch):
    """Mock Wildberries API client"""
    from unittest.mock import MagicMock
    
    mock_client = MagicMock()
    mock_client.get_stocks.return_value = [
        {
            "sku": "TEST-SKU-001",
            "barcode": "1234567890123",
            "quantity": 100,
            "warehouse_name": "Подольск"
        }
    ]
    mock_client.get_orders.return_value = []
    mock_client.get_sales.return_value = []
    
    return mock_client


@pytest.fixture
def mock_telegram_bot(monkeypatch):
    """Mock Telegram bot API"""
    from unittest.mock import patch, MagicMock
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": True, "result": {}}
    
    with patch("requests.post", return_value=mock_response) as mock_post:
        yield mock_post


# =============================================================================
# Async Test Support
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Environment Setup
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables"""
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
    os.environ["FERNET_KEY"] = "test-fernet-key-for-testing-only-32bytes=="
    os.environ["RATE_LIMIT_GLOBAL"] = "10000"
    os.environ["RATE_LIMIT_TENANT"] = "1000"
    yield
    # Cleanup if needed
