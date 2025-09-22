"""Pytest configuration and fixtures"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    """Create a test client for the FastAPI app"""
    with TestClient(app) as c:
        yield c