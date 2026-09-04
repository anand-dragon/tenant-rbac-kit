from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from tenant_rbac_kit.config import get_settings
from tenant_rbac_kit.db.base import Base
from tenant_rbac_kit.models import Invoice  # noqa: F401  (registers metadata)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata


# Alembic runs migrations synchronously; psycopg3 supports both sync and
# async through the same dialect, so this reuses the app's own URL.
connectable = engine_from_config(
    config.get_section(config.config_ini_section, {}),
    prefix="sqlalchemy.",
    poolclass=pool.NullPool,
)
with connectable.connect() as connection:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
