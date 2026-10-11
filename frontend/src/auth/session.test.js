import { beforeEach, expect, it, vi } from "vitest";
import { saveSession, sessionFetch } from "./session";

beforeEach(() => { localStorage.clear(); vi.restoreAllMocks(); });

it("refreshes once for concurrent expired requests and retries with the rotated token", async () => {
  saveSession({ access_token: "old", refresh_token: "refresh-old", user: { id: 1 } });
  const fetch = vi.spyOn(global, "fetch").mockImplementation(async (url, options) => {
    if (url.endsWith("/auth/refresh")) return { ok: true, json: async () => ({ access_token: "new", refresh_token: "refresh-new", user: { id: 1 } }) };
    return { status: options.headers.get("Authorization") === "Bearer old" ? 401 : 200 };
  });
  const responses = await Promise.all([sessionFetch("/api/jobs"), sessionFetch("/api/candidates")]);
  expect(responses.map((response) => response.status)).toEqual([200, 200]);
  expect(fetch.mock.calls.filter(([url]) => url.endsWith("/auth/refresh"))).toHaveLength(1);
  expect(localStorage.getItem("vireon_refresh")).toBe("refresh-new");
});

it("clears the identity when refresh is rejected", async () => {
  saveSession({ access_token: "old", refresh_token: "expired", user: { id: 1 } });
  vi.spyOn(global, "fetch").mockResolvedValue({ status: 401, ok: false });
  expect((await sessionFetch("/api/jobs")).status).toBe(401);
  expect(localStorage.getItem("vireon_user")).toBeNull();
  expect(localStorage.getItem("vireon_refresh")).toBeNull();
});
