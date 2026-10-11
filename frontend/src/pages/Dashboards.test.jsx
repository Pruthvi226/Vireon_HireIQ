import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { api } from "../api";
import CandidateDashboard from "./CandidateDashboard";
import AdminDashboard from "./AdminDashboard";

vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ user: { id: 1, name: "Jane", role: "ADMIN" }, logout: vi.fn() }) }));
vi.mock("../api", () => ({ api: {
  candidateProfile: vi.fn(), jobs: vi.fn(), createCandidate: vi.fn(), candidateAtsScore: vi.fn(), candidateSkillGap: vi.fn(), candidateResumeImprovement: vi.fn(),
  adminUsers: vi.fn(), adminPlatformData: vi.fn(), systemAudit: vi.fn(),
} }));
beforeEach(() => { vi.resetAllMocks(); });

it("lets a candidate save a resume and review evidence for a job", async () => {
  api.candidateProfile.mockResolvedValue({ resumes: [] });
  api.jobs.mockResolvedValue({ items: [{ id: 2, title: "Python Engineer" }], total: 1 });
  api.createCandidate.mockResolvedValue({ id: 3, name: "Jane", created_at: "2026-10-10" });
  api.candidateAtsScore.mockResolvedValue({ ats_score: 68, status: "Maybe", job: { title: "Python Engineer" }, match: { explanation: "Python evidence found" } });
  api.candidateSkillGap.mockResolvedValue({ missing_skills: ["SQL"], roadmap: [] });
  api.candidateResumeImprovement.mockResolvedValue({ suggestions: ["Add measurable SQL project evidence."] });
  const user = userEvent.setup();
  render(<BrowserRouter><CandidateDashboard /></BrowserRouter>);
  await screen.findByText("Save your first resume to unlock a fit review.");
  expect(screen.getByRole("button", { name: "Review my fit" })).toBeDisabled();
  await user.type(screen.getByLabelText("Or paste resume text"), "Jane Doe Python FastAPI backend developer");
  await user.click(screen.getByRole("button", { name: "Save resume" }));
  await screen.findByRole("status");
  await user.click(screen.getByRole("button", { name: "Review my fit" }));
  expect(await screen.findByText("Add measurable SQL project evidence.")).toBeInTheDocument();
  expect(api.candidateAtsScore).toHaveBeenCalledWith("2", "3");
});

it("shows actionable candidate API failures", async () => {
  api.candidateProfile.mockRejectedValue(new Error("Service unavailable"));
  api.jobs.mockResolvedValue({ items: [], total: 0 });
  render(<BrowserRouter><CandidateDashboard /></BrowserRouter>);
  expect(await screen.findByRole("alert")).toHaveTextContent("Service unavailable");
});

it("paginates and searches admin users", async () => {
  api.adminUsers.mockResolvedValue({ items: [{ id: 1, name: "Jane", email: "jane@example.com", role: "CANDIDATE" }], total: 26 });
  api.adminPlatformData.mockResolvedValue({ users: 26, jobs: 2 });
  api.systemAudit.mockResolvedValue([]);
  const user = userEvent.setup();
  render(<BrowserRouter><AdminDashboard /></BrowserRouter>);
  await screen.findByText("jane@example.com");
  await user.click(screen.getByRole("button", { name: "Next" }));
  await waitFor(() => expect(api.adminUsers).toHaveBeenCalledWith({ page: 2, search: "" }));
  await user.type(screen.getByLabelText("Search users"), "Jane");
  await user.click(screen.getByRole("button", { name: "Search" }));
  await waitFor(() => expect(api.adminUsers).toHaveBeenCalledWith({ page: 1, search: "Jane" }));
});
