import { beforeEach, expect, it, vi } from "vitest";
import { api } from "./api";
import { sessionFetch } from "./auth/session";

vi.mock("./auth/session", () => ({ API_BASE: "/api", sessionFetch: vi.fn(), errorMessage: (body, fallback) => body.detail || fallback }));
beforeEach(() => vi.resetAllMocks());

it("preserves PDF bytes through authenticated downloads instead of decoding them as JSON", async () => {
  const blob = new Blob([new Uint8Array([37, 80, 68, 70, 0, 255])], { type: "application/pdf" });
  const text = vi.fn();
  sessionFetch.mockResolvedValue({ ok: true, blob: vi.fn().mockResolvedValue(blob), text });
  expect(await api.candidateInterviewKitExport("2", "3", "pdf")).toBe(blob);
  expect(sessionFetch.mock.calls[0][0]).toBe("/api/candidate/interview-kit/2/export?candidate_id=3&format=pdf");
  expect(text).not.toHaveBeenCalled();
});

it("surfaces export authorization errors without treating the response as a download", async () => {
  const blob = vi.fn();
  sessionFetch.mockResolvedValue({ ok: false, status: 404, text: vi.fn().mockResolvedValue('{"detail":"Resume not found"}'), blob });
  await expect(api.candidateSkillGapExport("2", "99", "csv")).rejects.toThrow("Resume not found");
  expect(blob).not.toHaveBeenCalled();
});

it("sends batch files through multipart form data without setting a JSON content type", async () => {
  sessionFetch.mockResolvedValue({ ok: true, text: vi.fn().mockResolvedValue('{"succeeded":1}') });
  const form = new FormData();
  form.append("files", new File(["resume"], "resume.txt"));
  await api.bulkUploadResumes(form);
  expect(sessionFetch.mock.calls[0][1].body).toBe(form);
  expect(sessionFetch.mock.calls[0][1].headers).not.toHaveProperty("Content-Type");
});
