from __future__ import annotations

import argparse
import json
import time
import uuid
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class SmokeResult:
    feature: str
    status: str
    detail: object
    ms: float


class SmokeClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.results: list[SmokeResult] = []

    def request(
        self,
        method: str,
        path: str,
        body: object | bytes | None = None,
        token: str | None = None,
        headers: dict[str, str] | None = None,
        expected: int = 200,
    ) -> object:
        headers = dict(headers or {})
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = None
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
        elif isinstance(body, bytes):
            data = body

        request = Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read()
                status = response.status
                content_type = response.headers.get("Content-Type", "")
                text = raw.decode("utf-8", errors="replace")
                parsed = json.loads(text) if text and "json" in content_type else text
        except HTTPError as exc:
            raw = exc.read()
            status = exc.code
            text = raw.decode("utf-8", errors="replace")
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = text
        except URLError as exc:
            raise AssertionError(f"{method} {path} unreachable: {exc}") from exc

        if status != expected:
            raise AssertionError(f"{method} {path} expected {expected}, got {status}: {parsed}")
        return parsed

    def record(self, feature: str, callback):
        started = time.perf_counter()
        try:
            detail = callback()
        except Exception as exc:
            result = SmokeResult(feature, "FAIL", str(exc), round((time.perf_counter() - started) * 1000, 1))
            self.results.append(result)
            raise
        result = SmokeResult(feature, "PASS", detail, round((time.perf_counter() - started) * 1000, 1))
        self.results.append(result)
        return detail

    def login(self, email: str, password: str) -> dict:
        payload = self.request("POST", "/api/auth/login", {"email": email, "password": password})
        assert isinstance(payload, dict) and payload.get("access_token"), "missing auth token"
        return payload

    def multipart_resume(self, token: str) -> dict:
        boundary = "----VireonSmokeBoundary"
        file_body = (
            "Smoke Upload Candidate\nPython FastAPI SQL NLP Docker\n"
            "Projects: uploaded resume parsing test with recruiter evidence."
        ).encode("utf-8")
        body = b"".join(
            [
                f'--{boundary}\r\nContent-Disposition: form-data; name="candidate_name"\r\n\r\nSmoke Upload Candidate\r\n'.encode(),
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="smoke_resume.txt"\r\nContent-Type: text/plain\r\n\r\n'.encode()
                + file_body
                + b"\r\n",
                f"--{boundary}--\r\n".encode(),
            ]
        )
        payload = self.request(
            "POST",
            "/api/resumes/upload",
            body,
            token=token,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        assert isinstance(payload, dict) and payload.get("name") == "Smoke Upload Candidate", "upload candidate mismatch"
        return payload

    def run(self) -> list[SmokeResult]:
        health = self.record("Health endpoint", lambda: self.request("GET", "/health"))
        assert isinstance(health, dict) and health.get("status") == "ok", "health is not ok"
        ready = self.record("Readiness endpoint", lambda: self.request("GET", "/api/ready"))
        assert isinstance(ready, dict) and ready.get("status") == "ready", "api is not ready"

        seed = self.record("Demo seed", lambda: self.request("POST", "/api/demo/seed"))
        assert isinstance(seed, dict) and len(seed.get("ranked", [])) >= 3, "demo seed did not rank candidates"

        admin_auth = self.record("Admin login", lambda: self.login("admin@vireon.ai", "admin123"))
        recruiter_auth = self.record("Recruiter login", lambda: self.login("recruiter@vireon.ai", "recruiter123"))
        candidate_auth = self.record("Candidate login", lambda: self.login("candidate@vireon.ai", "candidate123"))
        admin = admin_auth["access_token"]
        recruiter = recruiter_auth["access_token"]
        candidate = candidate_auth["access_token"]

        self.record("Auth me", lambda: [self.request("GET", "/api/auth/me", token=t)["role"] for t in [admin, recruiter, candidate]])
        unique = uuid.uuid4().hex[:8]
        self.record(
            "Register new user",
            lambda: self.request(
                "POST",
                "/api/auth/register",
                {
                    "name": f"Smoke Candidate {unique}",
                    "email": f"smoke-{unique}@vireon.ai",
                    "password": "smoke12345",
                    "role": "CANDIDATE",
                    "company_name": "Smoke Labs",
                },
            )["user"]["role"],
        )

        self.record("Model experiment", lambda: self.request("GET", "/api/model/experiment", token=recruiter)["model_name"])
        self.record("List jobs", lambda: len(self.request("GET", "/api/jobs", token=recruiter)))
        self.record("List candidates", lambda: len(self.request("GET", "/api/candidates", token=recruiter)))

        new_job = self.record(
            "Create job",
            lambda: self.request(
                "POST",
                "/api/jobs/create",
                {
                    "title": "Senior AI Platform Engineer",
                    "company": "Vireon Scale Labs",
                    "description": (
                        "Build FastAPI services, NLP ranking pipelines, SQL analytics, Docker deployments, "
                        "model evaluation, RAG retrieval, and recruiter dashboards. Requires Python, FastAPI, SQL, "
                        "Machine Learning, NLP, Docker, REST API, Pandas, Scikit-learn and Model Evaluation. "
                        "Hybrid role with documentation and metrics ownership."
                    ),
                },
                token=recruiter,
            ),
        )
        new_candidate = self.record(
            "Create candidate from text",
            lambda: self.request(
                "POST",
                "/api/resumes/text",
                {
                    "name": "Smoke Candidate",
                    "resume_text": (
                        "Smoke Candidate smoke@example.com Python FastAPI SQL Docker REST API Pandas Scikit-learn NLP Machine Learning. "
                        "Projects: Built recruiter dashboards, ranking APIs, RAG candidate retrieval and model evaluation reports. "
                        "Experience: backend AI platform intern building data preprocessing and analytics services. Education: Computer Science."
                    ),
                },
                token=recruiter,
            ),
        )
        job_id = new_job["id"]
        candidate_id = new_candidate["id"]

        self.record("Match candidate", lambda: self.request("POST", "/api/match/candidate", {"candidate_id": candidate_id, "job_id": job_id, "bias_safe": True}, token=recruiter)["final_score"])
        self.record("Rank candidates", lambda: len(self.request("GET", f"/api/jobs/{job_id}/rank-candidates", token=recruiter)))
        self.record("Analytics", lambda: self.request("GET", f"/api/analytics/job/{job_id}", token=recruiter)["total_candidates"])
        self.record("Skill gap", lambda: self.request("GET", f"/api/candidates/{candidate_id}/skill-gap/{job_id}", token=recruiter)["missing_skills"])
        self.record("Interview kit", lambda: len(self.request("POST", "/api/interview/generate", {"candidate_id": candidate_id, "job_id": job_id, "include_answer_hints": True}, token=recruiter)["questions"]))
        self.record("HR chat", lambda: len(self.request("POST", "/api/chat/hr", {"question": "Who has FastAPI and NLP evidence?", "job_id": job_id}, token=recruiter)["evidence"]))
        self.record("CSV report", lambda: self.request("GET", f"/api/reports/job/{job_id}?format=csv", token=recruiter).splitlines()[0])
        self.record("Upload resume file", lambda: self.multipart_resume(recruiter)["id"])

        self.record(
            "Candidate upload own resume",
            lambda: self.request(
                "POST",
                "/api/resumes/text",
                {
                    "name": "Demo Candidate Owned Resume",
                    "resume_text": (
                        "Demo Candidate Owned Resume candidate@example.com Python FastAPI SQL NLP Pandas. "
                        "Projects: candidate self service upload and ATS score review. Education: Computer Science."
                    ),
                },
                token=candidate,
            )["owner_user_id"],
        )
        self.record("Candidate profile", lambda: len(self.request("GET", "/api/candidate/profile", token=candidate)["resumes"]))
        self.record("Candidate ATS score", lambda: self.request("GET", f"/api/candidate/ats-score?job_id={job_id}", token=candidate)["ats_score"])
        self.record("Candidate skill gap", lambda: self.request("GET", f"/api/candidate/skill-gap/{job_id}", token=candidate)["missing_skills"])
        self.record("Candidate resume improvement", lambda: self.request("GET", f"/api/candidate/resume-improvement/{job_id}", token=candidate)["suggestions"])

        self.record("Admin users", lambda: len(self.request("GET", "/api/admin/users", token=admin)))
        self.record("Admin candidates", lambda: len(self.request("GET", "/api/admin/candidates", token=admin)))
        self.record("Admin jobs", lambda: len(self.request("GET", "/api/admin/jobs", token=admin)))
        self.record("Admin analytics", lambda: self.request("GET", "/api/admin/analytics", token=admin)["matches"])
        self.record("Admin platform data", lambda: self.request("GET", "/api/admin/platform-data", token=admin)["audit_events"])
        self.record("Recruiter dashboard", lambda: self.request("GET", "/api/recruiter/dashboard", token=recruiter)["job_count"])
        self.record("Recruiter jobs alias", lambda: len(self.request("GET", "/api/recruiter/jobs", token=recruiter)))
        self.record("Recruiter candidates alias", lambda: len(self.request("GET", "/api/recruiter/candidates", token=recruiter)))
        self.record("Recruiter analytics alias", lambda: self.request("GET", f"/api/recruiter/analytics/{job_id}", token=recruiter)["total_candidates"])
        self.record("System overview", lambda: self.request("GET", "/api/system/overview", token=recruiter)["service"]["version"])
        self.record("System audit", lambda: len(self.request("GET", "/api/system/audit?limit=20", token=admin)))

        self.record("RBAC candidate cannot list all candidates", lambda: self.request("GET", "/api/candidates", token=candidate, expected=403)["detail"])
        self.record("RBAC candidate cannot admin users", lambda: self.request("GET", "/api/admin/users", token=candidate, expected=403)["detail"])
        self.record("RBAC recruiter cannot read audit", lambda: self.request("GET", "/api/system/audit?limit=1", token=recruiter, expected=403)["detail"])
        self.record("Unauthenticated jobs denied", lambda: self.request("GET", "/api/jobs", expected=401)["detail"])
        return self.results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Vireon HireIQ end-to-end API smoke tests against a live server.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL of the running API server")
    parser.add_argument("--json", action="store_true", help="Print full JSON result details")
    args = parser.parse_args()

    client = SmokeClient(args.base_url)
    try:
        results = client.run()
    except Exception:
        if args.json:
            print(json.dumps({"summary": {"passed": sum(item.status == "PASS" for item in client.results), "failed": 1}, "results": [item.__dict__ for item in client.results]}, indent=2))
        raise

    payload = {"summary": {"passed": len(results), "failed": 0}, "results": [item.__dict__ for item in results]}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Smoke OK: {len(results)} checks passed against {args.base_url}")
        slowest = sorted(results, key=lambda item: item.ms, reverse=True)[:5]
        for item in slowest:
            print(f"  {item.feature}: {item.ms} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
