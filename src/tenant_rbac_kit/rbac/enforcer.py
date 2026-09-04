import asyncio
from functools import lru_cache

import casbin
import casbin_sqlalchemy_adapter

from tenant_rbac_kit.config import get_settings


@lru_cache
def get_enforcer() -> casbin.Enforcer:
    """Casbin caches all policies in memory, so enforce() never blocks on the
    DB; only writes (grant_role/revoke_role below) do, via asyncio.to_thread.
    """
    settings = get_settings()
    # psycopg3 supports both sync and async through the same dialect URL,
    # so the adapter's plain sync engine reuses the app's connection string.
    adapter = casbin_sqlalchemy_adapter.Adapter(settings.database_url)
    return casbin.Enforcer(settings.casbin_model_path, adapter)


def has_permission(user_id: str, tenant_id: str, resource: str, action: str) -> bool:
    # casbin ships no type stubs, enforce() is untyped at the mypy boundary
    # even though it returns an actual bool at runtime.
    return bool(get_enforcer().enforce(user_id, tenant_id, resource, action))


async def grant_role(user_id: str, role: str, tenant_id: str) -> None:
    await asyncio.to_thread(get_enforcer().add_role_for_user_in_domain, user_id, role, tenant_id)


async def revoke_role(user_id: str, role: str, tenant_id: str) -> None:
    await asyncio.to_thread(get_enforcer().delete_role_for_user_in_domain, user_id, role, tenant_id)
