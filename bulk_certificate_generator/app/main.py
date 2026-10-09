from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from app.database import connect, init_db
from app.generator import generate_certificate
from app.schemas import GenerationRequest

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Bulk Certificate Generator API",
    description="Submit bulk certificate jobs, track results, and download generated PDF certificates.",
    version="1.0.0",
    lifespan=lifespan,
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/jobs", status_code=201)
def create_job(payload: GenerationRequest):
    job_id = str(uuid4())
    recipients = [recipient.model_dump() for recipient in payload.recipients]
    created_at = datetime.now(timezone.utc).isoformat()

    with connect() as db:
        db.execute(
            "INSERT INTO jobs (id, status, total, created_at) VALUES (?, ?, ?, ?)",
            (job_id, "processing", len(recipients), created_at),
        )
        for recipient in recipients:
            cursor = db.execute(
                """INSERT INTO certificates
                   (job_id, recipient_name, recipient_email, status)
                   VALUES (?, ?, ?, ?)""",
                (job_id, recipient["name"], recipient["email"], "queued"),
            )
            certificate_id = cursor.lastrowid
            try:
                file_path = generate_certificate(
                    name=recipient["name"],
                    email=recipient["email"],
                    event_name=payload.event_name,
                    title=payload.certificate_title,
                    job_id=job_id,
                    certificate_id=certificate_id,
                )
                db.execute(
                    "UPDATE certificates SET status = ?, file_path = ? WHERE id = ?",
                    ("succeeded", file_path, certificate_id),
                )
            except Exception as exc:
                db.execute(
                    "UPDATE certificates SET status = ?, error = ? WHERE id = ?",
                    ("failed", str(exc)[:500], certificate_id),
                )

        counts = db.execute(
            """SELECT
               SUM(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END) AS succeeded,
               SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed
               FROM certificates WHERE job_id = ?""",
            (job_id,),
        ).fetchone()
        succeeded, failed = counts["succeeded"] or 0, counts["failed"] or 0
        status = "completed" if failed == 0 else ("failed" if succeeded == 0 else "completed_with_errors")
        db.execute(
            "UPDATE jobs SET status = ?, succeeded = ?, failed = ? WHERE id = ?",
            (status, succeeded, failed, job_id),
        )

    return {
        "job_id": job_id,
        "status": status,
        "total": len(recipients),
        "succeeded": succeeded,
        "failed": failed,
        "status_url": f"/jobs/{job_id}",
    }

@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    with connect() as db:
        job = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        rows = db.execute(
            "SELECT * FROM certificates WHERE job_id = ? ORDER BY id", (job_id,)
        ).fetchall()

    return {
        "job_id": job["id"],
        "status": job["status"],
        "total": job["total"],
        "succeeded": job["succeeded"],
        "failed": job["failed"],
        "results": [
            {
                "id": row["id"],
                "name": row["recipient_name"],
                "email": row["recipient_email"],
                "status": row["status"],
                "download_url": f"/certificates/{row['id']}" if row["status"] == "succeeded" else None,
                "error": row["error"],
            }
            for row in rows
        ],
    }

@app.get("/certificates/{certificate_id}")
def download_certificate(certificate_id: int):
    with connect() as db:
        row = db.execute(
            "SELECT file_path, recipient_name FROM certificates WHERE id = ? AND status = 'succeeded'",
            (certificate_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Generated certificate not found")
    path = Path(row["file_path"])
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Certificate file is missing")
    return FileResponse(path, media_type="application/pdf", filename=f"{path.name}")

@app.get("/")
def root():
    return {"message": "Bulk Certificate Generator API", "docs": "/docs", "health": "/health"}
