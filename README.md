# tenant-rbac-kit

A reference implementation for multi-tenant RBAC in FastAPI: Keycloak handles
authentication and tenant identity, Casbin handles authorization. Clone it,
delete the demo `invoices` resource, wire `require_permission` into your own
routes.

## Why this exists

Keycloak + FastAPI + RBAC starter kits on GitHub are either abandoned toy
repos (a handful of stars, no CI, hardcoded to one business domain) or
generic SaaS boilerplates that bolt on a specific ORM schema per resource.
This kit takes a narrower, reusable position: authorization is expressed as
plain `"resource:action"` strings, not application-specific database tables,
so it drops into any domain without modification.

## Architecture

- **Authentication and tenant identity: Keycloak.** A verified JWT proves
  who the caller is (`sub`) and which tenant they belong to (`tenant_id`,
  via a protocol mapper on a user attribute, see
  [`keycloak/realm-export.json`](keycloak/realm-export.json)). Keycloak
  roles are not used for authorization here, see the note below.
- **Authorization: Casbin**, using the `rbac_with_domains` model
  ([`casbin/model.conf`](casbin/model.conf)). Casbin owns role assignment
  (`user -> role, per tenant`) and role-to-permission policy
  (`role -> resource:action, per tenant`) as the single source of truth,
  stored in Postgres via `casbin-sqlalchemy-adapter`.
- **Enforcement point:** one FastAPI dependency,
  `require_permission("resource:action")`
  ([`src/tenant_rbac_kit/rbac/dependencies.py`](src/tenant_rbac_kit/rbac/dependencies.py)).
  It has no knowledge of what a "resource" is, define your own strings.

```python
@router.delete("/invoices/{id}")
async def delete_invoice(
    claims: TokenClaims = Depends(require_permission("invoices:delete")),
): ...
```

### Why not use Keycloak's own realm/client roles for authorization

Keycloak roles and Casbin roles would be two overlapping systems answering
the same question. This kit picks one: Keycloak proves identity and tenant
membership, Casbin owns every authorization decision. Simpler mental model,
and role changes take effect immediately without a token refresh, since
Casbin is checked per-request rather than baked into the JWT at login time.

### Why Casbin over a hand-rolled permission table

Casbin's `rbac_with_domains` model already solves tenant-scoped role
inheritance correctly (role hierarchies, domain-scoped grants, policy
storage). Re-implementing that is real complexity with edge cases, not a
few lines. See [`casbin/model.conf`](casbin/model.conf).

### Why the Casbin adapter is synchronous in an otherwise fully async app

Casbin loads all policies into memory once at startup, `enforce()` on the
request hot path is a pure in-memory check, no DB round trip. Only policy
*writes* (granting or revoking a role) touch the database, and those go
through `asyncio.to_thread` (see
[`rbac/enforcer.py`](src/tenant_rbac_kit/rbac/enforcer.py)). The
maintained sync adapter (`pycasbin/sqlalchemy-adapter`) was chosen over the
async one, which has a fraction of the adoption and has seen less recent
activity.

## Stack

| Layer | Choice |
|---|---|
| Language | Python 3.13 |
| Package manager | [uv](https://github.com/astral-sh/uv) |
| Framework | FastAPI, fully async |
| DB driver | psycopg3 (one driver for both the async app and sync Alembic migrations) |
| ORM / migrations | SQLAlchemy 2.0 + Alembic |
| AuthN | Keycloak (OIDC/JWT), verified via `PyJWT` + JWKS |
| AuthZ | Casbin, `rbac_with_domains` model |
| Lint / format | Ruff ([`ruff.toml`](ruff.toml)) |
| Type checking | mypy, strict ([`mypy.ini`](mypy.ini)) |
| Tests | pytest + testcontainers (real Postgres and Keycloak, not mocks) |
| Task runner | Makefile (no extra install required to run it) |

## Running it

```bash
make up          # docker compose up + migrate
make seed-roles  # seed the demo alice/tenant-a and bob/tenant-b policies
make test
```

`make up` starts Postgres, Keycloak (auto-importing the realm in
[`keycloak/realm-export.json`](keycloak/realm-export.json)), and the API,
then runs migrations. Two demo users exist out of the box:

| User | Tenant | Role | Password |
|---|---|---|---|
| alice | tenant-a | admin (read/create/delete invoices) | alice |
| bob | tenant-b | viewer (read only) | bob |

Get a token and call the API:

```bash
TOKEN=$(curl -s -X POST \
  http://localhost:8080/realms/tenant-rbac-kit/protocol/openid-connect/token \
  -d grant_type=password -d client_id=tenant-rbac-api -d client_secret=dev-secret \
  -d username=alice -d password=alice | jq -r .access_token)

curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/invoices
```

## Testing philosophy

This is auth/RBAC code meant to be copied into other projects. Mocking JWT
verification would let a broken Keycloak realm config (wrong audience,
missing `tenant_id` mapper, wrong issuer) pass CI while failing for every
real user. The integration suite runs against real Postgres and Keycloak
containers via `testcontainers`, see
[`tests/conftest.py`](tests/conftest.py). This is slower (~30-40s to boot
Keycloak) than mocking, that cost is intentional.

## Using this in your own project

1. Replace [`src/tenant_rbac_kit/models/invoice.py`](src/tenant_rbac_kit/models/invoice.py)
   and [`api/routes/invoices.py`](src/tenant_rbac_kit/api/routes/invoices.py)
   with your own resources.
2. Call `require_permission("your_resource:your_action")` on each route.
3. Grant roles via `rbac/enforcer.py`'s `grant_role(user_id, role, tenant_id)`,
   and define what each role can do with `enforcer.add_policy(role, tenant_id, resource, action)`.
4. Point `keycloak/realm-export.json` at your own realm, only the
   `tenant_id` protocol mapper is required.
