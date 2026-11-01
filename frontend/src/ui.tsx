import { createContext, ReactNode, useCallback, useContext, useEffect, useRef, useState } from "react";
import { ApiError } from "./api";

export function Spinner({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" role="status" aria-label="Loading">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
      <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="4" strokeLinecap="round" className="opacity-90" />
    </svg>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-[1.7rem] font-bold leading-tight text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-slate-500">{subtitle}</p>}
      </div>
      <div className="flex flex-wrap items-center gap-2">{actions}</div>
    </div>
  );
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 10h18M9 4v16" /></svg>
      </div>
      <p className="font-medium text-slate-700">{title}</p>
      {hint && <p className="mt-1 max-w-sm text-sm text-slate-500">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorBanner({ error, onClose }: { error: unknown; onClose?: () => void }) {
  if (!error) return null;
  const e = error as ApiError;
  return (
    <div role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium">{e.message || "Something went wrong"}</p>
          {e.violations?.length > 0 && (
            <ul className="mt-1.5 list-disc space-y-0.5 pl-5">
              {e.violations.slice(0, 15).map((v, i) => <li key={i}>{v.message}</li>)}
              {e.violations.length > 15 && <li>…and {e.violations.length - 15} more</li>}
            </ul>
          )}
        </div>
        {onClose && <button onClick={onClose} className="text-red-700 hover:text-red-900" aria-label="Dismiss">✕</button>}
      </div>
    </div>
  );
}

const BADGE: Record<string, string> = {
  published: "bg-emerald-100 text-emerald-800", draft: "bg-amber-100 text-amber-800", preview: "bg-sky-100 text-sky-800",
  archived: "bg-slate-200 text-slate-700", infeasible: "bg-red-100 text-red-800", open: "bg-amber-100 text-amber-800",
  resolved: "bg-emerald-100 text-emerald-800", default: "bg-slate-100 text-slate-700",
};
export function Badge({ children, tone }: { children: ReactNode; tone?: string }) {
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${BADGE[tone ?? String(children)] ?? BADGE.default}`}>{children}</span>;
}

export function Modal({ title, onClose, children, wide, footer }: { title: string; onClose: () => void; children: ReactNode; wide?: boolean; footer?: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    ref.current?.focus();
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4 sm:p-8" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={ref} tabIndex={-1} role="dialog" aria-modal="true" aria-label={title} className={`card w-full ${wide ? "max-w-4xl" : "max-w-xl"} outline-none`}>
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3.5">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button className="btn-ghost !px-2 !py-1" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="max-h-[70vh] overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t border-slate-200 bg-slate-50 px-5 py-3 rounded-b-xl">{footer}</div>}
      </div>
    </div>
  );
}

export function ConfirmDialog({ title, message, confirmLabel = "Delete", onConfirm, onCancel, busy }: {
  title: string; message: ReactNode; confirmLabel?: string; onConfirm: () => void; onCancel: () => void; busy?: boolean;
}) {
  return (
    <Modal title={title} onClose={onCancel} footer={<>
      <button className="btn-secondary" onClick={onCancel}>Cancel</button>
      <button className="btn-danger" onClick={onConfirm} disabled={busy}>{busy && <Spinner className="h-4 w-4" />}{confirmLabel}</button>
    </>}>
      <p className="text-sm text-slate-600">{message}</p>
    </Modal>
  );
}

export function Field({ label, error, hint, children, required }: { label: string; error?: string; hint?: string; children: ReactNode; required?: boolean }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">{label}{required && <span className="text-red-600"> *</span>}</span>
      {children}
      {hint && !error && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
      {error && <span className="mt-1 block text-xs text-red-600" role="alert">{error}</span>}
    </label>
  );
}

export function Pagination({ page, pageSize, total, onPage }: { page: number; pageSize: number; total: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-sm text-slate-600">
      <span>{total === 0 ? "No results" : `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} of ${total}`}</span>
      <div className="flex items-center gap-2">
        <button className="btn-secondary !py-1" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</button>
        <span>Page {page} / {pages}</span>
        <button className="btn-secondary !py-1" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</button>
      </div>
    </div>
  );
}

export function StatCard({ label, value, sub, tone = "brand" }: { label: string; value: ReactNode; sub?: string; tone?: "brand" | "green" | "red" | "amber" }) {
  const dot = { brand: "bg-brand-500", green: "bg-emerald-500", red: "bg-red-500", amber: "bg-amber-500" }[tone];
  return (
    <div className="card p-4">
      <p className="flex items-center gap-2 text-sm font-medium text-slate-500"><span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden />{label}</p>
      <p className="mt-2 font-display text-3xl font-bold tracking-tight text-slate-900">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

export function Bar({ value, max, tone = "bg-brand-600", label }: { value: number; max: number; tone?: string; label?: string }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuenow={value} aria-valuemax={max} aria-label={label}>
      <div className={`h-full rounded-full ${tone}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

// ---- toasts -------------------------------------------------------------------------------------
interface Toast { id: number; kind: "success" | "error"; text: string }
const ToastCtx = createContext<(kind: Toast["kind"], text: string) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((kind: Toast["kind"], text: string) => {
    const id = Date.now() + Math.random();
    setItems((x) => [...x, { id, kind, text }]);
    setTimeout(() => setItems((x) => x.filter((t) => t.id !== id)), kind === "error" ? 7000 : 3500);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-[60] flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={`rounded-lg px-4 py-3 text-sm text-white shadow-lg ${t.kind === "success" ? "bg-emerald-600" : "bg-red-600"}`}>{t.text}</div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function LogoMark({ size = 30 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <rect width="32" height="32" rx="8" fill="#2535ae" />
      <rect x="6" y="6" width="9" height="9" rx="2" fill="#fff" />
      <rect x="17" y="6" width="9" height="5" rx="2" fill="#8fa0ff" />
      <rect x="6" y="17" width="5" height="9" rx="2" fill="#8fa0ff" />
      <rect x="13" y="17" width="13" height="9" rx="2" fill="#fff" opacity=".9" />
    </svg>
  );
}
