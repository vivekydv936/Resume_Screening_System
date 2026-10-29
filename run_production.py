"""Run the Flask app with Waitress for a Windows deployment."""

from __future__ import annotations

import os

from waitress import serve

from app import app


if __name__ == "__main__":
    serve(
        app,
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        threads=int(os.environ.get("WAITRESS_THREADS", "4")),
        channel_timeout=120,
    )
