"""Minimal API surface; analytical endpoints will be added behind contracts."""

from fastapi import FastAPI

from promoguard import __version__

app = FastAPI(title="PromoGuard API", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "promoguard-api", "version": __version__}

