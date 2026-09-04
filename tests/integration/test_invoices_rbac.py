import httpx


async def test_unauthenticated_request_is_rejected(client: httpx.AsyncClient) -> None:
    response = await client.get("/invoices")
    assert response.status_code == 401


async def test_admin_can_create_and_list_own_tenant_invoices(
    client: httpx.AsyncClient, alice_token: str
) -> None:
    headers = {"Authorization": f"Bearer {alice_token}"}

    create = await client.post(
        "/invoices",
        json={"customer_name": "Acme", "amount": "100.00"},
        headers=headers,
    )
    assert create.status_code == 201

    listing = await client.get("/invoices", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["customer_name"] == "Acme"


async def test_viewer_without_create_permission_is_forbidden(
    client: httpx.AsyncClient, bob_token: str
) -> None:
    headers = {"Authorization": f"Bearer {bob_token}"}

    response = await client.post(
        "/invoices",
        json={"customer_name": "Umbrella", "amount": "50.00"},
        headers=headers,
    )
    assert response.status_code == 403


async def test_tenants_do_not_see_each_others_invoices(
    client: httpx.AsyncClient, alice_token: str, bob_token: str
) -> None:
    await client.post(
        "/invoices",
        json={"customer_name": "Acme", "amount": "100.00"},
        headers={"Authorization": f"Bearer {alice_token}"},
    )

    bob_listing = await client.get("/invoices", headers={"Authorization": f"Bearer {bob_token}"})
    assert bob_listing.status_code == 200
    assert bob_listing.json() == []


async def test_admin_can_delete_own_invoice(client: httpx.AsyncClient, alice_token: str) -> None:
    headers = {"Authorization": f"Bearer {alice_token}"}

    create = await client.post(
        "/invoices",
        json={"customer_name": "Acme", "amount": "100.00"},
        headers=headers,
    )
    invoice_id = create.json()["id"]

    delete = await client.delete(f"/invoices/{invoice_id}", headers=headers)
    assert delete.status_code == 204
