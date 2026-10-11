import io
import zipfile

import pytest

import app.main as main
from .conftest import seed_and_login


def test_upload_limits_require_auth_and_reflect_server_configuration(client, monkeypatch):
    assert client.get("/api/resumes/limits").status_code == 401
    headers = seed_and_login(client, "candidate@vireon.ai", "candidate123")
    monkeypatch.setattr(main, "MAX_RESUME_BYTES", 123)
    monkeypatch.setattr(main, "MAX_BULK_BYTES", 615)
    response = client.get("/api/resumes/limits", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"max_resume_bytes": 123, "max_bulk_bytes": 615,
                               "max_bulk_files": 25, "extensions": [".txt", ".pdf", ".docx"],
                               "archive_extension": ".zip"}


def test_oversized_batch_rejects_before_saving_any_document(client, monkeypatch):
    headers = seed_and_login(client)
    monkeypatch.setattr(main, "MAX_BULK_BYTES", 80)
    response = client.post("/api/resumes/bulk", headers=headers, files=[
        ("files", ("valid.txt", b"Jane Python FastAPI SQL developer experience")),
        ("files", ("large.txt", b"x" * 81)),
    ])
    assert response.status_code == 413
    assert client.get("/api/candidates", headers=headers).json()["total"] == 0
    assert not list(main.RESUME_DIR.iterdir())


def test_archive_expansion_budget_is_shared_across_the_whole_batch(client, monkeypatch):
    headers = seed_and_login(client)
    monkeypatch.setattr(main, "MAX_BULK_BYTES", 1000)
    archives = []
    for name in ("first", "second"):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(f"{name}.txt", (f"{name} Python FastAPI SQL developer experience\n" * 15)[:600])
        archives.append(("files", (f"{name}.zip", buffer.getvalue(), "application/zip")))
    response = client.post("/api/resumes/bulk", headers=headers, files=archives)
    assert response.status_code == 200
    result = response.json()
    assert result["succeeded"] == 1 and result["failed"] == 1
    assert "byte budget" in result["results"][1]["error"]
    assert client.get("/api/candidates", headers=headers).json()["total"] == 1


@pytest.mark.parametrize("kind", ["skill-gap", "interview-kit"])
@pytest.mark.parametrize("format", ["csv", "pdf"])
def test_candidate_exports_bind_to_the_owned_resume_and_job(client, kind, format):
    recruiter = seed_and_login(client)
    seeded = client.post("/api/demo/seed", headers=recruiter).json()
    candidate = seed_and_login(client, "candidate@vireon.ai", "candidate123")
    own = client.post("/api/resumes/text", headers=candidate, json={"name": "Jane", "resume_text": "Jane Python FastAPI SQL developer project experience"}).json()
    path = f"/api/candidate/{kind}/{seeded['job_id']}/export"
    foreign_id = seeded["ranked"][0]["candidate_id"]
    assert client.get(path, headers=candidate, params={"candidate_id": foreign_id, "format": format}).status_code == 404
    response = client.get(path, headers=candidate, params={"candidate_id": own["id"], "format": format})
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    if format == "pdf":
        import fitz
        with fitz.open(stream=response.content, filetype="pdf") as document:
            assert document.page_count > 0
            assert document[0].get_text().strip()
    else:
        assert response.headers["content-type"].startswith("text/csv")
        assert len(response.text.splitlines()) > 1
