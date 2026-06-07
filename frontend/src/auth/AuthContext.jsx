import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { apiAuth, authStorage } from "./apiAuth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => authStorage.getToken());
  const [user, setUser] = useState(() => authStorage.getUser());
  const [loading, setLoading] = useState(Boolean(authStorage.getToken()));

  useEffect(() => {
    let active = true;
    async function restoreSession() {
      if (!authStorage.getToken()) {
        setLoading(false);
        return;
      }
      try {
        const currentUser = await apiAuth.me();
        if (!active) return;
        setUser(currentUser);
        setToken(authStorage.getToken());
        localStorage.setItem(authStorage.userKey, JSON.stringify(currentUser));
      } catch {
        authStorage.clearSession();
        if (!active) return;
        setToken(null);
        setUser(null);
      } finally {
        if (active) setLoading(false);
      }
    }
    restoreSession();
    return () => {
      active = false;
    };
  }, []);

  async function login(email, password) {
    const session = await apiAuth.login({ email, password });
    authStorage.saveSession(session);
    setToken(session.access_token);
    setUser(session.user);
    return session.user;
  }

  async function register(payload) {
    const session = await apiAuth.register(payload);
    authStorage.saveSession(session);
    setToken(session.access_token);
    setUser(session.user);
    return session.user;
  }

  function logout() {
    authStorage.clearSession();
    setToken(null);
    setUser(null);
  }

  const value = useMemo(
    () => ({
      token,
      user,
      loading,
      isAuthenticated: Boolean(token && user),
      login,
      register,
      logout,
    }),
    [token, user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}
