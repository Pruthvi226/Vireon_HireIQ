export const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

function apiPath(path) {
  if (API_BASE === "/api" && path.startsWith("/api/")) {
    return path.slice(4);
  }
  return path;
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${apiPath(path)}`, {
    headers: options.body instanceof FormData ? options.headers : { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json();
}

export const api = {
  health: () => request("/health"),
  seed: () => request("/api/demo/seed", { method: "POST" }),
  candidates: () => request("/api/candidates"),
  jobs: () => request("/api/jobs"),
  createCandidate: (payload) => request("/api/resumes/text", { method: "POST", body: JSON.stringify(payload) }),
  uploadResume: (formData) => request("/api/resumes/upload", { method: "POST", body: formData }),
  createJob: (payload) => request("/api/jobs/create", { method: "POST", body: JSON.stringify(payload) }),
  rank: (jobId) => request(`/api/jobs/${jobId}/rank-candidates`),
  analytics: (jobId) => request(`/api/analytics/job/${jobId}`),
  skillGap: (candidateId, jobId) => request(`/api/candidates/${candidateId}/skill-gap/${jobId}`),
  interview: (candidateId, jobId) =>
    request("/api/interview/generate", {
      method: "POST",
      body: JSON.stringify({ candidate_id: Number(candidateId), job_id: Number(jobId), include_answer_hints: true }),
    }),
  chat: (question, jobId) =>
    request("/api/chat/hr", {
      method: "POST",
      body: JSON.stringify({ question, job_id: jobId ? Number(jobId) : null }),
  }),
  experiment: () => request("/api/model/experiment"),
  reportUrl: (jobId, format = "csv") => `${API_BASE}${apiPath(`/api/reports/job/${jobId}?format=${format}`)}`,
};
