"""
Minimal test configuration for Stock Tracker FastAPI 2.0
"""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from unittest.mock import MagicMock

from stock_tracker.database.models.base import Base


# =============================================================================
# Test Database Setup
# =============================================================================

@pytest.fixture(scope="session")
def test_db_url() -> str:
    """Get test database URL"""
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://stock_tracker:stock_tracker_password@postgres:5432/stock_tracker_test"
    )


@pytest.fixture(scope="function")
def db_session():
    """Create a mock database session for unit tests"""
    mock_session = MagicMock(spec=Session)
    mock_session.add = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.rollback = MagicMock()
    mock_session.query = MagicMock()
    return mock_session


# =============================================================================
# Environment Setup
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables"""
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-minimum-32-characters-long"
    os.environ["ENCRYPTION_MASTER_KEY"] = "test-encryption-key-for-testing-32b="
    os.environ["REDIS_URL"] = "redis://redis:6379/15"
    os.environ["DATABASE_URL"] = "postgresql://stock_tracker:stock_tracker_password@postgres:5432/stock_tracker_test"
    yield
