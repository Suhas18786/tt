import { FormEvent, ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../api";
import { useLookups } from "../lookups";
import { ConfirmDialog, EmptyState, ErrorBanner, Field, Modal, PageHeader, Pagination, Spinner, useToast } from "../ui";
import type { Page } from "../types";

export interface Option { value: string | number; label: string }
export interface FieldDef {
  name: string; label: string;
  type: "text" | "number" | "email" | "password" | "select" | "checkbox" | "multiselect" | "tags";
  options?: Option[]; required?: boolean; min?: number; max?: number; maxLength?: number; hint?: string;
  pattern?: RegExp; patternMsg?: string; default?: unknown; placeholder?: string;
}
export interface Column<T> { key: string; label: string; render?: (row: T) => ReactNode }
export interface FilterDef { name: string; label: string; options: Option[] }

interface Props<T extends { id: number }> {
  title: string; subtitle?: string; noun: string; endpoint: string;
  columns: Column<T>[]; fields: FieldDef[]; filters?: FilterDef[];
  rowActions?: (row: T, reload: () => void) => ReactNode; toForm?: (row: T) => Record<string, any>;
  readOnly?: boolean; headerExtra?: ReactNode; embedded?: boolean; searchPlaceholder?: string; onChanged?: () => void;
}

const isEmpty = (v: unknown) => v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0);

