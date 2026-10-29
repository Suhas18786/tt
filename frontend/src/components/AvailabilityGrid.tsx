import { DAYS, Period } from "../types";

export type SlotMap = Record<string, string>;   // "day-period" -> status
export const slotKey = (d: number, p: number) => `${d}-${p}`;

interface Props {
  workingDays: number[]; periods: Period[]; value: SlotMap; onChange: (v: SlotMap) => void;
  mode: "faculty" | "blocked"; disabled?: boolean;
}

const CYCLE: Record<Props["mode"], string[]> = { faculty: ["", "unavailable", "preferred"], blocked: ["", "blocked"] };
const STYLE: Record<string, string> = {
  "": "bg-white hover:bg-slate-50 text-slate-400", unavailable: "bg-red-100 text-red-800 hover:bg-red-200",
  preferred: "bg-emerald-100 text-emerald-800 hover:bg-emerald-200", blocked: "bg-slate-300 text-slate-700 hover:bg-slate-400",
};
const LABEL: Record<string, string> = { "": "Available", unavailable: "✕ Unavailable", preferred: "★ Preferred", blocked: "✕ Blocked" };

export default function AvailabilityGrid({ workingDays, periods, value, onChange, mode, disabled }: Props) {
  const cycle = (d: number, p: number) => {
    if (disabled) return;
    const cur = value[slotKey(d, p)] ?? "";
    const seq = CYCLE[mode];
    const next = seq[(seq.indexOf(cur) + 1) % seq.length];
    const copy = { ...value };
    if (next) copy[slotKey(d, p)] = next; else delete copy[slotKey(d, p)];
    onChange(copy);
  };
  const toggleDay = (d: number) => {
    if (disabled) return;
    const classP = periods.filter((p) => p.kind === "class");
    const all = classP.every((p) => value[slotKey(d, p.index)]);
    const copy = { ...value };
    classP.forEach((p) => { if (all) delete copy[slotKey(d, p.index)]; else copy[slotKey(d, p.index)] = mode === "faculty" ? "unavailable" : "blocked"; });
    onChange(copy);
  };
  return (
    <div>
      <div className="mb-2 flex flex-wrap gap-3 text-xs text-slate-600">
        {CYCLE[mode].map((s) => <span key={s} className="inline-flex items-center gap-1.5"><span className={`inline-block h-3 w-3 rounded border border-slate-300 ${STYLE[s].split(" ")[0]}`} />{LABEL[s]}</span>)}
        <span className="text-slate-500">Click a cell to change it; click a day name to toggle the whole day.</span>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-xs">
          <thead><tr>
            <th className="w-28 border border-slate-200 bg-slate-50 p-2 text-left">Period</th>
            {workingDays.map((d) => <th key={d} className="border border-slate-200 bg-slate-50 p-0">
              <button type="button" className="w-full p-2 font-semibold hover:bg-slate-100" onClick={() => toggleDay(d)}>{DAYS[d].slice(0, 3)}</button></th>)}
          </tr></thead>
          <tbody>
            {periods.map((p) => (
              <tr key={p.index}>
                <th className="border border-slate-200 bg-slate-50 p-2 text-left font-medium">{p.start}–{p.end}{p.kind !== "class" && <span className="ml-1 capitalize text-slate-400">({p.kind})</span>}</th>
                {workingDays.map((d) => p.kind !== "class"
                  ? <td key={d} className="border border-slate-200 bg-slate-100" />
                  : <td key={d} className="border border-slate-200 p-0">
                    <button type="button" disabled={disabled} onClick={() => cycle(d, p.index)}
                      className={`h-9 w-full text-[11px] transition ${STYLE[value[slotKey(d, p.index)] ?? ""]}`}
                      aria-label={`${DAYS[d]} ${p.start}: ${LABEL[value[slotKey(d, p.index)] ?? ""]}`}>
                      {value[slotKey(d, p.index)] ? LABEL[value[slotKey(d, p.index)]].split(" ")[0] : ""}
                    </button></td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
