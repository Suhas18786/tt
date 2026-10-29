import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import TimetableWorkspace from "../components/TimetableWorkspace";
import { Generation } from "../types";
import { Badge, EmptyState, ErrorBanner, PageHeader, Spinner } from "../ui";

interface Hist { id: number; generation_id: number | null; generation_name: string; action: string; note: string; created_at: string }

export default function Timetables() {
  const { id } = useParams();
  const nav = useNavigate();
  const [list, setList] = useState<Generation[] | null>(null);
  const [hist, setHist] = useState<Hist[]>([]);
  const [error, setError] = useState<unknown>(null);

  const load = () => {
    api<Generation[]>("/timetables").then(setList).catch(setError);
    api<Hist[]>("/timetables/history").then(setHist).catch(() => {});
  };
  useEffect(load, [id]);

  if (id) {
    return (
      <div>
        <PageHeader title="Timetable" actions={<Link className="btn-secondary" to="/timetables">← All timetables</Link>} />
        <TimetableWorkspace id={+id} onDeleted={() => nav("/timetables")} />
      </div>
    );
  }
  return (
    <div>
      <PageHeader title="Timetables" subtitle="Generated, draft and published timetables. Only one published timetable can exist per batch."
        actions={<Link className="btn-primary" to="/generator">+ Generate new</Link>} />
      <ErrorBanner error={error} />
      <div className="card overflow-hidden">
        {!list ? <div className="p-8 text-center"><Spinner /></div> : list.length === 0 ? (
          <EmptyState title="No timetables yet" hint="Generate your first timetable from the sample or your own data." action={<Link className="btn-primary" to="/generator">Generate timetable</Link>} />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50"><tr><th className="th">#</th><th className="th">Name</th><th className="th">Status</th><th className="th">Batches</th><th className="th">Sessions</th><th className="th">Solver</th><th className="th">Created</th><th className="th" /></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {list.map((g) => (
                  <tr key={g.id} className="hover:bg-slate-50/70">
                    <td className="td">{g.id}</td><td className="td font-medium">{g.name}</td><td className="td"><Badge>{g.status}</Badge></td>
                    <td className="td">{g.batch_ids.length}</td>
                    <td className="td">{g.expected_sessions - g.unscheduled_count}/{g.expected_sessions}{g.unscheduled_count > 0 && <span className="text-red-600"> ({g.unscheduled_count} missing)</span>}</td>
                    <td className="td">{g.solver_status}{g.solve_seconds != null && ` · ${g.solve_seconds}s`}</td>
                    <td className="td whitespace-nowrap">{new Date(g.created_at).toLocaleString()}</td>
                    <td className="td text-right"><Link className="btn-secondary !py-1" to={`/timetables/${g.id}`}>Open</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {hist.length > 0 && (
        <div className="card mt-6 overflow-hidden">
          <h2 className="border-b border-slate-200 px-4 py-3 font-semibold">Publication history</h2>
          <ul className="max-h-72 divide-y divide-slate-100 overflow-y-auto text-sm">
            {hist.map((h) => (
              <li key={h.id} className="flex flex-wrap gap-x-3 px-4 py-2">
                <span className="w-40 text-slate-500">{new Date(h.created_at).toLocaleString()}</span>
                <span className="w-28 font-medium capitalize">{h.action.replace("_", " ")}</span>
                <span>{h.generation_name}</span><span className="text-slate-500">{h.note}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
