import { API_BASE } from "../api";

const TOKEN_KEY = "vireon_token";
const USER_KEY = "vireon_user";

function apiPath(path) {
  if (API_BASE === "/api" && path.startsWith("/api/")) {
    return path.slice(4);
  }
  return path;
}

async function authRequest(path, options = {}) {
  const token = localStorage.getItem(TOKEN_KEY);
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${apiPath(path)}`, {
    ...options,
    headers,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(data?.detail || `Request failed: ${response.status}`);
  }
  return data;
}

export const authStorage = {
  tokenKey: TOKEN_KEY,
  userKey: USER_KEY,
  getToken: () => localStorage.getItem(TOKEN_KEY),
  getUser: () => {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || "null");
    } catch {
      return null;
    }
  },
  saveSession: ({ access_token, user }) => {
    localStorage.setItem(TOKEN_KEY, access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  clearSession: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
};

export const apiAuth = {
  login: (payload) => authRequest("/api/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  register: (payload) => authRequest("/api/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  me: () => authRequest("/api/auth/me"),
};

export function roleHome(role) {
  if (role === "ADMIN") return "/admin";
  if (role === "RECRUITER") return "/recruiter";
  if (role === "CANDIDATE") return "/candidate";
  return "/login";
}
