"""Integration test fixtures.

These tests run against real Postgres and Keycloak containers, not mocks.
This is an auth/RBAC reference kit, mocking JWT verification would let a
broken Keycloak realm config (wrong audience, missing tenant_id mapper,
wrong issuer) pass tests while failing for real users, exactly the kind of
gap that should not exist in code meant to be copied into other projects.
"""

import os
import subprocess
import time
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import httpx
import pytest
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer

from tenant_rbac_kit.config import get_settings

ALICE_SUB = "11111111-1111-1111-1111-111111111111"
BOB_SUB = "22222222-2222-2222-2222-222222222222"


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    with PostgresContainer("postgres:17-alpine", driver="psycopg") as container:
        yield container


def _wait_for_realm(url: str, timeout: float = 120) -> None:
    """Poll the realm's discovery endpoint directly rather than matching a
    log line. Keycloak's JVM logging interleaves stdout/stderr with enough
    buffering jitter that a "server started" line can be observed before a
    slightly-earlier "realm imported" line actually flushes, so log-order
    matching is racy for import completion. Polling the real endpoint checks
    the actual condition the tests depend on.

    The generous timeout is deliberate: when a second dynamically-published
    container's port comes up shortly after another (Postgres, here), some
    Docker Desktop networking setups take several seconds, occasionally
    longer, to route traffic to it correctly, and every attempt in that
    window fails as a connection reset rather than a refusal. That is an
    environment characteristic, not an application bug, confirmed by the
    same container's own logs showing a clean boot and realm import in
    under five seconds every time.
    """
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{url}/realms/tenant-rbac-kit/.well-known/openid-configuration")
            if response.status_code == 200:
                return
        except httpx.TransportError as exc:
            last_error = exc
        time.sleep(1)
    raise TimeoutError(f"tenant-rbac-kit realm not ready after {timeout}s") from last_error


@pytest.fixture(scope="session")
def keycloak_container() -> Iterator[DockerContainer]:
    realm_export = str((Path(__file__).parent.parent / "keycloak" / "realm-export.json").resolve())
    container = (
        DockerContainer("quay.io/keycloak/keycloak:26.0")
        .with_env("KEYCLOAK_ADMIN", "admin")
        .with_env("KEYCLOAK_ADMIN_PASSWORD", "admin")
        .with_command(["start-dev", "--import-realm"])
        .with_volume_mapping(realm_export, "/opt/keycloak/data/import/realm-export.json", "ro")
        .with_exposed_ports(8080)
    )
    with container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(8080)
        try:
            _wait_for_realm(f"http://{host}:{port}")
        except TimeoutError:
            print("=== keycloak container logs on timeout ===", flush=True)
            print(container.get_logs()[0].decode(errors="replace"), flush=True)
            print(container.get_logs()[1].decode(errors="replace"), flush=True)
            raise
        yield container


@pytest.fixture(scope="session")
def keycloak_url(keycloak_container: DockerContainer) -> str:
    host = keycloak_container.get_container_host_ip()
    port = keycloak_container.get_exposed_port(8080)
    return f"http://{host}:{port}"


@pytest.fixture(scope="session", autouse=True)
def configure_settings(postgres_container: PostgresContainer, keycloak_url: str) -> Iterator[None]:
    os.environ["DATABASE_URL"] = postgres_container.get_connection_url()
    os.environ["KEYCLOAK_SERVER_URL"] = keycloak_url
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def run_migrations(configure_settings: None) -> None:
    subprocess.run(
        ["uv", "run", "alembic", "-c", "alembic/alembic.ini", "upgrade", "head"], check=True
    )


@pytest.fixture(scope="session")
def seed_roles(run_migrations: None) -> None:
    from tenant_rbac_kit.rbac.enforcer import get_enforcer

    get_enforcer.cache_clear()
    enforcer = get_enforcer()
    enforcer.add_policy("admin", "tenant-a", "invoices", "read")
    enforcer.add_policy("admin", "tenant-a", "invoices", "create")
    enforcer.add_policy("admin", "tenant-a", "invoices", "delete")
    enforcer.add_role_for_user_in_domain(ALICE_SUB, "admin", "tenant-a")

    enforcer.add_policy("viewer", "tenant-b", "invoices", "read")
    enforcer.add_role_for_user_in_domain(BOB_SUB, "viewer", "tenant-b")


async def _password_grant(keycloak_url: str, username: str, password: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{keycloak_url}/realms/tenant-rbac-kit/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "tenant-rbac-api",
                "client_secret": "dev-secret",
                "username": username,
                "password": password,
            },
        )
        if response.is_error:
            raise RuntimeError(f"token request failed: {response.status_code} {response.text}")
        return response.json()["access_token"]


@pytest.fixture
async def alice_token(keycloak_url: str, seed_roles: None) -> str:
    return await _password_grant(keycloak_url, "alice", "alice")


@pytest.fixture
async def bob_token(keycloak_url: str, seed_roles: None) -> str:
    return await _password_grant(keycloak_url, "bob", "bob")


@pytest.fixture(autouse=True)
async def _clean_invoices(run_migrations: None) -> AsyncIterator[None]:
    yield
    from sqlalchemy import delete

    from tenant_rbac_kit.db.session import async_session
    from tenant_rbac_kit.models.invoice import Invoice

    async with async_session() as session:
        await session.execute(delete(Invoice))
        await session.commit()


@pytest.fixture
async def client(seed_roles: None) -> AsyncIterator[httpx.AsyncClient]:
    from tenant_rbac_kit.main import create_app

    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
