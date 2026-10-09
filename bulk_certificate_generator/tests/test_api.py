import os
import tempfile
from pathlib import Path

# Configure isolated storage before importing the app.
_temp = tempfile.TemporaryDirectory()
os.environ["DATABASE_PATH"] = str(Path(_temp.name) / "test.db")
os.environ["CERTIFICATE_DIR"] = str(Path(_temp.name) / "generated")

from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

init_db()
client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_create_job_and_download_certificate():
    payload = {
        "event_name": "Python Bootcamp",
        "certificate_title": "Certificate of Completion",
        "recipients": [
            {"name": "Asha Patil", "email": "asha@example.com"},
            {"name": "Rahul Shah", "email": "rahul@example.com"}
        ]
    }
    response = client.post("/jobs", json=payload)
    assert response.status_code == 201
    job = response.json()
    assert job["total"] == 2
    assert job["succeeded"] == 2
    assert job["failed"] == 0

    status_response = client.get(job["status_url"])
    assert status_response.status_code == 200
    status = status_response.json()
    assert status["status"] == "completed"
    assert len(status["results"]) == 2

    certificate_response = client.get(status["results"][0]["download_url"])
    assert certificate_response.status_code == 200
    assert certificate_response.headers["content-type"] == "application/pdf"
    assert certificate_response.content.startswith(b"%PDF")

def test_input_validation():
    response = client.post("/jobs", json={
        "event_name": "Workshop",
        "recipients": [{"name": "A", "email": "not-an-email"}]
    })
    assert response.status_code == 422

def test_unknown_job_returns_404():
    response = client.get("/jobs/not-a-real-job")
    assert response.status_code == 404

def test_missing_certificate_returns_404():
    response = client.get("/certificates/999999")
    assert response.status_code == 404


def test_individual_certificate_failure_does_not_stop_batch(monkeypatch):
    import app.main as main_module
    original_generator = main_module.generate_certificate

    def flaky_generator(**kwargs):
        if kwargs["name"] == "Asha Patil":
            raise RuntimeError("simulated PDF generation failure")
        return original_generator(**kwargs)

    monkeypatch.setattr(main_module, "generate_certificate", flaky_generator)
    response = client.post("/jobs", json={
        "event_name": "Resilience Workshop",
        "recipients": [
            {"name": "Asha Patil", "email": "asha@example.com"},
            {"name": "Rahul Shah", "email": "rahul@example.com"}
        ]
    })
    assert response.status_code == 201
    job = response.json()
    assert job["total"] == 2
    assert job["succeeded"] == 1
    assert job["failed"] == 1
    assert job["status"] == "completed_with_errors"

    results = client.get(job["status_url"]).json()["results"]
    assert [item["status"] for item in results] == ["failed", "succeeded"]
    assert "simulated PDF generation failure" in results[0]["error"]
