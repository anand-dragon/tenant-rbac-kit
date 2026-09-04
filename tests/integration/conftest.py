"""Integration test fixtures: real Postgres and Keycloak containers, not
mocks, since mocking JWT verification would let a broken Keycloak realm
config pass tests while failing for real users.
"""

import json
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


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    with PostgresContainer("postgres:17-alpine", driver="psycopg") as container:
        yield container


def _wait_reachable(url: str, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = httpx.get(url)
            if response.status_code < 500:
                return
        except httpx.TransportError as exc:
            last_error = exc
        time.sleep(1)
    raise TimeoutError(f"{url} not reachable after {timeout}s") from last_error


def _import_realm(url: str) -> None:
    """Imports via Keycloak's admin REST API instead of a launch-time bind
    mount: a wrong host path there silently gets Docker to mount an empty
    directory instead of failing, exactly what happened here once.
    """
    realm_path = Path(__file__).parent.parent.parent / "keycloak" / "realm-export.json"
    realm = json.loads(realm_path.read_text())

    token_response = httpx.post(
        f"{url}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": "admin",
            "password": "admin",
        },
    )
    token_response.raise_for_status()
    admin_token = token_response.json()["access_token"]

    response = httpx.post(
        f"{url}/admin/realms",
        json=realm,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response.raise_for_status()


@pytest.fixture(scope="session")
def keycloak_container() -> Iterator[DockerContainer]:
    container = (
        DockerContainer("quay.io/keycloak/keycloak:26.0")
        .with_env("KEYCLOAK_ADMIN", "admin")
        .with_env("KEYCLOAK_ADMIN_PASSWORD", "admin")
        .with_command(["start-dev"])
        .with_exposed_ports(8080)
    )
    with container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(8080)
        url = f"http://{host}:{port}"
        _wait_reachable(url)
        _import_realm(url)
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
    from tenant_rbac_kit import seed_roles as seed_roles_script
    from tenant_rbac_kit.rbac.enforcer import get_enforcer

    get_enforcer.cache_clear()
    seed_roles_script.main()


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
