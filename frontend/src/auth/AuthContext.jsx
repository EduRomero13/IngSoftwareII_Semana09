import { createContext, useContext, useEffect, useMemo, useState } from "react";
import api from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("soclite_token"));
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("soclite_user");
    return raw ? JSON.parse(raw) : null;
  });

  useEffect(() => {
    if (token) localStorage.setItem("soclite_token", token);
    else localStorage.removeItem("soclite_token");
  }, [token]);

  useEffect(() => {
    if (user) localStorage.setItem("soclite_user", JSON.stringify(user));
    else localStorage.removeItem("soclite_user");
  }, [user]);

  const login = async (username, password) => {
    const { data } = await api.post("/auth/login/json", { username, password });
    setToken(data.access_token);
    setUser({
      username: data.username,
      role: data.role,
      permissions: data.permissions,
    });
    return data;
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      /* la sesion local se cierra igualmente */
    }
    setToken(null);
    setUser(null);
  };

  const can = (permission) => Boolean(user?.permissions?.includes(permission));

  const value = useMemo(
    () => ({ token, user, login, logout, can, isAuthenticated: Boolean(token) }),
    [token, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
