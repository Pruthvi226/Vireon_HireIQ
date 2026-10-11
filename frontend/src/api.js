import { API_BASE, errorMessage, sessionFetch } from "./auth/session";
export { API_BASE } from "./auth/session";

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

  const response = await sessionFetch(`${API_BASE}${apiPath(path)}`, {
    ...fetchOptions,
    headers,
  });
  const text = await response.text();
  if (!response.ok) {
    let message = text;
    try {
      const parsed = JSON.parse(text);
      message = errorMessage(parsed, "Request failed");
    } catch {
      // Keep the raw server message when it is not JSON.
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
  candidates: (params = {}) => request(`/api/candidates?${new URLSearchParams(params)}`),
  jobs: (params = {}) => request(`/api/jobs?${new URLSearchParams(params)}`),
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
  systemOverview: () => request("/api/system/overview"),
  systemAudit: (limit = 8) => request(`/api/system/audit?limit=${limit}`),
  adminUsers: (params = {}) => request(`/api/admin/users?${new URLSearchParams(params)}`),
  adminCandidates: (params = {}) => request(`/api/admin/candidates?${new URLSearchParams(params)}`),
  adminJobs: (params = {}) => request(`/api/admin/jobs?${new URLSearchParams(params)}`),
  adminAnalytics: () => request("/api/admin/analytics"),
  adminPlatformData: () => request("/api/admin/platform-data"),
  candidateProfile: () => request("/api/candidate/profile"),
  updateStage: (matchId, pipeline_stage) => request(`/api/match/${matchId}/stage`, { method: "PATCH", body: JSON.stringify({ pipeline_stage }) }),
  updateJobStatus: (jobId, status) => request(`/api/jobs/${jobId}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
  candidateAtsScore: (jobId, candidateId) =>
    request(`/api/candidate/ats-score?job_id=${jobId}${candidateId ? `&candidate_id=${candidateId}` : ""}`),
  candidateSkillGap: (jobId, candidateId) =>
    request(`/api/candidate/skill-gap/${jobId}${candidateId ? `?candidate_id=${candidateId}` : ""}`),
  candidateResumeImprovement: (jobId, candidateId) =>
    request(`/api/candidate/resume-improvement/${jobId}${candidateId ? `?candidate_id=${candidateId}` : ""}`),
  reportCsv: (jobId) => request(`/api/reports/job/${jobId}?format=csv`, { responseType: "text" }),
  reportUrl: (jobId, format = "csv") => `${API_BASE}${apiPath(`/api/reports/job/${jobId}?format=${format}`)}`,
};
