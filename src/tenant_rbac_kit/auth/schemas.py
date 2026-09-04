from pydantic import BaseModel


class TokenClaims(BaseModel):
    """Claims from a verified Keycloak token: identity and tenant only, all
    authorization data lives in Casbin (see rbac/enforcer.py).
    """

    sub: str
    tenant_id: str
