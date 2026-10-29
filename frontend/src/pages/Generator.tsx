import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import AvailabilityGrid, { SlotMap, slotKey } from "../components/AvailabilityGrid";
import TimetableWorkspace from "../components/TimetableWorkspace";
import { useLookups } from "../lookups";
import { Config, DAYS, Generation, Period } from "../types";
import { ErrorBanner, PageHeader, Spinner, useToast } from "../ui";

const WEIGHT_LABELS: Record<string, string> = {
  faculty_spread: "Spread faculty workload across the week", faculty_gaps: "Avoid gaps in faculty days", student_gaps: "Minimise batch idle periods",
  consecutive: "Avoid too many consecutive periods", subject_spread: "Spread repeated sessions over different days", preferred: "Respect faculty preferred periods",
  room_balance: "Balance classroom utilisation", difficulty: "Avoid piling hard subjects on one day",
};
const toMin = (t: string) => { const [h, m] = t.split(":").map(Number); return h * 60 + m; };
const fmt = (m: number) => `${String(Math.floor(m / 60) % 24).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;

function buildPeriods(start: string, minutes: number, count: number, lunchAfter: number, breakAfter: number, breakMin: number, lunchMin: number): Period[] {
  const out: Period[] = [];
  let t = toMin(start);
  const push = (len: number, kind: Period["kind"]) => { out.push({ index: out.length, start: fmt(t), end: fmt(t + len), kind }); t += len; };
  for (let i = 1; i <= count; i++) {
    push(minutes, "class");
    if (i === breakAfter && i !== count) push(breakMin, "break");
    if (i === lunchAfter && i !== count) push(lunchMin, "lunch");
  }
  return out;
}

export default function Generator() {
  const { data } = useLookups();
  const toast = useToast();
  const [cfg, setCfg] = useState<Config | null>(null);
  const [name, setName] = useState("Timetable");
  const [yearId, setYearId] = useState("");
  const [semId, setSemId] = useState("");
  const [deptId, setDeptId] = useState("");
  const [batchIds, setBatchIds] = useState<number[]>([]);
  const [days, setDays] = useState<number[]>([]);
  const [periods, setPeriods] = useState<Period[]>([]);
  const [blocked, setBlocked] = useState<SlotMap>({});
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [maxDaily, setMaxDaily] = useState("");
  const [timeLimit, setTimeLimit] = useState(30);
  const [maxConsec, setMaxConsec] = useState(3);
  const [assignments, setAssignments] = useState<{ id: number; batch_id: number; subject_id: number; faculty_id: number }[]>([]);
  const [excluded, setExcluded] = useState<number[]>([]);
  const [builder, setBuilder] = useState({ start: "09:00", minutes: 60, count: 6, lunchAfter: 3, breakAfter: 0, breakMin: 15, lunchMin: 60 });
  const [genId, setGenId] = useState<number | null>(null);
  const [running, setRunning] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => {
    api<Config>("/config").then((c) => {
      setCfg(c); setDays(c.working_days); setPeriods(c.periods); setWeights(c.weights);
      setBlocked(Object.fromEntries(c.blocked_slots.map(([d, p]) => [slotKey(d, p), "blocked"])));
      setMaxDaily(c.max_daily_hours_override ? String(c.max_daily_hours_override) : ""); setTimeLimit(c.time_limit_seconds); setMaxConsec(c.max_consecutive);
    }).catch(setError);
  }, []);

  const semesters = data.semesters.filter((s) => !yearId || s.academic_year_id === +yearId);
  const scopeBatches = useMemo(() => data.batches.filter((b) =>
    (!semId || b.semester_id === +semId) && (!deptId || b.department_id === +deptId)), [data.batches, semId, deptId]);
  useEffect(() => { setBatchIds((cur) => cur.filter((id) => scopeBatches.some((b) => b.id === id))); }, [scopeBatches]);
  const effectiveBatches = batchIds.length ? batchIds : scopeBatches.map((b) => b.id);

  useEffect(() => {
    api<{ items: typeof assignments }>("/assignments", { params: { page_size: 500 } }).then((r) => setAssignments(r.items)).catch(() => {});
  }, [data.batches.length]);
  const scopeAssignments = assignments.filter((a) => effectiveBatches.includes(a.batch_id));
  const subj = (id: number) => data.subjects.find((s) => s.id === id);

  const body = () => {
    const included = scopeAssignments.filter((a) => !excluded.includes(a.id)).map((a) => a.id);
    return {
      name, semester_id: semId ? +semId : undefined, department_id: deptId ? +deptId : undefined,
      batch_ids: effectiveBatches, assignment_ids: excluded.some((id) => scopeAssignments.some((a) => a.id === id)) ? included : undefined,
      working_days: days, periods, blocked_slots: Object.keys(blocked).map((k) => k.split("-").map(Number)), weights,
      max_consecutive: maxConsec, time_limit_seconds: timeLimit, max_daily_hours_override: maxDaily ? +maxDaily : null,
    };
  };

  const generate = async (replaceId?: number) => {
    if (!days.length) { setError(new Error("Select at least one working day.")); return; }
    if (!effectiveBatches.length) { setError(new Error("No student batches match the selected scope.")); return; }
    setRunning(true); setError(null); setElapsed(0);
    timer.current = window.setInterval(() => setElapsed((e) => e + 1), 1000);
    try {
      const gen = await api<Generation>("/timetables/generate", { method: "POST", body: { ...body(), replace_generation_id: replaceId } });
      setGenId(gen.id);
      toast(gen.status === "infeasible" ? "error" : "success", gen.status === "infeasible" ? "No complete timetable exists for these inputs — see the report." : "Timetable generated");
    } catch (e) { setError(e); } finally { window.clearInterval(timer.current); setRunning(false); }
  };

  const saveDefaults = async () => {
    try { await api("/config", { method: "PUT", body: { ...body(), semester_id: undefined, name: undefined } }); toast("success", "Saved as the default configuration"); }
    catch (e) { setError(e); }
  };

  if (!cfg) return error ? <ErrorBanner error={error} /> : <div className="p-10 text-center"><Spinner className="h-7 w-7" /></div>;
  const sec = "card space-y-4 p-4";
  const h = "text-base font-semibold text-slate-900";

  return (
    <div>
      <PageHeader title="Generate timetable" subtitle="Choose the scope and rules, then let the CP-SAT solver build a conflict-free weekly schedule." />
      <ErrorBanner error={error} onClose={() => setError(null)} />
      <div className="grid gap-5 xl:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]">
        <form className="space-y-5" onSubmit={(e) => { e.preventDefault(); generate(genId ?? undefined); }}>
          <section className={sec}>
            <h2 className={h}>1. Scope</h2>
            <label className="block text-sm font-medium">Timetable name<input className="input mt-1" value={name} onChange={(e) => setName(e.target.value)} required maxLength={200} /></label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block text-sm font-medium">Academic year
                <select className="input mt-1" value={yearId} onChange={(e) => { setYearId(e.target.value); setSemId(""); }}><option value="">All</option>
                  {data.academic_years.map((y) => <option key={y.id} value={y.id}>{y.name}</option>)}</select></label>
              <label className="block text-sm font-medium">Semester
                <select className="input mt-1" value={semId} onChange={(e) => setSemId(e.target.value)}><option value="">All</option>
                  {semesters.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
            </div>
            <label className="block text-sm font-medium">Department
              <select className="input mt-1" value={deptId} onChange={(e) => setDeptId(e.target.value)}><option value="">All departments</option>
                {data.departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></label>
            <fieldset>
              <legend className="mb-1 text-sm font-medium">Student batches <span className="font-normal text-slate-500">({batchIds.length ? batchIds.length : "all"} of {scopeBatches.length} selected)</span></legend>
              <div className="max-h-40 overflow-y-auto rounded-md border border-slate-300 p-2">
                {scopeBatches.length === 0 && <p className="text-sm text-slate-500">No batches match. Add batches first.</p>}
                {scopeBatches.map((b) => (
                  <label key={b.id} className="flex items-center gap-2 py-0.5 text-sm">
                    <input type="checkbox" checked={batchIds.includes(b.id)} onChange={(e) => setBatchIds(e.target.checked ? [...batchIds, b.id] : batchIds.filter((x) => x !== b.id))} />
                    {b.code} <span className="text-slate-500">· {b.strength} students</span>
                  </label>
                ))}
              </div>
              <p className="mt-1 text-xs text-slate-500">Leave all unticked to include every batch in scope. Published timetables of other batches stay untouched and their faculty/rooms are treated as busy.</p>
            </fieldset>
          </section>

          <section className={sec}>
            <h2 className={h}>2. Days & periods</h2>
            <div className="flex flex-wrap gap-2" role="group" aria-label="Working days">
              {DAYS.map((d, i) => (
                <label key={d} className={`cursor-pointer rounded-md border px-2.5 py-1 text-sm ${days.includes(i) ? "border-brand-600 bg-brand-50 text-brand-800" : "border-slate-300 text-slate-600"}`}>
                  <input type="checkbox" className="sr-only" checked={days.includes(i)} onChange={(e) => setDays(e.target.checked ? [...days, i].sort() : days.filter((x) => x !== i))} />{d.slice(0, 3)}
                </label>
              ))}
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs font-medium text-slate-600">
              <label>Day starts<input type="time" className="input mt-1" value={builder.start} onChange={(e) => setBuilder({ ...builder, start: e.target.value })} /></label>
              <label>Period (min)<input type="number" min={20} max={180} className="input mt-1" value={builder.minutes} onChange={(e) => setBuilder({ ...builder, minutes: +e.target.value })} /></label>
              <label>Class periods<input type="number" min={1} max={14} className="input mt-1" value={builder.count} onChange={(e) => setBuilder({ ...builder, count: +e.target.value })} /></label>
              <label>Lunch after #<input type="number" min={0} max={14} className="input mt-1" value={builder.lunchAfter} onChange={(e) => setBuilder({ ...builder, lunchAfter: +e.target.value })} /></label>
              <label>Lunch (min)<input type="number" min={10} max={120} className="input mt-1" value={builder.lunchMin} onChange={(e) => setBuilder({ ...builder, lunchMin: +e.target.value })} /></label>
              <label>Break after #<input type="number" min={0} max={14} className="input mt-1" value={builder.breakAfter} onChange={(e) => setBuilder({ ...builder, breakAfter: +e.target.value })} /></label>
            </div>
            <button type="button" className="btn-secondary w-full" onClick={() => {
              if (!builder.start || builder.minutes < 20 || builder.count < 1) return setError(new Error("Enter a valid start time, period length and period count."));
              setPeriods(buildPeriods(builder.start, builder.minutes, builder.count, builder.lunchAfter, builder.breakAfter, builder.breakMin, builder.lunchMin)); setBlocked({});
            }}>Build periods from these settings</button>
            <ul className="divide-y divide-slate-100 rounded-md border border-slate-200 text-sm">
              {periods.map((p, i) => (
                <li key={i} className="flex items-center gap-2 px-2 py-1.5">
                  <span className="w-6 text-slate-400">{i + 1}</span>
                  <input type="time" className="input !w-28 !py-1" value={p.start} aria-label={`Period ${i + 1} start`} onChange={(e) => setPeriods(periods.map((x, j) => j === i ? { ...x, start: e.target.value } : x))} />
                  <span>–</span>
                  <input type="time" className="input !w-28 !py-1" value={p.end} aria-label={`Period ${i + 1} end`} onChange={(e) => setPeriods(periods.map((x, j) => j === i ? { ...x, end: e.target.value } : x))} />
                  <select className="input !w-auto !py-1" value={p.kind} aria-label={`Period ${i + 1} type`} onChange={(e) => setPeriods(periods.map((x, j) => j === i ? { ...x, kind: e.target.value as Period["kind"] } : x))}>
                    <option value="class">Class</option><option value="break">Break</option><option value="lunch">Lunch</option>
                  </select>
                  <button type="button" className="ml-auto text-slate-400 hover:text-red-600" aria-label={`Remove period ${i + 1}`}
                    onClick={() => { setPeriods(periods.filter((_, j) => j !== i).map((x, j) => ({ ...x, index: j }))); setBlocked({}); }}>✕</button>
                </li>
              ))}
            </ul>
            <p className="text-xs text-slate-500">Break and lunch periods are never used for classes; sessions cannot span them.</p>
          </section>

          <section className={sec}>
            <h2 className={h}>3. Blocked periods <span className="text-xs font-normal text-slate-500">(optional)</span></h2>
            <AvailabilityGrid workingDays={days} periods={periods} value={blocked} onChange={setBlocked} mode="blocked" />
          </section>

          <section className={sec}>
            <h2 className={h}>4. Faculty & subject assignments</h2>
            <p className="text-xs text-slate-500">All teaching assignments for the selected batches are scheduled. Untick any to leave them out of this run.</p>
            <div className="max-h-56 overflow-y-auto rounded-md border border-slate-200">
              {scopeAssignments.length === 0 && <p className="p-3 text-sm text-slate-500">No assignments for the selected batches. Add them under Teaching assignments.</p>}
              {scopeAssignments.map((a) => (
                <label key={a.id} className="flex items-start gap-2 border-b border-slate-100 px-2 py-1.5 text-sm last:border-0">
                  <input type="checkbox" className="mt-1" checked={!excluded.includes(a.id)} onChange={(e) => setExcluded(e.target.checked ? excluded.filter((x) => x !== a.id) : [...excluded, a.id])} />
                  <span>{data.batches.find((b) => b.id === a.batch_id)?.code} · {subj(a.subject_id)?.code} ({subj(a.subject_id)?.weekly_hours}h)
                    <span className="block text-xs text-slate-500">{data.faculty.find((f) => f.id === a.faculty_id)?.name}</span></span>
                </label>
              ))}
            </div>
            <label className="block text-sm font-medium">Max daily hours per faculty (override)
              <input className="input mt-1" type="number" min={1} max={12} placeholder="Use each faculty member's own limit" value={maxDaily} onChange={(e) => setMaxDaily(e.target.value)} /></label>
          </section>

          <section className={sec}>
            <h2 className={h}>5. Optimisation priorities</h2>
            {Object.keys(weights).map((k) => (
              <label key={k} className="block text-sm">
                <span className="flex justify-between"><span>{WEIGHT_LABELS[k] ?? k}</span><span className="font-medium">{weights[k]}</span></span>
                <input type="range" min={0} max={10} className="w-full" value={weights[k]} onChange={(e) => setWeights({ ...weights, [k]: +e.target.value })} />
              </label>
            ))}
            <div className="grid grid-cols-2 gap-3">
              <label className="block text-sm font-medium">Max consecutive periods<input className="input mt-1" type="number" min={1} max={10} value={maxConsec} onChange={(e) => setMaxConsec(+e.target.value)} /></label>
              <label className="block text-sm font-medium">Solver time limit (s)<input className="input mt-1" type="number" min={1} max={600} value={timeLimit} onChange={(e) => setTimeLimit(+e.target.value)} /></label>
            </div>
            <p className="text-xs text-slate-500">Weights only affect preferences. Hard constraints are always enforced. 0 switches a preference off.</p>
          </section>

          <div className="sticky bottom-0 -mx-1 flex gap-2 bg-slate-50/90 p-1 backdrop-blur">
            <button className="btn-primary flex-1 !py-2.5" disabled={running}>{running && <Spinner className="h-4 w-4" />}{running ? "Generating…" : genId ? "Generate again" : "Generate timetable"}</button>
            <button type="button" className="btn-secondary" onClick={saveDefaults} title="Store days, periods and weights as the system default">Save as default</button>
          </div>
        </form>

        <div className="min-w-0">
          {running && (
            <div className="card flex flex-col items-center gap-3 p-12 text-center" role="status" aria-live="polite">
              <Spinner className="h-10 w-10 text-brand-600" />
              <p className="font-medium">Solving… {elapsed}s</p>
              <p className="max-w-md text-sm text-slate-500">The CP-SAT solver is searching for a schedule that satisfies every hard constraint and optimises your preferences. It stops at the time limit ({timeLimit}s) with the best solution found.</p>
            </div>
          )}
          {!running && genId && <TimetableWorkspace id={genId} regenerating={running} onRegenerate={() => generate(genId)} onDeleted={() => setGenId(null)} />}
          {!running && !genId && (
            <div className="card p-12 text-center text-slate-500">
              <p className="font-medium text-slate-700">No timetable generated yet</p>
              <p className="mt-1 text-sm">Set the scope on the left and press <b>Generate timetable</b>. The weekly grid, validation summary and any unscheduled sessions appear here.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
