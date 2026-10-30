import { Fragment, useState } from "react";
import { DAYS, Period, Session } from "../types";

const PALETTE = [
  ["#dbeafe", "#1e40af"], ["#dcfce7", "#166534"], ["#fef3c7", "#92400e"], ["#fce7f3", "#9d174d"], ["#e0e7ff", "#3730a3"],
  ["#ccfbf1", "#115e59"], ["#ffedd5", "#9a3412"], ["#f3e8ff", "#6b21a8"], ["#fee2e2", "#991b1b"], ["#ecfccb", "#3f6212"],
  ["#cffafe", "#155e75"], ["#e5e7eb", "#1f2937"],
];
export const subjectColor = (id: number) => PALETTE[id % PALETTE.length];

export type GridView = "batch" | "faculty" | "room" | "mixed";

interface Props {
  config: { working_days: number[]; periods: Period[]; blocked_slots?: number[][] };
  sessions: Session[]; view: GridView; editable?: boolean; highlightIds?: number[];
  onMove?: (s: Session, day: number, period: number) => void; onSessionClick?: (s: Session) => void;
}

function lines(s: Session, view: GridView): string[] {
  if (view === "batch") return [s.faculty_name, s.room_label];
  if (view === "faculty") return [s.batch_code, s.room_label];
  if (view === "room") return [s.batch_code, s.faculty_name];
  return [s.batch_code, s.faculty_name, s.room_label];
}

const isLab = (s: Session) => s.subject_type === "lab";

export default function TimetableGrid({ config, sessions, view, editable, highlightIds = [], onMove, onSessionClick }: Props) {
  const [dragId, setDragId] = useState<number | null>(null);
  const [over, setOver] = useState<string | null>(null);
  const blocked = new Set((config.blocked_slots ?? []).map(([d, p]) => `${d}-${p}`));

  const drop = (d: number, p: number) => {
    setOver(null);
    const s = sessions.find((x) => x.id === dragId);
    setDragId(null);
    if (s && onMove && (s.day !== d || s.start_period !== p)) onMove(s, d, p);
  };

  const card = (s: Session, periodIndex: number) => {
    const [bg, fg] = subjectColor(s.subject_id);
    const cont = s.start_period !== periodIndex;
    const bad = highlightIds.includes(s.id);
    return (
      <div key={s.id} draggable={!!editable && !cont}
        onDragStart={(e) => { setDragId(s.id); e.dataTransfer.setData("text/plain", String(s.id)); e.dataTransfer.effectAllowed = "move"; }}
        onDragEnd={() => { setDragId(null); setOver(null); }}
        onClick={() => onSessionClick?.(s)} role={onSessionClick ? "button" : undefined} tabIndex={onSessionClick ? 0 : undefined}
        onKeyDown={(e) => { if (onSessionClick && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); onSessionClick(s); } }}
        title={`${s.subject_name} (${s.subject_code}) · ${s.faculty_name} · ${s.room_label} · ${s.batch_code}`}
        style={{ backgroundColor: bg, color: fg, borderColor: fg }}
        className={`min-h-0 flex-1 overflow-hidden rounded-md border-l-4 px-1.5 py-1 text-[11px] leading-tight ${editable && !cont ? "cursor-grab active:cursor-grabbing" : onSessionClick ? "cursor-pointer" : ""} ${cont ? "opacity-70" : ""} ${bad ? "ring-2 ring-red-500" : ""} ${dragId === s.id ? "opacity-40" : ""}`}>
        <div className="font-bold">{s.subject_code}{cont && <span className="font-normal"> (cont.)</span>}</div>
        {!cont && <>
          <div className="truncate opacity-90">{s.subject_name}</div>
          {lines(s, view).map((l, i) => <div key={i} className="truncate">{l}</div>)}
        </>}
      </div>
    );
  };

  const cell = (d: number, p: Period, lab: boolean) => {
    const slot = `${d}-${p.index}-${lab ? "lab" : "class"}`;
    const here = sessions.filter((s) => s.day === d && s.start_period <= p.index && p.index < s.start_period + s.duration && isLab(s) === lab);
    const isOver = over === slot;
    return (
      <td key={slot}
        className={`h-24 border-b border-r border-slate-200 p-1 align-top ${lab ? "bg-slate-50/70" : ""} ${isOver ? "bg-brand-50 ring-2 ring-inset ring-brand-500" : ""}`}
        onDragOver={editable ? (e) => { e.preventDefault(); setOver(slot); } : undefined}
        onDragLeave={editable ? () => setOver((o) => (o === slot ? null : o)) : undefined}
        onDrop={editable ? (e) => { e.preventDefault(); drop(d, p.index); } : undefined}>
        <div className="flex h-full flex-col gap-1">{here.map((s) => card(s, p.index))}</div>
      </td>
    );
  };

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
      <table className="w-full min-w-[980px] table-fixed border-collapse" aria-label="Weekly timetable">
        <thead>
          <tr>
            <th rowSpan={2} className="w-28 border-b border-r border-slate-200 bg-slate-50 p-2 text-left text-xs font-semibold text-slate-500">Period</th>
            {config.working_days.map((d) => <th key={d} colSpan={2} className="border-b border-r border-slate-200 bg-slate-50 p-2 text-sm font-semibold text-slate-700">{DAYS[d]}</th>)}
          </tr>
          <tr>
            {config.working_days.map((d) => (
              <Fragment key={d}>
                <th className="border-b border-r border-slate-200 bg-slate-50 px-2 py-1 text-left text-[11px] font-medium text-slate-500">Lectures &amp; tutorials</th>
                <th className="border-b border-r border-slate-200 bg-slate-100 px-2 py-1 text-left text-[11px] font-semibold text-slate-600">Lab</th>
              </Fragment>
            ))}
          </tr>
        </thead>
        <tbody>
          {config.periods.map((p) => (
            <tr key={p.index}>
              <th className="border-b border-r border-slate-200 bg-slate-50 p-2 text-left align-top text-xs font-medium text-slate-600">
                <div>Period {p.index + 1}</div><div className="font-normal text-slate-500">{p.start}–{p.end}</div>
                {p.kind !== "class" && <div className="mt-0.5 text-[10px] font-semibold text-slate-400">{p.kind}</div>}
              </th>
              {config.working_days.map((d) => {
                if (p.kind !== "class") return <td key={d} colSpan={2} className="border-b border-r border-slate-200 bg-slate-100 text-center text-[11px] capitalize text-slate-400">{p.kind}</td>;
                if (blocked.has(`${d}-${p.index}`)) return <td key={d} colSpan={2} className="border-b border-r border-slate-200 bg-slate-200 text-center text-[11px] text-slate-500">Blocked</td>;
                return <Fragment key={d}>{cell(d, p, false)}{cell(d, p, true)}</Fragment>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
