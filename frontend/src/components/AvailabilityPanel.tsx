import { useEffect, useState } from "react";
import { api } from "../api";
import { ErrorBanner, Spinner, useToast } from "../ui";
import type { Config } from "../types";
import AvailabilityGrid, { SlotMap, slotKey } from "./AvailabilityGrid";

/** Load/edit/save one faculty member's availability + preferred periods (shared by admin modal and faculty portal). */
export default function AvailabilityPanel({ facultyId, onSaved }: { facultyId: number; onSaved?: () => void }) {
  const toast = useToast();
  const [cfg, setCfg] = useState<Config | null>(null);
  const [val, setVal] = useState<SlotMap>({});
  const [err, setErr] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([api<Config>("/config"), api<{ slots: { day: number; period: number; status: string }[] }>(`/faculty/${facultyId}/availability`)])
      .then(([c, a]) => { setCfg(c); setVal(Object.fromEntries(a.slots.map((s) => [slotKey(s.day, s.period), s.status]))); })
      .catch(setErr);
  }, [facultyId]);

  const save = async () => {
    if (!cfg) return;
    setSaving(true);
    try {
      const slots = Object.entries(val)
        .map(([k, status]) => { const [day, period] = k.split("-").map(Number); return { day, period, status }; })
        .filter((s) => cfg.working_days.includes(s.day));
      await api(`/faculty/${facultyId}/availability`, { method: "PUT", body: { slots } });
      toast("success", "Availability saved");
      setErr(null);
      onSaved?.();
    } catch (e) { setErr(e); } finally { setSaving(false); }
  };

  if (!cfg) return err ? <ErrorBanner error={err} /> : <div className="p-6 text-center text-slate-400"><Spinner /></div>;
  return (
    <div>
      <ErrorBanner error={err} />
      <p className="mb-3 text-sm text-slate-600">Mark periods when the faculty member cannot teach (hard rule) or prefers to teach (soft preference). Unmarked periods are available.</p>
      <AvailabilityGrid workingDays={cfg.working_days} periods={cfg.periods} value={val} onChange={setVal} mode="faculty" />
      <div className="mt-4 flex justify-end"><button className="btn-primary" onClick={save} disabled={saving}>{saving && <Spinner className="h-4 w-4" />}Save availability</button></div>
    </div>
  );
}
