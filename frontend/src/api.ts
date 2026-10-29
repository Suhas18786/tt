const BASE: string = import.meta.env.VITE_API_URL ?? "/api";
const TOKEN_KEY = "timetable_token";

export const getToken = (): string | null => { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } };
export const setToken = (t: string | null) => {
  try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY); } catch { /* ignore */ }
};

export interface ViolationLike { code: string; message: string }
export class ApiError extends Error {
  status: number;
  violations: ViolationLike[];
  constructor(status: number, message: string, violations: ViolationLike[] = []) {
    super(message);
    this.status = status;
    this.violations = violations;
  }
}

function parseDetail(body: any, status: number): ApiError {
  const d = body?.detail;
  if (typeof d === "string") return new ApiError(status, d);
  if (d && typeof d === "object" && !Array.isArray(d)) return new ApiError(status, d.message ?? "Request failed", d.violations ?? []);
  if (Array.isArray(d)) return new ApiError(status, d.map((e: any) => e.msg).join("; "));
  return new ApiError(status, `Request failed (${status})`);
}

type Opts = { method?: string; body?: unknown; params?: Record<string, string | number | boolean | null | undefined> };

function url(path: string, params?: Opts["params"]) {
  const q = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") q.set(k, String(v)); });
  const s = q.toString();
  return `${BASE}${path}${s ? `?${s}` : ""}`;
}

async function request(path: string, opts: Opts = {}): Promise<Response> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(url(path, opts.params), { method: opts.method ?? "GET", headers, body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Check your connection and try again.");
  }
  if (res.status === 401 && token && !path.startsWith("/auth/login")) {
    setToken(null);
    window.dispatchEvent(new Event("auth-expired"));
  }
  if (!res.ok) {
    let body: unknown = null;
    try { body = await res.json(); } catch { /* not json */ }
    throw parseDetail(body, res.status);
  }
  return res;
}

export async function api<T = any>(path: string, opts: Opts = {}): Promise<T> {
  const res = await request(path, opts);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function download(path: string, params: Opts["params"], filename: string) {
  const res = await request(path, { params });
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
