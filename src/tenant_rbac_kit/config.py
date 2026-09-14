from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+psycopg://tenant_rbac:tenant_rbac@localhost:5432/tenant_rbac"

    keycloak_server_url: str = "http://localhost:8080"
    # Issuer as it appears in tokens. Differs from server_url when the API
    # reaches Keycloak over an internal hostname (e.g. compose) but tokens
    # are minted via the public one. Defaults to server_url.
    keycloak_issuer_url: str | None = None
    keycloak_realm: str = "tenant-rbac-kit"
    keycloak_client_id: str = "tenant-rbac-api"
    keycloak_audience: str = "tenant-rbac-api"

    casbin_model_path: str = "casbin/model.conf"

    @property
    def keycloak_issuer(self) -> str:
        base = self.keycloak_issuer_url or self.keycloak_server_url
        return f"{base}/realms/{self.keycloak_realm}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
