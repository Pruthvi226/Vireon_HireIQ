export const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

function apiPath(path) {
  if (API_BASE === "/api" && path.startsWith("/api/")) {
    return path.slice(4);
  }
  return path;
}

async function request(path, options = {}) {
  const { responseType, ...fetchOptions } = options;
  const isFormData = fetchOptions.body instanceof FormData;
  const headers = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(fetchOptions.headers || {}),
  };
  const token = localStorage.getItem("vireon_token");
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${apiPath(path)}`, {
    ...fetchOptions,
    headers,
  });
  const text = await response.text();
  if (!response.ok) {
    let message = text;
    try {
      const parsed = JSON.parse(text);
      message = parsed.detail || message;
    } catch {
      // Keep the raw server message when it is not JSON.
    }
    if (response.status === 401) {
      localStorage.removeItem("vireon_token");
      localStorage.removeItem("vireon_user");
    }
    throw new Error(message || `Request failed: ${response.status}`);
  }
  if (responseType === "text") {
    return text;
  }
  return text ? JSON.parse(text) : null;
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
  adminUsers: () => request("/api/admin/users"),
  adminCandidates: () => request("/api/admin/candidates"),
  adminJobs: () => request("/api/admin/jobs"),
  adminAnalytics: () => request("/api/admin/analytics"),
  adminPlatformData: () => request("/api/admin/platform-data"),
  candidateProfile: () => request("/api/candidate/profile"),
  candidateAtsScore: (jobId, candidateId) =>
    request(`/api/candidate/ats-score?job_id=${jobId}${candidateId ? `&candidate_id=${candidateId}` : ""}`),
  candidateSkillGap: (jobId, candidateId) =>
    request(`/api/candidate/skill-gap/${jobId}${candidateId ? `?candidate_id=${candidateId}` : ""}`),
  candidateResumeImprovement: (jobId, candidateId) =>
    request(`/api/candidate/resume-improvement/${jobId}${candidateId ? `?candidate_id=${candidateId}` : ""}`),
  reportCsv: (jobId) => request(`/api/reports/job/${jobId}?format=csv`, { responseType: "text" }),
  reportUrl: (jobId, format = "csv") => `${API_BASE}${apiPath(`/api/reports/job/${jobId}?format=${format}`)}`,
};
