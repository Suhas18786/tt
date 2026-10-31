import { useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiError, download } from "../api";
import { useAuth } from "../auth";
import { Badge, Bar, ConfirmDialog, EmptyState, ErrorBanner, Spinner, useToast } from "../ui";
import { Generation, Session } from "../types";
import TimetableGrid, { GridView } from "./TimetableGrid";

interface Move { sid: number; from: { day: number; start: number; room: number }; to: { day: number; start: number; room: number } }
const EDITABLE = ["preview", "draft", "infeasible"];

export default function TimetableWorkspace({ id, onRegenerate, onDeleted, regenerating }: {
  id: number; onRegenerate?: () => void; onDeleted?: () => void; regenerating?: boolean;
}) {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const toast = useToast();
  const [gen, setGen] = useState<Generation | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [moveError, setMoveError] = useState<unknown>(null);
  const [undo, setUndo] = useState<Move[]>([]);
  const [redo, setRedo] = useState<Move[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<"delete" | "unpublish" | null>(null);
  const [f, setF] = useState({ faculty: "", department: "", room: "", semester: "", batch: "" });
  const [exportView, setExportView] = useState("batch");
  const [highlight, setHighlight] = useState<number[]>([]);

  const load = useCallback(async () => {
    try { setGen(await api<Generation>(`/timetables/${id}`)); setError(null); } catch (e) { setError(e); }
  }, [id]);
  useEffect(() => { setGen(null); setUndo([]); setRedo([]); setMoveError(null); setHighlight([]); load(); }, [load]);

  const sessions = gen?.sessions ?? [];
  const opts = useMemo(() => {
    const uniq = (pick: (s: Session) => [number, string]) => {
      const m = new Map<number, string>();
      sessions.forEach((s) => { const [k, v] = pick(s); m.set(k, v); });
      return [...m.entries()].sort((a, b) => a[1].localeCompare(b[1]));
    };
    return {
      faculty: uniq((s) => [s.faculty_id, s.faculty_name]), department: uniq((s) => [s.department_id, s.department_code]),
      room: uniq((s) => [s.room_id, s.room_label]), semester: uniq((s) => [s.semester_id, `Semester #${s.semester_id}`]),
      batch: uniq((s) => [s.batch_id, s.batch_code]),
    };
  }, [sessions]);

  const shown = sessions.filter((s) =>
    (!f.faculty || s.faculty_id === +f.faculty) && (!f.department || s.department_id === +f.department) &&
    (!f.room || s.room_id === +f.room) && (!f.semester || s.semester_id === +f.semester) && (!f.batch || s.batch_id === +f.batch));
  const view: GridView = f.batch ? "batch" : f.faculty ? "faculty" : f.room ? "room" : "mixed";
  const editable = isAdmin && !!gen && EDITABLE.includes(gen.status);

  const doMove = (sid: number, day: number, start: number, room: number) =>
    api(`/timetables/${id}/move`, { method: "POST", body: { session_id: sid, day, start_period: start, room_id: room } });

  const onMove = async (s: Session, day: number, period: number) => {
    setBusy("move");
    try {
      await doMove(s.id, day, period, s.room_id);
      setUndo((u) => [...u, { sid: s.id, from: { day: s.day, start: s.start_period, room: s.room_id }, to: { day, start: period, room: s.room_id } }]);
      setRedo([]); setMoveError(null); setHighlight([]);
      await load();
    } catch (e) {
      setMoveError(e);
      setHighlight(((e as ApiError).violations as any[]).flatMap((v) => v.session_ids ?? []));
    } finally { setBusy(null); }
  };
  const step = async (kind: "undo" | "redo") => {
    const stack = kind === "undo" ? undo : redo;
    const m = stack[stack.length - 1];
    if (!m) return;
    const t = kind === "undo" ? m.from : m.to;
    setBusy(kind);
    try {
      await doMove(m.sid, t.day, t.start, t.room);
      if (kind === "undo") { setUndo(undo.slice(0, -1)); setRedo([...redo, m]); } else { setRedo(redo.slice(0, -1)); setUndo([...undo, m]); }
      setMoveError(null);
      await load();
    } catch (e) { setMoveError(e); } finally { setBusy(null); }
  };

  const act = async (name: string, path: string, okMsg: string) => {
    setBusy(name);
    try { await api(path, { method: "POST" }); toast("success", okMsg); await load(); setError(null); }
    catch (e) { setError(e); } finally { setBusy(null); setConfirm(null); }
  };
  const remove = async () => {
    setBusy("delete");
    try { await api(`/timetables/${id}`, { method: "DELETE" }); toast("success", "Timetable deleted"); onDeleted?.(); }
    catch (e) { setError(e); setConfirm(null); } finally { setBusy(null); }
  };
  const exportAs = async (format: "pdf" | "xlsx") => {
    setBusy(format);
    try {
      const entity = exportView === "faculty" ? f.faculty : exportView === "batch" ? f.batch : exportView === "room" ? f.room : exportView === "department" ? f.department : "";
      await download(`/timetables/${id}/export`, { format, view: exportView, entity_id: entity }, `timetable-${id}-${exportView}.${format}`);
    } catch (e) { setError(e); } finally { setBusy(null); }
  };

  if (!gen) return error ? <ErrorBanner error={error} /> : <div className="p-10 text-center text-slate-400"><Spinner className="h-7 w-7" /></div>;
  const rep = gen.report;
  const canPublish = !!rep?.complete && (gen.status === "preview" || gen.status === "draft") && gen.validation?.ok;
  const maxHours = Math.max(1, ...(gen.workload ?? []).map((w) => Math.max(w.hours, w.required, w.max_hours_per_week)));

  return (
    <div className="space-y-5">
      <ErrorBanner error={error} onClose={() => setError(null)} />

      <div className="card p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-semibold">{gen.name}</h2><Badge>{gen.status}</Badge>
              <span className="text-xs text-slate-500">#{gen.id} · solver: {gen.solver_status}{gen.solve_seconds != null && ` · ${gen.solve_seconds}s`}{gen.objective != null && ` · objective ${gen.objective}`}</span>
            </div>
            <p className="mt-1 text-sm text-slate-600">
              {sessions.length} of {gen.expected_sessions} sessions scheduled
              {gen.unscheduled_count > 0 && <span className="font-medium text-red-600"> · {gen.unscheduled_count} unscheduled</span>}
            </p>
          </div>
          {isAdmin && (
            <div className="flex flex-wrap gap-2">
              {onRegenerate && <button className="btn-secondary" onClick={onRegenerate} disabled={regenerating || !!busy}>{regenerating && <Spinner className="h-4 w-4" />}Regenerate</button>}
              {(gen.status === "preview") && <button className="btn-secondary" disabled={!!busy} onClick={() => act("draft", `/timetables/${id}/save-draft`, "Saved as draft")}>Save as draft</button>}
              {(gen.status === "preview" || gen.status === "draft") && <button className="btn-primary" disabled={!!busy || !canPublish}
                title={canPublish ? "" : "All classes must be scheduled with no violations before publishing"} onClick={() => act("publish", `/timetables/${id}/publish`, "Timetable published")}>
                {busy === "publish" && <Spinner className="h-4 w-4" />}Publish</button>}
              {gen.status === "published" && <button className="btn-secondary" onClick={() => setConfirm("unpublish")}>Unpublish</button>}
              {gen.status !== "published" && <button className="btn-ghost text-red-600 hover:bg-red-50" onClick={() => setConfirm("delete")}>Delete</button>}
            </div>
          )}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
          <span className="text-sm font-medium text-slate-600">Export</span>
          <select className="input !w-auto" value={exportView} onChange={(e) => setExportView(e.target.value)} aria-label="Export view">
            <option value="batch">By student batch</option><option value="faculty">By faculty</option><option value="room">By room</option><option value="department">By department</option>
          </select>
          <button className="btn-secondary" onClick={() => exportAs("pdf")} disabled={!!busy || !sessions.length}>{busy === "pdf" && <Spinner className="h-4 w-4" />}PDF</button>
          <button className="btn-secondary" onClick={() => exportAs("xlsx")} disabled={!!busy || !sessions.length}>{busy === "xlsx" && <Spinner className="h-4 w-4" />}Excel</button>
          <span className="text-xs text-slate-500">Uses the matching filter below when set, otherwise exports every {exportView}.</span>
        </div>
      </div>

      {gen.status === "infeasible" && (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
          <p className="font-semibold">A complete conflict-free timetable could not be produced.</p>
          <p className="mt-1">The sessions shown are the best valid partial schedule (no conflicts). This timetable cannot be published until every class fits — see the reasons below.</p>
        </div>
      )}

      {rep && rep.issues.length > 0 && (
        <div className="card p-4">
          <h3 className="mb-2 font-semibold">Scheduling diagnostics</h3>
          <ul className="space-y-1.5 text-sm">
            {rep.issues.map((i, k) => (
              <li key={k} className="flex gap-2"><span className={`mt-0.5 h-2 w-2 flex-none rounded-full ${i.severity === "error" ? "bg-red-500" : i.severity === "warning" ? "bg-amber-500" : "bg-sky-500"}`} />
                <span><span className="font-medium capitalize">{i.severity}:</span> {i.message}</span></li>
            ))}
          </ul>
        </div>
      )}

      <div className="card p-4">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          {(["faculty", "department", "room", "semester", "batch"] as const).map((k) => (
            <select key={k} className="input !w-auto max-w-[190px]" aria-label={`Filter by ${k}`} value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })}>
              <option value="">{k[0].toUpperCase() + k.slice(1)}: all</option>
              {opts[k].map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          ))}
          {Object.values(f).some(Boolean) && <button className="btn-ghost" onClick={() => setF({ faculty: "", department: "", room: "", semester: "", batch: "" })}>Clear</button>}
          {editable && (
            <div className="ml-auto flex items-center gap-2">
              {busy === "move" && <Spinner className="h-4 w-4 text-slate-400" />}
              <button className="btn-secondary" onClick={() => step("undo")} disabled={!undo.length || !!busy}>↶ Undo</button>
              <button className="btn-secondary" onClick={() => step("redo")} disabled={!redo.length || !!busy}>↷ Redo</button>
            </div>
          )}
        </div>
        {editable && <p className="mb-3 text-xs text-slate-500">Drag a class to another period to move it. Every move is checked against all hard constraints; invalid moves are rejected with the reason.</p>}
        <ErrorBanner error={moveError} onClose={() => { setMoveError(null); setHighlight([]); }} />
        {gen.config && (sessions.length > 0
          ? <TimetableGrid config={gen.config} sessions={shown} view={view} editable={editable} highlightIds={highlight} onMove={onMove} />
          : <EmptyState title="Nothing scheduled" hint="No class could be placed. See the diagnostics above." />)}
        {shown.length === 0 && sessions.length > 0 && <p className="mt-2 text-sm text-slate-500">No classes match these filters.</p>}
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="card p-4">
          <h3 className="mb-2 font-semibold">Conflict validation</h3>
          {gen.validation?.ok
            ? <p className="text-sm text-emerald-700">✓ No hard-constraint violations. Every required class is scheduled.</p>
            : <>
              {gen.validation && gen.validation.violations.length === 0 && <p className="text-sm text-emerald-700">✓ No hard-constraint violations in the scheduled classes.</p>}
              <ul className="mt-1 space-y-1 text-sm text-red-700">
                {gen.validation?.violations.map((v, i) => <li key={i}><button className="text-left hover:underline" onClick={() => setHighlight(v.session_ids)}>✕ {v.message}</button></li>)}
              </ul>
              {gen.validation && gen.validation.unscheduled > 0 && <p className="mt-2 text-sm text-red-700">✕ {gen.validation.unscheduled} required session(s) are not scheduled.</p>}
            </>}
        </div>
        <div className="card p-4">
          <h3 className="mb-2 font-semibold">Faculty weekly teaching hours <span className="text-xs font-normal text-slate-500">(scheduled of required)</span></h3>
          {gen.workload && gen.workload.length > 0 ? (
            <ul className="max-h-64 space-y-2 overflow-y-auto pr-1">
              {gen.workload.map((w) => (
                <li key={w.faculty_id}>
                  <div className="flex justify-between text-sm"><span>{w.faculty_name}</span><span className="text-slate-500">{w.hours} of {w.required} h scheduled · limit {w.max_hours_per_week}</span></div>
                  <Bar value={w.hours} max={maxHours} tone={w.hours > w.max_hours_per_week ? "bg-red-500" : "bg-brand-600"} label={w.faculty_name} />
                </li>
              ))}
            </ul>
          ) : <p className="text-sm text-slate-500">No teaching assignments in this timetable.</p>}
        </div>
      </div>

      {rep && rep.unscheduled.length > 0 && (
        <div className="card overflow-hidden">
          <h3 className="border-b border-slate-200 px-4 py-3 font-semibold text-red-700">Unscheduled sessions ({rep.unscheduled.length})</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50"><tr><th className="th">Session</th><th className="th">Subject</th><th className="th">Periods</th><th className="th">Why it could not be placed</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {rep.unscheduled.map((u, i) => <tr key={i}><td className="td">{u.session}</td><td className="td">{u.subject_code} – {u.subject_name}</td><td className="td">{u.duration}</td><td className="td text-red-700">{u.reason}</td></tr>)}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {confirm === "delete" && <ConfirmDialog title="Delete timetable?" message={`"${gen.name}" and all its sessions will be permanently deleted.`} busy={busy === "delete"} onConfirm={remove} onCancel={() => setConfirm(null)} />}
      {confirm === "unpublish" && <ConfirmDialog title="Unpublish timetable?" confirmLabel="Unpublish" message="Faculty will no longer see this timetable, and it becomes editable as a draft." busy={busy === "unpublish"}
        onConfirm={() => act("unpublish", `/timetables/${id}/unpublish`, "Timetable unpublished")} onCancel={() => setConfirm(null)} />}
    </div>
  );
}
