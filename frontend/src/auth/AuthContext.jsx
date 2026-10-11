import { createContext, useContext, useEffect, useState } from "react";
import { API_BASE, SESSION_EVENT, clearSession, errorMessage, saveSession, sessionFetch } from "./session";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem("vireon_token")));

  useEffect(() => {
    let active = true;
    function update() {
      try { setUser(JSON.parse(localStorage.getItem("vireon_user") || "null")); }
      catch { setUser(null); }
    }
    window.addEventListener(SESSION_EVENT, update);
    const syncStorage = (event) => { if (event.key === "vireon_token" || event.key === null) window.location.reload(); };
    window.addEventListener("storage", syncStorage);
    if (localStorage.getItem("vireon_token")) {
      sessionFetch(`${API_BASE}/auth/me`).then(async (response) => {
        if (!response.ok) throw new Error("Session validation failed");
        const identity = await response.json();
        if (active && localStorage.getItem("vireon_token")) {
          localStorage.setItem("vireon_user", JSON.stringify(identity));
          setUser(identity);
        }
      }).catch(() => { if (active) clearSession(); }).finally(() => { if (active) setLoading(false); });
    }
    return () => {
      active = false;
      window.removeEventListener(SESSION_EVENT, update);
      window.removeEventListener("storage", syncStorage);
    };
  }, []);

  async function authenticate(path, payload) {
    const response = await fetch(`${API_BASE}/auth/${path}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(errorMessage(data, "Authentication failed"));
    saveSession(data);
    setUser(data.user);
    return data.user;
  }

  async function logout() {
    const token = localStorage.getItem("vireon_token");
    clearSession();
    setUser(null);
    try {
      await fetch(`${API_BASE}/auth/logout`, { method: "POST", headers: token ? { Authorization: `Bearer ${token}` } : {} });
    } catch { /* Local logout succeeds if the server is unreachable. */ }
  }

  return <AuthContext.Provider value={{ user, loading, login: (email, password) => authenticate("login", { email, password }), register: (payload) => authenticate("register", payload), logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
