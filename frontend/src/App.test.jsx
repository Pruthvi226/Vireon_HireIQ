import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import App from "./App";
import { api } from "./api";

vi.mock("./auth/AuthContext", () => ({ useAuth: () => ({ user: { id: 1, name: "Recruiter", role: "RECRUITER" }, logout: vi.fn() }) }));
vi.mock("./api", () => ({ api: { candidates: vi.fn(), jobs: vi.fn(), experiment: vi.fn(), health: vi.fn(), systemOverview: vi.fn(), skillGap: vi.fn(), interview: vi.fn() } }));

beforeEach(() => {
  vi.resetAllMocks();
  api.candidates.mockResolvedValue({ items: [{ id: 1, name: "Jane", skills: ["Python"], links: [] }], total: 1 });
  api.jobs.mockResolvedValue({ items: [{ id: 2, title: "Engineer", status: "open", required_skills: [], responsibilities: [], tools: [], skill_weightage: {} }], total: 1 });
  api.experiment.mockRejectedValue(new Error("No metrics"));
  api.health.mockResolvedValue({ status: "ok" });
  api.systemOverview.mockResolvedValue({});
  api.skillGap.mockResolvedValue({ strong_skills: ["Python"], partial_skills: [], missing_skills: [], roadmap: [] });
  api.interview.mockResolvedValue({ questions: [] });
});

it("provides keyboard navigation and restores focus after closing candidate insights", async () => {
  const user = userEvent.setup();
  render(<BrowserRouter><App /></BrowserRouter>);
  const navigation = screen.getByRole("button", { name: "Candidates", exact: true });
  navigation.focus();
  await user.keyboard("{Enter}");
  const details = await screen.findByRole("button", { name: "Details" });
  await waitFor(() => expect(screen.getByLabelText("Job context")).toHaveValue("2"));
  await user.click(details);
  const dialog = await screen.findByRole("dialog");
  expect(dialog).toHaveAttribute("aria-modal", "true");
  expect(screen.getByRole("button", { name: "Close candidate insights" })).toHaveFocus();
  await user.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(details).toHaveFocus();
});
