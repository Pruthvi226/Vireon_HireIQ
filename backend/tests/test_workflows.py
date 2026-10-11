from .conftest import seed_and_login


def test_core_recruiter_workflows_and_admin_views(client):
    headers = seed_and_login(client)
    seeded = client.post("/api/demo/seed", headers=headers).json()
    job_id = seeded["job_id"]
    candidate_id = seeded["ranked"][0]["candidate_id"]
    assert client.get("/health").status_code == 200
    assert client.get("/api/health").status_code == 200
    assert client.get("/ready").status_code == 200
    assert client.get("/api/ready").status_code == 200
    assert client.get("/metrics").status_code == 200
    assert isinstance(client.get("/api/recruiter/jobs", headers=headers).json(), list)
    assert isinstance(client.get("/api/recruiter/candidates", headers=headers).json(), list)
    assert client.get(f"/api/analytics/job/{job_id}", headers=headers).status_code == 200
    assert client.get(f"/api/jobs/{job_id}/rank-candidates", headers=headers).status_code == 200
    assert client.post("/api/chat/hr", headers=headers, json={"question": "Who knows Python and NLP?"}).status_code == 200
    interview = client.post("/api/interview/generate", headers=headers, json={"candidate_id": candidate_id, "job_id": job_id})
    assert interview.status_code == 200
    assert client.get(f"/api/reports/job/{job_id}", headers=headers).status_code == 200
    assert client.get(f"/api/reports/job/{job_id}?format=csv", headers=headers).status_code == 200
    assert client.get(f"/api/candidates/{candidate_id}/skill-gap/{job_id}", headers=headers).status_code == 200
    admin = client.post("/api/auth/login", json={"email": "admin@vireon.ai", "password": "admin123"}).json()
    admin_headers = {"Authorization": f"Bearer {admin['access_token']}"}
    assert client.get("/api/admin/users", headers=admin_headers).status_code == 200
    assert client.get("/api/admin/candidates", headers=admin_headers).status_code == 200
    assert client.get("/api/admin/jobs", headers=admin_headers).status_code == 200
    assert client.get("/api/admin/analytics", headers=admin_headers).status_code == 200
    assert client.get("/api/admin/platform-data", headers=admin_headers).status_code == 200
    assert client.get("/api/system/overview", headers=admin_headers).status_code == 200
    assert client.get("/api/system/audit", headers=admin_headers).status_code == 200


def test_parsing_and_input_validation_helpers(client):
    import app.main as main

    parsed = main.parse_resume("Jane Doe\njane@example.com\nPython, SQL\nProjects: built data API\nEducation: Computer Science")
    assert parsed["email"] == "jane@example.com"
    assert "Python" in parsed["skills"]
    assert main.safe_resume_filename("résumé ../candidate.txt").endswith("candidate.txt")
    main.validate_resume_bytes(b"plain text resume", "resume.txt")
    try:
        main.validate_resume_bytes(b"MZ executable", "resume.txt")
    except ValueError:
        pass
    else:
        raise AssertionError("executable signature should be rejected")
    assert main.cosine("Python FastAPI", "FastAPI Python") > 0
    assert main.percentile([1, 2, 3], 95) == 3
    assert main.pdf_response("Title", ["line"], "test.pdf").media_type == "application/pdf"


def test_rate_limit_redis_failure_falls_back(client, monkeypatch):
    import app.main as main

    class Request:
        class Client:
            host = "coverage-client"
        client = Client()
        url = type("URL", (), {"path": "/health"})()

    monkeypatch.setattr(main, "REDIS_URL", "redis://127.0.0.1:1")
    monkeypatch.setattr(main, "REDIS_CLIENT", None)
    monkeypatch.setattr(main, "RATE_LIMIT_PER_MINUTE", 2)
    assert main.check_rate_limit(Request()) is None
