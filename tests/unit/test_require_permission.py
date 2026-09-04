import pytest

from tenant_rbac_kit.rbac.dependencies import require_permission


def test_valid_permission_string_is_accepted() -> None:
    require_permission("invoices:delete")


@pytest.mark.parametrize("permission", ["invoices", "invoices:", ":delete", ""])
def test_malformed_permission_string_is_rejected(permission: str) -> None:
    with pytest.raises(ValueError, match="resource:action"):
        require_permission(permission)
