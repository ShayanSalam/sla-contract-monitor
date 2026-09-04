"""Tests for signup/login and JWT-protected access."""


def test_signup_creates_user(client, test_user_credentials):
    res = client.post("/auth/signup", json=test_user_credentials)
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == test_user_credentials["email"]
    assert "id" in body
    assert "password" not in body  # never leak the password back, hashed or not


def test_signup_rejects_duplicate_email(client, test_user_credentials):
    client.post("/auth/signup", json=test_user_credentials)
    res = client.post("/auth/signup", json=test_user_credentials)
    assert res.status_code == 400


def test_login_succeeds_with_correct_credentials(client, test_user_credentials):
    client.post("/auth/signup", json=test_user_credentials)
    res = client.post(
        "/auth/login",
        data={"username": test_user_credentials["email"], "password": test_user_credentials["password"]},
    )
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_fails_with_wrong_password(client, test_user_credentials):
    client.post("/auth/signup", json=test_user_credentials)
    res = client.post(
        "/auth/login",
        data={"username": test_user_credentials["email"], "password": "wrong-password"},
    )
    assert res.status_code == 401


def test_login_fails_for_unknown_email(client):
    res = client.post(
        "/auth/login",
        data={"username": "nobody@example.com", "password": "whatever"},
    )
    assert res.status_code == 401


def test_protected_route_rejects_missing_token(client):
    res = client.get("/contracts/")
    assert res.status_code == 401


def test_protected_route_accepts_valid_token(authenticated_client):
    res = authenticated_client.get("/contracts/")
    assert res.status_code == 200
    assert res.json() == []
