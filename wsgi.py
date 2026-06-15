"""WSGI entry point for Viraly platform."""

import os
import logging
import sys

from app import create_app
from config import get_config

app = create_app(os.getenv("FLASK_ENV", "production"))

if not app.debug:
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
    ))
    stream_handler.setLevel(logging.INFO)
    app.logger.addHandler(stream_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info("Viraly startup")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)