export default function CrudPage<T extends { id: number }>(p: Props<T>) {
  const { reload: reloadLookups } = useLookups();
  const toast = useToast();
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [filterVals, setFilterVals] = useState<Record<string, string>>({});
  const [data, setData] = useState<Page<T> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [modal, setModal] = useState<{ row?: T } | null>(null);
  const [toDelete, setToDelete] = useState<T | null>(null);
  const [busy, setBusy] = useState(false);
  const pageSize = 10;

  useEffect(() => { const t = setTimeout(() => { setDebouncedQ(q); setPage(1); }, 300); return () => clearTimeout(t); }, [q]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await api<Page<T>>(p.endpoint, { params: { page, page_size: pageSize, q: debouncedQ, ...filterVals } }));
      setError(null);
    } catch (e) { setError(e); } finally { setLoading(false); }
  }, [p.endpoint, page, debouncedQ, filterVals]);
  useEffect(() => { load(); }, [load]);

  const changed = () => { load(); reloadLookups(); p.onChanged?.(); };

  const remove = async () => {
    if (!toDelete) return;
    setBusy(true);
    try {
      await api(`${p.endpoint}/${toDelete.id}`, { method: "DELETE" });
      toast("success", `${p.noun} deleted`);
      setToDelete(null);
      if (data && data.items.length === 1 && page > 1) setPage(page - 1); else changed();
      changed();
    } catch (e) { toast("error", (e as ApiError).message); setToDelete(null); } finally { setBusy(false); }
  };

  return (
    <div>
      {!p.embedded && <PageHeader title={p.title} subtitle={p.subtitle} actions={<>
        {p.headerExtra}
        {!p.readOnly && <button className="btn-primary" onClick={() => setModal({})}>+ Add {p.noun}</button>}
      </>} />}
      {p.embedded && !p.readOnly && <div className="mb-3 flex justify-end"><button className="btn-primary" onClick={() => setModal({})}>+ Add {p.noun}</button></div>}
      <ErrorBanner error={error} />
      <div className="card overflow-hidden">
        <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 p-3">
          <input className="input max-w-xs" placeholder={p.searchPlaceholder ?? `Search ${p.title.toLowerCase()}…`} value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" />
          {p.filters?.map((f) => (
            <select key={f.name} className="input max-w-[200px]" aria-label={f.label} value={filterVals[f.name] ?? ""}
              onChange={(e) => { setFilterVals({ ...filterVals, [f.name]: e.target.value }); setPage(1); }}>
              <option value="">{f.label}: all</option>
              {f.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          ))}
          {loading && <Spinner className="h-4 w-4 text-slate-400" />}
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50"><tr>
              {p.columns.map((c) => <th key={c.key} className="th">{c.label}</th>)}
              <th className="th text-right">Actions</th>
            </tr></thead>
            <tbody className="divide-y divide-slate-100">
              {data?.items.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50/70">
                  {p.columns.map((c) => <td key={c.key} className="td">{c.render ? c.render(row) : String((row as any)[c.key] ?? "")}</td>)}
                  <td className="td whitespace-nowrap text-right">
                    {p.rowActions?.(row, changed)}
                    {!p.readOnly && <>
                      <button className="btn-ghost !px-2 !py-1" onClick={() => setModal({ row })}>Edit</button>
                      <button className="btn-ghost !px-2 !py-1 text-red-600 hover:bg-red-50" onClick={() => setToDelete(row)}>Delete</button>
                    </>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {data && data.items.length === 0 && !loading && (
          <EmptyState title={debouncedQ || Object.values(filterVals).some(Boolean) ? "No matches" : `No ${p.title.toLowerCase()} yet`}
            hint={debouncedQ ? "Try a different search or clear the filters." : `Add the first ${p.noun} to get started.`}
            action={!p.readOnly && !debouncedQ ? <button className="btn-primary" onClick={() => setModal({})}>+ Add {p.noun}</button> : undefined} />
        )}
        {data && <Pagination page={page} pageSize={pageSize} total={data.total} onPage={setPage} />}
      </div>

      {modal && <RecordForm {...p} row={modal.row} onClose={() => setModal(null)} onSaved={() => { setModal(null); changed(); toast("success", `${p.noun} saved`); }} />}
      {toDelete && <ConfirmDialog title={`Delete ${p.noun}?`} busy={busy} onCancel={() => setToDelete(null)} onConfirm={remove}
        message={<>This permanently deletes this {p.noun}. This cannot be undone.</>} />}
    </div>
  );
}

function RecordForm<T extends { id: number }>(p: Props<T> & { row?: T; onClose: () => void; onSaved: () => void }) {
  const initial = useMemo(() => {
    const base: Record<string, any> = {};
    p.fields.forEach((f) => { base[f.name] = f.default ?? (f.type === "checkbox" ? false : f.type === "multiselect" || f.type === "tags" ? [] : ""); });
    if (p.row) Object.assign(base, p.toForm ? p.toForm(p.row) : p.row);
    return base;
  }, [p.row]);  // eslint-disable-line react-hooks/exhaustive-deps
  const [form, setForm] = useState<Record<string, any>>(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);
  const [ms, setMs] = useState<Record<string, string>>({});

  const set = (name: string, v: unknown) => setForm((f) => ({ ...f, [name]: v }));

  const validate = () => {
    const errs: Record<string, string> = {};
    for (const f of p.fields) {
      const v = form[f.name];
      if (f.required && isEmpty(v)) { errs[f.name] = "This field is required"; continue; }
      if (isEmpty(v)) continue;
      if (f.type === "number") {
        const n = Number(v);
        if (Number.isNaN(n)) errs[f.name] = "Enter a number";
        else if (f.min !== undefined && n < f.min) errs[f.name] = `Must be at least ${f.min}`;
        else if (f.max !== undefined && n > f.max) errs[f.name] = `Must be at most ${f.max}`;
      }
      if (f.type === "email" && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(String(v))) errs[f.name] = "Enter a valid email address";
      if (f.maxLength && String(v).length > f.maxLength) errs[f.name] = `At most ${f.maxLength} characters`;
      if (f.pattern && !f.pattern.test(String(v))) errs[f.name] = f.patternMsg ?? "Invalid format";
      if (f.type === "password" && String(v).length < 8) errs[f.name] = "At least 8 characters";
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    const body: Record<string, unknown> = {};
    for (const f of p.fields) {
      const v = form[f.name];
      if (f.type === "number") body[f.name] = isEmpty(v) ? null : Number(v);
      else if (f.type === "password") { if (!isEmpty(v)) body[f.name] = v; }
      else if (f.type === "text" || f.type === "email") body[f.name] = typeof v === "string" ? v.trim() : v;
      else body[f.name] = v;
    }
    setSaving(true);
    try {
      await api(p.row ? `${p.endpoint}/${p.row.id}` : p.endpoint, { method: p.row ? "PUT" : "POST", body });
      p.onSaved();
    } catch (err) { setServerError(err); } finally { setSaving(false); }
  };

  return (
    <Modal title={`${p.row ? "Edit" : "Add"} ${p.noun}`} onClose={p.onClose} wide={p.fields.length > 8}
      footer={<>
        <button type="button" className="btn-secondary" onClick={p.onClose}>Cancel</button>
        <button type="submit" form="record-form" className="btn-primary" disabled={saving}>{saving && <Spinner className="h-4 w-4" />}Save</button>
      </>}>
      <form id="record-form" onSubmit={submit} noValidate className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2"><ErrorBanner error={serverError} /></div>
        {p.fields.map((f) => {
          const full = f.type === "multiselect" || f.type === "tags";
          return (
            <div key={f.name} className={full ? "sm:col-span-2" : ""}>
              {f.type === "checkbox" ? (
                <label className="mt-6 flex items-center gap-2 text-sm font-medium text-slate-700">
                  <input type="checkbox" className="h-4 w-4 rounded border-slate-300" checked={!!form[f.name]} onChange={(e) => set(f.name, e.target.checked)} />
                  {f.label}
                </label>
              ) : (
                <Field label={f.label} required={f.required} error={errors[f.name]} hint={f.hint}>
                  {f.type === "select" ? (
                    <select className="input" value={String(form[f.name] ?? "")} onChange={(e) => set(f.name, f.options?.find((o) => String(o.value) === e.target.value)?.value ?? "")}>
                      <option value="">Select…</option>
                      {f.options?.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  ) : f.type === "multiselect" ? (
                    <div className="rounded-md border border-slate-300">
                      <input className="input rounded-b-none border-0 border-b" placeholder="Filter…" value={ms[f.name] ?? ""} onChange={(e) => setMs({ ...ms, [f.name]: e.target.value })} />
                      <div className="max-h-40 overflow-y-auto p-2">
                        {f.options?.filter((o) => o.label.toLowerCase().includes((ms[f.name] ?? "").toLowerCase())).map((o) => (
                          <label key={o.value} className="flex items-center gap-2 py-0.5 text-sm">
                            <input type="checkbox" checked={(form[f.name] as unknown[]).includes(o.value)}
                              onChange={(e) => set(f.name, e.target.checked ? [...(form[f.name] as unknown[]), o.value] : (form[f.name] as unknown[]).filter((x) => x !== o.value))} />
                            {o.label}
                          </label>
                        ))}
                      </div>
                    </div>
                  ) : f.type === "tags" ? (
                    <input className="input" value={(form[f.name] as string[]).join(", ")} placeholder={f.placeholder ?? "comma separated"}
                      onChange={(e) => set(f.name, e.target.value.split(",").map((s) => s.trim()).filter(Boolean))} />
                  ) : (
                    <input className="input" type={f.type === "number" ? "number" : f.type} value={form[f.name] ?? ""} min={f.min} max={f.max}
                      placeholder={f.placeholder} autoComplete={f.type === "password" ? "new-password" : "off"} onChange={(e) => set(f.name, e.target.value)} />
                  )}
                </Field>
              )}
            </div>
          );
        })}
      </form>
    </Modal>
  );
}
