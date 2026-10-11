export const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");
export const SESSION_EVENT = "vireon-session";
const KEYS = ["vireon_token", "vireon_refresh", "vireon_user"];

export function clearSession() {
  KEYS.forEach((key) => localStorage.removeItem(key));
  window.dispatchEvent(new Event(SESSION_EVENT));
}

export function saveSession(data) {
  localStorage.setItem(KEYS[0], data.access_token);
  if (data.refresh_token) localStorage.setItem(KEYS[1], data.refresh_token);
  else localStorage.removeItem(KEYS[1]);
  localStorage.setItem(KEYS[2], JSON.stringify(data.user));
  window.dispatchEvent(new Event(SESSION_EVENT));
}

export function errorMessage(data, fallback = "Request failed") {
  if (Array.isArray(data?.detail)) return data.detail.map((item) => item.msg).join("; ");
  return typeof data?.detail === "string" ? data.detail : fallback;
}

let refreshPending;
async function refreshSession() {
  if (!refreshPending) {
    refreshPending = (async () => {
      const refresh_token = localStorage.getItem(KEYS[1]);
      if (!refresh_token) return false;
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh_token }),
      });
      if (!response.ok) return false;
      const data = await response.json();
      if (localStorage.getItem(KEYS[1]) !== refresh_token) return false;
      saveSession(data);
      return true;
    })().finally(() => { refreshPending = undefined; });
  }
  return refreshPending;
}

export async function sessionFetch(url, options = {}) {
  const send = () => {
    const headers = new Headers(options.headers);
    const token = localStorage.getItem(KEYS[0]);
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return fetch(url, { ...options, headers });
  };
  let response = await send();
  if (response.status === 401) {
    if (await refreshSession()) response = await send();
    if (response.status === 401) clearSession();
  }
  return response;
}
