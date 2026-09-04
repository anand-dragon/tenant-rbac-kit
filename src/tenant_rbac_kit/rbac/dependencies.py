from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from tenant_rbac_kit.auth.dependencies import get_current_claims
from tenant_rbac_kit.auth.schemas import TokenClaims
from tenant_rbac_kit.rbac.enforcer import has_permission


def require_permission(permission: str) -> Callable[[TokenClaims], TokenClaims]:
    """FastAPI dependency factory for a "resource:action" permission string.

    Generic on purpose: this module has no knowledge of what "invoices" or
    "posts" are. Callers define their own resource:action strings and wire
    them to Casbin policies, this dependency only enforces whatever string
    it is given.

        @router.delete("/invoices/{id}")
        async def delete_invoice(
            claims: TokenClaims = Depends(require_permission("invoices:delete")),
        ): ...
    """
    resource, _, action = permission.partition(":")
    if not resource or not action:
        raise ValueError(f'permission must be "resource:action", got {permission!r}')

    def dependency(claims: TokenClaims = Depends(get_current_claims)) -> TokenClaims:
        if not has_permission(claims.sub, claims.tenant_id, resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return claims

    return dependency
