"""Alembic environment configuration."""

import sys
from logging.config import fileConfig

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

sys.path.insert(0, config.get_main_option("script_location", "."))

import os
os.environ["FLASK_ENV"] = "testing"
os.environ["SQLALCHEMY_DATABASE_URI"] = "sqlite:///viraly_migration.db"

from app import create_app, db as app_db
from models import *

app = create_app("testing")
app.app_context().push()

target_metadata = app_db.metadata


def get_engine():
    """Get database engine."""
    return app_db.engine


def get_engine_url():
    """Get database URL."""
    return get_engine().url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_engine_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()