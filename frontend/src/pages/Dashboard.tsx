import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Badge, Bar, EmptyState, ErrorBanner, PageHeader, Spinner, StatCard } from "../ui";

interface Dash {
  counts: { faculty: number; subjects: number; batches: number; classrooms: number; laboratories: number };
  open_conflict_reports: number;
  generation: { id: number; name: string; status: string; solver_status: string; solve_seconds: number | null } | null;
  sessions: { scheduled: number; unscheduled: number; expected: number };
  workload: { faculty_id: number; faculty_name: string; hours: number; required: number; max_hours_per_week: number }[];
  room_utilization: { room_id: number; room: string; used: number; capacity: number; percent: number }[];
  conflicts: { code: string; message: string }[];
  issues: { severity: string; message: string }[];
  status_counts: Record<string, number>;
}

export default function Dashboard() {
  const [d, setD] = useState<Dash | null>(null);
  const [err, setErr] = useState<unknown>(null);
  useEffect(() => { api<Dash>("/dashboard").then(setD).catch(setErr); }, []);
  if (err) return <ErrorBanner error={err} />;
  if (!d) return <div className="p-10 text-center"><Spinner className="h-7 w-7" /></div>;
  const g = d.generation;
  const pct = d.sessions.expected ? Math.round((100 * d.sessions.scheduled) / d.sessions.expected) : 0;
  const maxH = Math.max(1, ...d.workload.map((w) => Math.max(w.hours, w.required, w.max_hours_per_week)));

  return (
    <div>
      <PageHeader title="Dashboard" subtitle="Overview of your institution's scheduling data and the latest timetable."
        actions={<Link to="/generator" className="btn-primary">Generate timetable</Link>} />
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <StatCard label="Faculty" value={d.counts.faculty} />
        <StatCard label="Subjects" value={d.counts.subjects} />
        <StatCard label="Student batches" value={d.counts.batches} />
        <StatCard label="Classrooms" value={d.counts.classrooms} />
        <StatCard label="Labs" value={d.counts.laboratories} />
        <StatCard label="Open conflict reports" value={d.open_conflict_reports} tone={d.open_conflict_reports ? "amber" : "green"} />
      </div>

      {!g ? <div className="card"><EmptyState title="No timetable generated yet" hint="Generate one to see scheduling status, workload and room utilisation here."
        action={<Link to="/generator" className="btn-primary">Generate timetable</Link>} /></div> : (
        <div className="grid gap-5 lg:grid-cols-3">
          <div className="card p-4 lg:col-span-1">
            <h2 className="mb-3 font-semibold">Generation status</h2>
            <div className="flex items-center gap-2"><Link className="font-medium text-brand-700 hover:underline" to={`/timetables/${g.id}`}>{g.name}</Link><Badge>{g.status}</Badge></div>
            <p className="mt-1 text-xs text-slate-500">Solver: {g.solver_status}{g.solve_seconds != null && ` · ${g.solve_seconds}s`}</p>
            <div className="mt-4">
              <div className="mb-1 flex justify-between text-sm"><span>Scheduled vs required</span><span className="font-medium">{d.sessions.scheduled}/{d.sessions.expected}</span></div>
              <Bar value={d.sessions.scheduled} max={d.sessions.expected} tone={d.sessions.unscheduled ? "bg-amber-500" : "bg-emerald-500"} label="Scheduled sessions" />
              <p className="mt-1 text-xs text-slate-500">{pct}% placed · <span className={d.sessions.unscheduled ? "font-medium text-red-600" : ""}>{d.sessions.unscheduled} unscheduled</span></p>
            </div>
            <div className="mt-4 flex flex-wrap gap-1.5">{Object.entries(d.status_counts).map(([k, v]) => <span key={k} className="text-xs"><Badge>{k}</Badge> ×{v}</span>)}</div>
          </div>

          <div className="card p-4 lg:col-span-2">
            <h2 className="mb-3 font-semibold">Detected conflicts & constraint issues</h2>
            {d.conflicts.length === 0 && d.issues.length === 0
              ? <p className="text-sm text-emerald-700">✓ No conflicts or infeasible constraints detected in the latest timetable.</p>
              : <ul className="max-h-48 space-y-1.5 overflow-y-auto text-sm">
                {d.conflicts.map((c, i) => <li key={`c${i}`} className="text-red-700">✕ {c.message}</li>)}
                {d.issues.map((c, i) => <li key={`i${i}`} className={c.severity === "error" ? "text-red-700" : "text-amber-700"}>{c.severity === "error" ? "✕" : "!"} {c.message}</li>)}
              </ul>}
          </div>

          <div className="card p-4 lg:col-span-2">
            <h2 className="mb-3 font-semibold">Faculty workload distribution <span className="text-xs font-normal text-slate-500">(hours scheduled of required, against the weekly limit)</span></h2>
            {d.workload.length === 0 ? <p className="text-sm text-slate-500">No teaching assignments in this timetable.</p> : (
              <ul className="max-h-80 space-y-2.5 overflow-y-auto pr-2">
                {d.workload.map((w) => (
                  <li key={w.faculty_id}>
                    <div className="flex justify-between text-sm"><span>{w.faculty_name}</span><span className="text-slate-500">{w.hours} of {w.required} scheduled · limit {w.max_hours_per_week}</span></div>
                    <Bar value={w.hours} max={maxH} tone={w.hours > w.max_hours_per_week ? "bg-red-500" : "bg-brand-600"} label={w.faculty_name} />
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="card p-4 lg:col-span-1">
            <h2 className="mb-3 font-semibold">Classroom utilisation</h2>
            {d.room_utilization.length === 0 ? <p className="text-sm text-slate-500">No rooms in use.</p> : (
              <ul className="max-h-80 space-y-2.5 overflow-y-auto pr-2">
                {d.room_utilization.map((r) => (
                  <li key={r.room_id}>
                    <div className="flex justify-between text-sm"><span>{r.room}</span><span className="text-slate-500">{r.percent}%</span></div>
                    <Bar value={r.used} max={r.capacity} tone="bg-teal-600" label={r.room} />
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
