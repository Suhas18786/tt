import { useEffect, useState } from "react";
import { api, download } from "../api";
import TimetableGrid, { GridView } from "../components/TimetableGrid";
import { Generation, Period, Session, Unscheduled, Violation, DAYS } from "../types";
import { Badge, EmptyState, ErrorBanner, PageHeader, Spinner } from "../ui";

type Kind = "faculty" | "batch" | "room" | "department" | "workload" | "unscheduled";
const TABS: [Kind, string][] = [["faculty", "Faculty-wise"], ["batch", "Batch-wise"], ["room", "Room-wise"], ["department", "Department-wise"], ["workload", "Faculty workload"], ["unscheduled", "Unscheduled & violations"]];
type Cfg = { working_days: number[]; periods: Period[]; blocked_slots?: number[][] };

export default function Reports() {
  const [gens, setGens] = useState<Generation[]>([]);
  const [genId, setGenId] = useState("");
  const [kind, setKind] = useState<Kind>("faculty");
  const [rep, setRep] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<unknown>(null);

  useEffect(() => { api<Generation[]>("/timetables").then(setGens).catch(setErr); }, []);
  useEffect(() => {
    setLoading(true); setRep(null);
    api(`/reports/${kind}`, { params: { generation_id: genId } }).then((r) => { setRep(r); setErr(null); }).catch(setErr).finally(() => setLoading(false));
  }, [kind, genId]);

  const exp = async (format: "pdf" | "xlsx", entity?: number) => {
    const gid = rep?.generation?.id;
    if (!gid) return;
    try { await download(`/timetables/${gid}/export`, { format, view: kind, entity_id: entity }, `${kind}-${entity ?? "all"}.${format}`); } catch (e) { setErr(e); }
  };

  return (
    <div>
      <PageHeader title="Reports" subtitle="Per-faculty, batch, room and department timetables, workload and constraint reports."
        actions={<select className="input !w-auto" value={genId} onChange={(e) => setGenId(e.target.value)} aria-label="Timetable">
          <option value="">Latest (published first)</option>{gens.map((g) => <option key={g.id} value={g.id}>#{g.id} {g.name} ({g.status})</option>)}</select>} />
      <div className="mb-4 flex flex-wrap gap-1 border-b border-slate-200" role="tablist">
        {TABS.map(([k, l]) => <button key={k} role="tab" aria-selected={kind === k} onClick={() => setKind(k)}
          className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${kind === k ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-800"}`}>{l}</button>)}
      </div>
      <ErrorBanner error={err} />
      {loading && <div className="p-10 text-center"><Spinner className="h-7 w-7" /></div>}
      {rep && !loading && (
        <>
          <p className="mb-3 text-sm text-slate-600">Source: <b>{rep.generation.name}</b> <Badge>{rep.generation.status}</Badge></p>
          {["faculty", "batch", "room", "department"].includes(kind) && (
            <div className="space-y-6">
              {rep.groups.length === 0 && <div className="card"><EmptyState title="No sessions" /></div>}
              {rep.groups.map((g: { id: number; title: string; sessions: Session[] }) => (
                <section key={g.id} className="card p-4">
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <h2 className="font-semibold">{g.title} <span className="text-sm font-normal text-slate-500">· {g.sessions.reduce((a, s) => a + s.duration, 0)} periods/week</span></h2>
                    <div className="flex gap-2"><button className="btn-secondary !py-1" onClick={() => exp("pdf", g.id)}>PDF</button><button className="btn-secondary !py-1" onClick={() => exp("xlsx", g.id)}>Excel</button></div>
                  </div>
                  <TimetableGrid config={rep.generation.config as Cfg} sessions={g.sessions} view={(kind === "department" ? "mixed" : kind) as GridView} />
                </section>
              ))}
            </div>
          )}
          {kind === "workload" && (
            <div className="card overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50"><tr><th className="th">Faculty</th>{DAYS.slice(0, 6).map((d) => <th key={d} className="th">{d.slice(0, 3)}</th>)}<th className="th">Total</th><th className="th">Limit</th></tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {rep.rows.map((r: any) => (
                    <tr key={r.faculty_id}><td className="td font-medium">{r.faculty_name}</td>
                      {DAYS.slice(0, 6).map((_, i) => <td key={i} className="td">{r.per_day[i] ?? 0}</td>)}
                      <td className={`td font-semibold ${r.hours > r.max_hours_per_week ? "text-red-600" : ""}`}>{r.hours}</td><td className="td">{r.max_hours_per_week}</td></tr>
                  ))}
                </tbody>
              </table>
              {rep.rows.length === 0 && <EmptyState title="No sessions scheduled" />}
            </div>
          )}
          {kind === "unscheduled" && (
            <div className="space-y-5">
              <div className="card p-4"><h2 className="mb-2 font-semibold">Constraint violations</h2>
                {rep.violations.length === 0 ? <p className="text-sm text-emerald-700">✓ No hard-constraint violations.</p>
                  : <ul className="space-y-1 text-sm text-red-700">{rep.violations.map((v: Violation, i: number) => <li key={i}>✕ {v.message}</li>)}</ul>}</div>
              <div className="card p-4"><h2 className="mb-2 font-semibold">Unscheduled subjects</h2>
                {rep.unscheduled.length === 0 ? <p className="text-sm text-emerald-700">✓ Every required session is scheduled.</p>
                  : <ul className="space-y-2 text-sm">{rep.unscheduled.map((u: Unscheduled, i: number) => <li key={i}><b>{u.subject_code} – {u.subject_name}</b> ({u.session}): <span className="text-red-700">{u.reason}</span></li>)}</ul>}</div>
              {rep.issues.length > 0 && <div className="card p-4"><h2 className="mb-2 font-semibold">Diagnostics</h2>
                <ul className="space-y-1 text-sm">{rep.issues.map((i: { severity: string; message: string }, k: number) => <li key={k}><span className="font-medium capitalize">{i.severity}:</span> {i.message}</li>)}</ul></div>}
            </div>
          )}
        </>
      )}
    </div>
  );
}
