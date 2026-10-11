import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import ProtectedRoute from "./ProtectedRoute";
import { AuthProvider } from "./AuthContext";

describe("ProtectedRoute", () => {
  it("redirects unauthenticated users to login", () => {
    localStorage.clear();
    render(<MemoryRouter initialEntries={["/recruiter"]}><AuthProvider><ProtectedRoute allowedRoles={["RECRUITER"]}><p>private</p></ProtectedRoute></AuthProvider></MemoryRouter>);
    expect(screen.queryByText("private")).not.toBeInTheDocument();
  });
});