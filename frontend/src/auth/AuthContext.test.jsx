import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Login from "../pages/Login";
import { AuthProvider } from "./AuthContext";

function renderLogin() {
  return render(<BrowserRouter><AuthProvider><Login /></AuthProvider></BrowserRouter>);
}

describe("login flow", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("stores the access token and routes the user", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ access_token: "access", user: { id: 1, role: "RECRUITER" } }),
    });
    const user = userEvent.setup();
    renderLogin();
    await user.type(screen.getByLabelText("Email"), "recruiter@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(localStorage.getItem("vireon_token")).toBe("access"));
    expect(screen.getByText("Create an account")).toBeInTheDocument();
  });

  it("renders an authentication error", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue({ ok: false, json: async () => ({ detail: "Invalid credentials" }) });
    const user = userEvent.setup();
    renderLogin();
    await user.type(screen.getByLabelText("Email"), "recruiter@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid credentials");
  });
});
