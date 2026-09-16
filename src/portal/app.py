"""FastAPI application factory and run lifecycle endpoints."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from portal import __version__
from portal.artifacts import zip_directory
from portal.runs import QueueFullError, RunManager, RunSnapshot
from portal.schemas import RunSubmission


def _snapshot_payload(snapshot: RunSnapshot) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "run_id": snapshot.run_id,
        "status": snapshot.status,
        "created_at": snapshot.created_at.isoformat(),
        "updated_at": snapshot.updated_at.isoformat(),
        "poll_after_seconds": 2,
    }
    if snapshot.status == "failed":
        payload["error"] = snapshot.error or "run failed"
    if snapshot.status == "completed" and snapshot.result is not None:
        payload["source_version"] = snapshot.result.source_version
        payload["results"] = [
            {
                "rank": row.rank,
                "serving_mode": row.serving_mode,
                "metrics": dict(row.metrics),
            }
            for row in snapshot.result.rows
        ]
    return payload


def create_app(run_manager: RunManager | None = None) -> FastAPI:
    """Build the application without importing the Linux-only estimator."""

    manager = run_manager or RunManager(
        Path(os.getenv("PORTAL_RUN_ROOT", "/tmp/serving-portal-runs"))
    )
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        manager.close()

    app = FastAPI(title="Serving Configuration Portal", version=__version__, lifespan=lifespan)

    @app.get("/health/live", tags=["health"])
    def live() -> dict[str, str]:
        """Report that the web process can serve requests."""

        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse, tags=["meta"])
    def index(request: Request) -> HTMLResponse:
        """Render the self-service request form."""

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"version": __version__},
        )

    @app.post("/api/runs", status_code=202, tags=["runs"])
    def submit_run(submission: RunSubmission) -> JSONResponse:
        """Admit one run and return a polling location immediately."""

        try:
            snapshot = manager.submit(submission.to_request())
        except QueueFullError:
            return JSONResponse(
                status_code=429,
                content={"error": "run capacity is full; retry later"},
                headers={"Retry-After": "2"},
            )
        except RuntimeError as exc:
            return JSONResponse(status_code=503, content={"error": str(exc)})
        return JSONResponse(
            status_code=202,
            content={
                "run_id": snapshot.run_id,
                "status": snapshot.status,
                "status_url": f"/api/runs/{snapshot.run_id}",
                "poll_after_seconds": 2,
            },
        )

    @app.get("/api/runs/{run_id}", tags=["runs"])
    def get_run(run_id: str) -> JSONResponse:
        """Return lifecycle state and normalized results when complete."""

        if not run_id.isascii() or len(run_id) != 32:
            return JSONResponse(status_code=404, content={"error": "run not found"})
        snapshot = manager.snapshot(run_id)
        if snapshot is None:
            return JSONResponse(status_code=404, content={"error": "run not found"})
        return JSONResponse(content=_snapshot_payload(snapshot))

    @app.get("/api/runs/{run_id}/artifacts", response_model=None, tags=["runs"])
    def download_artifacts(run_id: str) -> StreamingResponse | JSONResponse:
        """Download generated files only after a run completes."""

        if not run_id.isascii() or len(run_id) != 32:
            return JSONResponse(status_code=404, content={"error": "run not found"})
        snapshot = manager.snapshot(run_id)
        if snapshot is None:
            return JSONResponse(status_code=404, content={"error": "run not found"})
        if snapshot.status != "completed" or snapshot.result is None:
            return JSONResponse(status_code=409, content={"error": "run is not complete"})
        try:
            content = zip_directory(snapshot.result.artifact_dir)
        except (FileNotFoundError, ValueError) as exc:
            return JSONResponse(status_code=500, content={"error": str(exc)})
        return StreamingResponse(
            iter([content]),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="run-{run_id}-artifacts.zip"'},
        )

    return app


app = create_app()
