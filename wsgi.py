"""WSGI entry point for Viraly platform."""

import os
import logging
from logging.handlers import RotatingFileHandler

from app import create_app
from config import get_config

app = create_app(os.getenv("FLASK_ENV", "production"))

if not app.debug:
    if not os.path.exists("logs"):
        os.mkdir("logs")
    
    file_handler = RotatingFileHandler(
        "logs/viraly.log",
        maxBytes=10240000,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    
    app.logger.setLevel(logging.INFO)
    app.logger.info("Viraly startup")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)