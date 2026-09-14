from tenant_rbac_kit.config import Settings


def test_issuer_defaults_to_server_url() -> None:
    s = Settings(keycloak_server_url="http://keycloak:8080", keycloak_realm="r")
    assert s.keycloak_issuer == "http://keycloak:8080/realms/r"


def test_issuer_url_overrides_server_url() -> None:
    s = Settings(
        keycloak_server_url="http://keycloak:8080",
        keycloak_issuer_url="http://localhost:8080",
        keycloak_realm="r",
    )
    assert s.keycloak_issuer == "http://localhost:8080/realms/r"
