"""FastAPI application factory."""

from fastapi import FastAPI

from portal import __version__


def create_app() -> FastAPI:
    """Build the application without importing the Linux-only estimator."""

    app = FastAPI(title="Serving Configuration Portal", version=__version__)

    @app.get("/health/live", tags=["health"])
    def live() -> dict[str, str]:
        """Report that the web process can serve requests."""

        return {"status": "ok"}

    @app.get("/", tags=["meta"])
    def index() -> dict[str, str]:
        """Temporary metadata endpoint until the browser slice is added."""

        return {"service": "serving-configuration-portal", "version": __version__}

    return app


app = create_app()
