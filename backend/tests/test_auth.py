from .conftest import seed_and_login


def test_auth_requires_credentials(client):
    assert client.get("/api/candidates").status_code == 401


def test_refresh_rotation_and_logout(client):
    client.post("/api/demo/seed-users")
    login = client.post("/api/auth/login", json={"email": "recruiter@vireon.ai", "password": "recruiter123"})
    refresh = login.json()["refresh_token"]
    rotated = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert rotated.status_code == 200
    assert client.post("/api/auth/refresh", json={"refresh_token": refresh}).status_code == 401
    headers = {"Authorization": f"Bearer {rotated.json()['access_token']}"}
    assert client.post("/api/auth/logout", headers=headers).status_code == 200


def test_account_lockout(client):
    client.post("/api/demo/seed-users")
    for _ in range(5):
        assert client.post("/api/auth/login", json={"email": "recruiter@vireon.ai", "password": "wrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "recruiter@vireon.ai", "password": "recruiter123"}).status_code == 423


def test_password_reset_is_single_use(client):
    client.post("/api/demo/seed-users")
    request = client.post("/api/auth/password-reset/request", json={"email": "recruiter@vireon.ai"})
    token = request.json()["reset_token"]
    assert client.post("/api/auth/password-reset/confirm", json={"token": token, "password": "newpassword123"}).status_code == 200
    assert client.post("/api/auth/password-reset/confirm", json={"token": token, "password": "newpassword456"}).status_code == 400
    assert client.post("/api/auth/login", json={"email": "recruiter@vireon.ai", "password": "newpassword123"}).status_code == 200
