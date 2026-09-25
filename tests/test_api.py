from fastapi.testclient import TestClient

from backend.serving.fast_api import app


client = TestClient(app)


def test_health_endpoint():
    """Verify that the health endpoint returns HTTP 200 and the expected payload."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
