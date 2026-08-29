import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, errorMessage, tokens } from "@/lib/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [organization, setOrganization] = useState(null);
  const [role, setRole] = useState(null);
  const [loading, setLoading] = useState(true);

  const applySession = useCallback((data) => {
    if (data.access_token) tokens.set(data);
    setUser(data.user || null);
    setOrganization(data.organization || null);
    setRole(data.role || null);
  }, []);

  const bootstrap = useCallback(async () => {
    if (!tokens.access()) {
      setLoading(false);
      return;
    }
    try {
      const { data } = await api.get("/auth/me");
      setUser(data.user);
      setOrganization(data.organization);
      setRole(data.role);
    } catch (e) {
      tokens.clear();
      setUser(null);
      setOrganization(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  const login = useCallback(
    async (email, password) => {
      const { data } = await api.post("/auth/login", { email, password }, { skipAuth: true });
      applySession(data);
      return data;
    },
    [applySession],
  );

  const signup = useCallback(
    async (payload) => {
      const { data } = await api.post("/auth/signup", payload, { skipAuth: true });
      applySession(data);
      return data;
    },
    [applySession],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } catch (e) {
      /* session already gone */
    }
    tokens.clear();
    setUser(null);
    setOrganization(null);
    setRole(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const { data } = await api.get("/auth/me");
    setUser(data.user);
    setOrganization(data.organization);
    setRole(data.role);
    return data;
  }, []);

  const value = useMemo(
    () => ({
      user,
      organization,
      role,
      loading,
      isAuthenticated: Boolean(user),
      login,
      signup,
      logout,
      refreshUser,
      setOrganization,
      errorMessage,
    }),
    [user, organization, role, loading, login, signup, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
};
