import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";
import type { User } from "./types";

interface AuthCtx { user: User | null; loading: boolean; login: (email: string, password: string) => Promise<void>; logout: () => void }
const Ctx = createContext<AuthCtx>(null as unknown as AuthCtx);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(!!getToken());

  useEffect(() => {
    if (!getToken()) return;
    api<User>("/auth/me").then(setUser).catch(() => setToken(null)).finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    const h = () => setUser(null);
    window.addEventListener("auth-expired", h);
    return () => window.removeEventListener("auth-expired", h);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const r = await api<{ access_token: string; user: User }>("/auth/login", { method: "POST", body: { email, password } });
    setToken(r.access_token);
    setUser(r.user);
  }, []);
  const logout = useCallback(() => { setToken(null); setUser(null); }, []);
  return <Ctx.Provider value={{ user, loading, login, logout }}>{children}</Ctx.Provider>;
}
