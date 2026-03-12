"""
Alembic environment configuration.

Uses async SQLAlchemy engine to run migrations.
Imports all models so that Alembic's autogenerate can detect changes.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.models import Base

# Import all models so they register with Base.metadata
from app.models.user import User  # noqa: F401
from app.models.property import Property  # noqa: F401
from app.models.payment import Payment  # noqa: F401
from app.models.job import Job  # noqa: F401
from app.models.inspection import Inspection  # noqa: F401
from app.models.kyc import KycDocument  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.supporting import Dispute, BankAccount, Message, AuditLog  # noqa: F401
from app.models.agreement import Agreement  # noqa: F401

# Alembic Config object
config = context.config

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generates SQL script without DB connection."""
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Execute migrations against the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connects to DB asynchronously."""
    connectable = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
