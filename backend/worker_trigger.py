"""Start Cloud Run worker executions for video-processing jobs."""

from __future__ import annotations

from urllib.parse import quote

import google.auth
from google.auth.transport.requests import Request
import requests

from config import settings


CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


def trigger_video_worker(job_id: str) -> None:
    """Start one Cloud Run Job execution for a PostgreSQL job."""

    if not settings.worker_job_name:
        raise RuntimeError("WORKER_JOB_NAME is not configured.")
    if not settings.google_cloud_project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is not configured.")

    credentials, _ = google.auth.default(
        scopes=[CLOUD_PLATFORM_SCOPE],
    )
    credentials.refresh(Request())

    project = quote(settings.google_cloud_project, safe="")
    region = quote(settings.worker_job_region, safe="")
    job_name = quote(settings.worker_job_name, safe="")
    endpoint = (
        "https://run.googleapis.com/v2/projects/"
        f"{project}/locations/{region}/jobs/{job_name}:run"
    )
    response = requests.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json",
        },
        json={
            "overrides": {
                "containerOverrides": [
                    {
                        "env": [
                            {
                                "name": "PRONONCIA_JOB_ID",
                                "value": job_id,
                            }
                        ]
                    }
                ]
            }
        },
        timeout=15,
    )
    response.raise_for_status()
