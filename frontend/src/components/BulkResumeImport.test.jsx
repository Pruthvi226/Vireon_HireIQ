import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { api } from "../api";
import BulkResumeImport from "./BulkResumeImport";

vi.mock("../api", () => ({ api: { resumeLimits: vi.fn(), bulkUploadResumes: vi.fn() } }));
beforeEach(() => {
  vi.resetAllMocks();
  api.resumeLimits.mockResolvedValue({ max_resume_bytes: 100, max_bulk_bytes: 200, max_bulk_files: 2, extensions: [".txt", ".pdf", ".docx"], archive_extension: ".zip" });
});

it("imports mixed batches, shows individual errors and refreshes saved candidates", async () => {
  const onImported = vi.fn();
  api.bulkUploadResumes.mockResolvedValue({ succeeded: 1, failed: 1, results: [
    { filename: "jane.txt", status: "success", candidate: { name: "Jane" } },
    { filename: "bad.pdf", status: "error", error: "No readable text found" },
  ] });
  const user = userEvent.setup();
  render(<BulkResumeImport onImported={onImported} />);
  const input = screen.getByLabelText("Batch resume files");
  await waitFor(() => expect(input).toBeEnabled());
  await user.upload(input, [new File(["Jane Python FastAPI developer"], "jane.txt"), new File(["broken"], "bad.pdf")]);
  await user.click(screen.getByRole("button", { name: "Import 2 resumes" }));
  expect(await screen.findByRole("status")).toHaveTextContent("1 imported; 1 failed.");
  expect(screen.getByText(/Failed — No readable text found/)).toBeInTheDocument();
  expect(api.bulkUploadResumes.mock.calls[0][0].getAll("files").map((file) => file.name)).toEqual(["jane.txt", "bad.pdf"]);
  expect(onImported).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("button", { name: "Import selected resumes" })).toBeDisabled();
});

it("uses server file-count and total-byte limits before sending a batch", async () => {
  const user = userEvent.setup();
  render(<BulkResumeImport />);
  const input = screen.getByLabelText("Batch resume files");
  await waitFor(() => expect(input).toBeEnabled());
  await user.upload(input, ["a", "b", "c"].map((name) => new File(["text"], `${name}.txt`)));
  expect(screen.getByRole("alert")).toHaveTextContent("no more than 2 files");
  await user.upload(input, new File(["x".repeat(201)], "resumes.zip"));
  expect(screen.getByRole("alert")).toHaveTextContent("selected batch exceeds");
  expect(api.bulkUploadResumes).not.toHaveBeenCalled();
});

it("preserves saved results when refreshing the list fails and warns against duplicate retries", async () => {
  api.bulkUploadResumes.mockResolvedValue({ succeeded: 1, failed: 0, results: [{ filename: "jane.txt", status: "success" }] });
  const user = userEvent.setup();
  render(<BulkResumeImport onImported={vi.fn().mockRejectedValue(new Error("Offline"))} />);
  const input = screen.getByLabelText("Batch resume files");
  await waitFor(() => expect(input).toBeEnabled());
  await user.upload(input, new File(["Jane Python FastAPI developer"], "jane.txt"));
  await user.click(screen.getByRole("button", { name: "Import 1 resume" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Imports were saved");
  expect(screen.getByRole("status")).toHaveTextContent("1 imported; 0 failed.");
});
