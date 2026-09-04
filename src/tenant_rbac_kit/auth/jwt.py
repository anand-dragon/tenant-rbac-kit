from functools import lru_cache

import jwt

from tenant_rbac_kit.auth.schemas import TokenClaims
from tenant_rbac_kit.config import get_settings


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    settings = get_settings()
    jwks_uri = (
        f"{settings.keycloak_server_url}/realms/{settings.keycloak_realm}"
        "/protocol/openid-connect/certs"
    )
    return jwt.PyJWKClient(jwks_uri, cache_keys=True)


def verify_token(token: str) -> TokenClaims:
    """Verify a Keycloak access token's signature and extract claims.

    Raises jwt.PyJWTError (or a subclass) on any validation failure. Callers
    are expected to translate that into a 401 at the API boundary.
    """
    settings = get_settings()
    signing_key = _jwks_client().get_signing_key_from_jwt(token)

    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.keycloak_audience,
        issuer=f"{settings.keycloak_server_url}/realms/{settings.keycloak_realm}",
    )

    return TokenClaims(
        sub=payload["sub"],
        tenant_id=payload["tenant_id"],
        preferred_username=payload.get("preferred_username"),
    )
