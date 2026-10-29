import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import TimetableGrid from "../components/TimetableGrid";
import { Period, Session } from "../types";
import { Bar, EmptyState, ErrorBanner, PageHeader, Spinner, StatCard } from "../ui";

interface Mine { faculty_name: string; config: { working_days: number[]; periods: Period[]; blocked_slots: number[][] } | null; sessions: Session[]; generation_ids: number[] }
interface Load {
  faculty: { max_hours_per_day: number; max_hours_per_week: number };
  assignments: { assignment_id: number; batch_id: number; subject_code: string; subject_name: string; weekly_hours: number; type: string }[];
  total_hours: number;
}

export default function MyTimetable() {
  const [t, setT] = useState<Mine | null>(null);
  const [w, setW] = useState<Load | null>(null);
  const [err, setErr] = useState<unknown>(null);
  useEffect(() => {
    api<Mine>("/me/timetable").then(setT).catch(setErr);
    api<Load>("/me/workload").then(setW).catch(setErr);
  }, []);
  if (err) return <ErrorBanner error={err} />;
  if (!t || !w) return <div className="p-10 text-center"><Spinner className="h-7 w-7" /></div>;
  const scheduled = t.sessions.reduce((a, s) => a + s.duration, 0);
  return (
    <div>
      <PageHeader title="My timetable" subtitle={`Published schedule for ${t.faculty_name}.`} actions={<Link to="/conflicts" className="btn-secondary">Report a conflict</Link>} />
      <div className="mb-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Assigned hours / week" value={w.total_hours} sub={`Limit ${w.faculty.max_hours_per_week}`} />
        <StatCard label="Scheduled hours" value={scheduled} tone="green" />
        <StatCard label="Subjects" value={new Set(w.assignments.map((a) => a.subject_code)).size} />
        <StatCard label="Max per day" value={w.faculty.max_hours_per_day} />
      </div>
      {t.config && t.sessions.length > 0
        ? <TimetableGrid config={t.config} sessions={t.sessions} view="faculty" />
        : <div className="card"><EmptyState title="No published timetable yet" hint="Your classes will appear here as soon as the administrator publishes a timetable." /></div>}
      <div className="card mt-5 overflow-hidden">
        <h2 className="border-b border-slate-200 px-4 py-3 font-semibold">Assigned subjects & workload</h2>
        {w.assignments.length === 0 ? <EmptyState title="No subjects assigned" /> : (
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50"><tr><th className="th">Subject</th><th className="th">Type</th><th className="th">Hours / week</th><th className="th w-1/3">Share of limit</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {w.assignments.map((a) => <tr key={a.assignment_id}><td className="td">{a.subject_code} – {a.subject_name}</td><td className="td capitalize">{a.type}</td><td className="td">{a.weekly_hours}</td>
                <td className="td"><Bar value={a.weekly_hours} max={w.faculty.max_hours_per_week} label={a.subject_code} /></td></tr>)}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
