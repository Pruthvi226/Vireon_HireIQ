from locust import HttpUser, between, task


class HireIQUser(HttpUser):
    wait_time = between(1, 3)
    access_token = ""

    def on_start(self):
        response = self.client.post("/api/auth/login", json={"email": "recruiter@vireon.ai", "password": "recruiter123"})
        if response.ok:
            self.access_token = response.json()["access_token"]

    @task(3)
    def analytics(self):
        self.client.get("/api/analytics/job/1", headers={"Authorization": f"Bearer {self.access_token}"})

    @task(2)
    def rank_candidates(self):
        self.client.get("/api/jobs/1/rank-candidates", headers={"Authorization": f"Bearer {self.access_token}"})