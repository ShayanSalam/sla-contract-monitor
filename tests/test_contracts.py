"""Tests for contract creation, listing, and per-user data isolation."""


def test_create_contract(authenticated_client):
    res = authenticated_client.post(
        "/contracts/",
        json={"title": "Test Vendor Agreement", "raw_text": "Deliver goods by Jan 1, 2027."},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "Test Vendor Agreement"
    assert body["status"] == "uploaded"


def test_list_contracts_returns_only_own_contracts(client, test_user_credentials):
    # User A creates a contract
    client.post("/auth/signup", json=test_user_credentials)
    login_a = client.post(
        "/auth/login",
        data={"username": test_user_credentials["email"], "password": test_user_credentials["password"]},
    )
    token_a = login_a.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token_a}"})
    client.post("/contracts/", json={"title": "User A Contract", "raw_text": "Some text."})

    # User B signs up separately and should see an empty list, not User A's contract
    user_b = {"email": "userb@example.com", "password": "anotherpassword123"}
    client.post("/auth/signup", json=user_b)
    login_b = client.post(
        "/auth/login",
        data={"username": user_b["email"], "password": user_b["password"]},
    )
    token_b = login_b.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token_b}"})

    res = client.get("/contracts/")
    assert res.status_code == 200
    assert res.json() == []  # User B must not see User A's contract


def test_get_nonexistent_contract_returns_404(authenticated_client):
    res = authenticated_client.get("/contracts/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404


def test_create_manual_obligation(authenticated_client):
    contract_res = authenticated_client.post(
        "/contracts/", json={"title": "Test Contract", "raw_text": "Some text."}
    )
    contract_id = contract_res.json()["id"]

    res = authenticated_client.post(
        "/obligations/",
        json={
            "contract_id": contract_id,
            "description": "Submit quarterly report",
            "deadline": "2027-01-01T00:00:00",
            "penalty_amount": 500,
            "penalty_currency": "USD",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["description"] == "Submit quarterly report"
    assert body["status"] == "pending"
    assert body["is_ai_extracted"] is False


def test_mark_obligation_completed(authenticated_client):
    contract_res = authenticated_client.post(
        "/contracts/", json={"title": "Test Contract", "raw_text": "Some text."}
    )
    contract_id = contract_res.json()["id"]
    ob_res = authenticated_client.post(
        "/obligations/",
        json={
            "contract_id": contract_id,
            "description": "Deliver goods",
            "deadline": "2027-01-01T00:00:00",
        },
    )
    obligation_id = ob_res.json()["id"]

    res = authenticated_client.patch(
        f"/obligations/{obligation_id}/status", json={"status": "completed"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "completed"
