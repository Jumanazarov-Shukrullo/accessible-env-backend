import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client():
    """
    A session-scoped fixture that returns a FastAPI TestClient.
    If you need DB setup or teardown, you can do it here as well.
    """
    with TestClient(app) as c:
        yield c
