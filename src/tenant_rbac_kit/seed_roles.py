"""One-off script that seeds example Casbin policies for the demo users
defined in keycloak/realm-export.json (alice/tenant-a, bob/tenant-b).

Run via `make seed-roles`. Not part of the request-serving app, so it talks
to the enforcer synchronously rather than through the asyncio.to_thread
wrappers in rbac/enforcer.py.
"""

from tenant_rbac_kit.rbac.enforcer import get_enforcer

# Must match the fixed "id" of each user in keycloak/realm-export.json,
# Keycloak's JWT "sub" claim is the user's UUID, never the username.
ALICE_SUB = "11111111-1111-1111-1111-111111111111"
BOB_SUB = "22222222-2222-2222-2222-222222222222"


def main() -> None:
    enforcer = get_enforcer()

    enforcer.add_policy("admin", "tenant-a", "invoices", "read")
    enforcer.add_policy("admin", "tenant-a", "invoices", "create")
    enforcer.add_policy("admin", "tenant-a", "invoices", "delete")
    enforcer.add_role_for_user_in_domain(ALICE_SUB, "admin", "tenant-a")

    enforcer.add_policy("viewer", "tenant-b", "invoices", "read")
    enforcer.add_role_for_user_in_domain(BOB_SUB, "viewer", "tenant-b")

    print("Seeded: alice=admin@tenant-a, bob=viewer@tenant-b")


if __name__ == "__main__":
    main()
