from pydantic import BaseModel


class TokenClaims(BaseModel):
    """Claims pulled from a verified Keycloak access token.

    Keycloak's job here is authentication and tenant identity only, it does
    not carry authorization data. tenant_id is populated by a protocol
    mapper on the Keycloak client, see keycloak/realm-export.json. Role and
    permission data lives entirely in Casbin, addressed by sub + tenant_id,
    see rbac/enforcer.py.
    """

    sub: str
    tenant_id: str
    preferred_username: str | None = None
