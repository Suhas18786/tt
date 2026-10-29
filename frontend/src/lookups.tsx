import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { api } from "./api";
import { useAuth } from "./auth";
import type { Lookups } from "./types";

const empty: Lookups = { departments: [], academic_years: [], semesters: [], batches: [], faculty: [], subjects: [], rooms: [] };
const Ctx = createContext<{ data: Lookups; reload: () => Promise<void> }>({ data: empty, reload: async () => {} });
export const useLookups = () => useContext(Ctx);

export function LookupsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [data, setData] = useState<Lookups>(empty);
  const reload = useCallback(async () => { if (user) setData(await api<Lookups>("/lookups")); }, [user]);
  useEffect(() => { reload().catch(() => {}); }, [reload]);
  return <Ctx.Provider value={{ data, reload }}>{children}</Ctx.Provider>;
}
