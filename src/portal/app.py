"""FastAPI application factory and run lifecycle endpoints."""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.templating import Jinja2Templates
from prometheus_client import CONTENT_TYPE_LATEST

from portal import __version__
from portal.artifacts import zip_directory
from portal.observability import PortalMetrics, configure_logging
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
        payload["visualizations"] = [
            {
                "id": asset.asset_id,
                "url": f"/api/runs/{snapshot.run_id}/visualizations/{asset.asset_id}",
                "media_type": asset.media_type,
                "width": asset.width,
                "height": asset.height,
                "alt_text": asset.alt_text,
                "caption": asset.caption,
                "scope_note": asset.scope_note,
                "axis_note": asset.axis_note,
            }
            for asset in snapshot.result.visualizations
        ]
    return payload


def create_app(run_manager: RunManager | None = None) -> FastAPI:
    """Build the application without importing the Linux-only estimator."""

    manager = run_manager or RunManager(
        Path(os.getenv("PORTAL_RUN_ROOT", "/tmp/serving-portal-runs"))
    )
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
    metrics = PortalMetrics()
    configure_logging()
    logger = logging.getLogger("portal")

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        manager.close()

    app = FastAPI(title="Serving Configuration Portal", version=__version__, lifespan=lifespan)

    @app.get("/health/live", tags=["health"])
    def live() -> dict[str, str]:
        """Report that the web process can serve requests."""

        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    def ready() -> JSONResponse:
        """Report whether the process is initialized and accepting work."""

        if not bool(manager.stats()["ready"]):
            return JSONResponse(status_code=503, content={"status": "shutting_down"})
        return JSONResponse(content={"status": "ok"})

    @app.get("/metrics", tags=["health"])
    def prometheus_metrics() -> Response:
        """Expose bounded service metrics without run/model labels."""

        return Response(content=metrics.render(manager.stats()), media_type=CONTENT_TYPE_LATEST)

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
            metrics.rejected.inc()
            logger.warning(
                "run rejected", extra={"event": "run_rejected", "error_category": "capacity"}
            )
            return JSONResponse(
                status_code=429,
                content={"error": "run capacity is full; retry later"},
                headers={"Retry-After": "2"},
            )
        except RuntimeError as exc:
            logger.warning(
                "run rejected", extra={"event": "run_rejected", "error_category": "shutdown"}
            )
            return JSONResponse(status_code=503, content={"error": str(exc)})
        metrics.submitted.inc()
        logger.info(
            "run accepted",
            extra={"event": "run_accepted", "run_id": snapshot.run_id, "status": snapshot.status},
        )
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

    @app.get("/api/runs/{run_id}/visualizations/{asset_id}", response_model=None, tags=["runs"])
    def get_visualization(run_id: str, asset_id: str) -> FileResponse | JSONResponse:
        """Serve one verified PNG generated by the completed run."""

        if not _is_opaque_id(run_id) or not _is_opaque_id(asset_id):
            return JSONResponse(status_code=404, content={"error": "visualization not found"})
        snapshot = manager.snapshot(run_id)
        if snapshot is None:
            return JSONResponse(status_code=404, content={"error": "run not found"})
        if snapshot.status != "completed" or snapshot.result is None:
            return JSONResponse(status_code=409, content={"error": "run is not complete"})
        asset = next(
            (
                candidate
                for candidate in snapshot.result.visualizations
                if candidate.asset_id == asset_id
            ),
            None,
        )
        if asset is None:
            return JSONResponse(status_code=404, content={"error": "visualization not found"})
        if asset.media_type != "image/png":
            return JSONResponse(
                status_code=415, content={"error": "unsupported visualization media"}
            )
        root = snapshot.result.artifact_dir.resolve()
        candidate = root / asset.relative_path
        if candidate.is_symlink():
            return JSONResponse(status_code=404, content={"error": "visualization not found"})
        path = candidate.resolve()
        if not path.is_relative_to(root) or not path.is_file():
            return JSONResponse(status_code=404, content={"error": "visualization not found"})
        try:
            header = path.read_bytes()[:8]
        except OSError:
            return JSONResponse(status_code=404, content={"error": "visualization not found"})
        if header != b"\x89PNG\r\n\x1a\n":
            return JSONResponse(
                status_code=415, content={"error": "unsupported visualization media"}
            )
        return FileResponse(path, media_type="image/png")

    return app


app = create_app()


def _is_opaque_id(value: str) -> bool:
    """Accept only server-issued lowercase hexadecimal identifiers."""

    return len(value) == 32 and all(character in "0123456789abcdef" for character in value)
