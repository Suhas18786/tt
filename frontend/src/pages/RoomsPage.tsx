import { useEffect, useState } from "react";
import { api } from "../api";
import AvailabilityGrid, { SlotMap, slotKey } from "../components/AvailabilityGrid";
import CrudPage from "../components/CrudPage";
import { ErrorBanner, Modal, Spinner, useToast } from "../ui";
import { Config, ROOM_TYPES } from "../types";

function BlockedEditor({ room, onClose }: { room: any; onClose: () => void }) {
  const toast = useToast();
  const [cfg, setCfg] = useState<Config | null>(null);
  const [val, setVal] = useState<SlotMap>({});
  const [err, setErr] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    Promise.all([api<Config>("/config"), api<{ slots: number[][] }>(`/classrooms/${room.id}/blocked`)])
      .then(([c, b]) => { setCfg(c); setVal(Object.fromEntries(b.slots.map(([d, p]) => [slotKey(d, p), "blocked"]))); }).catch(setErr);
  }, [room.id]);
  const save = async () => {
    setSaving(true);
    try {
      await api(`/classrooms/${room.id}/blocked`, { method: "PUT", body: { slots: Object.keys(val).map((k) => k.split("-").map(Number)) } });
      toast("success", "Room availability saved");
      onClose();
    } catch (e) { setErr(e); } finally { setSaving(false); }
  };
  return (
    <Modal wide title={`Available time slots – ${room.building}-${room.room_number}`} onClose={onClose}
      footer={<><button className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary" onClick={save} disabled={saving || !cfg}>{saving && <Spinner className="h-4 w-4" />}Save</button></>}>
      <ErrorBanner error={err} />
      {!cfg ? <Spinner /> : <><p className="mb-3 text-sm text-slate-600">Mark the periods when this room is <b>not</b> available. Everything else is available.</p>
        <AvailabilityGrid workingDays={cfg.working_days} periods={cfg.periods} value={val} onChange={setVal} mode="blocked" /></>}
    </Modal>
  );
}

export default function RoomsPage() {
  const [blocked, setBlocked] = useState<any>(null);
  const opts = Object.entries(ROOM_TYPES).map(([value, label]) => ({ value, label }));
  return (
    <>
      <CrudPage<any> title="Classrooms & labs" noun="room" endpoint="/classrooms" searchPlaceholder="Search room or building…"
        filters={[{ name: "room_type", label: "Type", options: opts }]}
        columns={[
          { key: "building", label: "Building" }, { key: "room_number", label: "Room" },
          { key: "room_type", label: "Type", render: (r) => ROOM_TYPES[r.room_type] }, { key: "capacity", label: "Capacity" },
          { key: "equipment", label: "Equipment", render: (r) => (r.equipment ?? []).join(", ") || "—" },
        ]}
        fields={[
          { name: "building", label: "Building", type: "text", required: true, maxLength: 100 },
          { name: "room_number", label: "Room number", type: "text", required: true, maxLength: 30 },
          { name: "room_type", label: "Room type", type: "select", required: true, default: "lecture_room", options: opts },
          { name: "capacity", label: "Seating capacity", type: "number", required: true, min: 1, max: 2000 },
          { name: "equipment", label: "Equipment", type: "tags", placeholder: "projector, lab-kit" },
        ]}
        rowActions={(r) => <button className="btn-ghost !px-2 !py-1" onClick={() => setBlocked(r)}>Time slots</button>} />
      {blocked && <BlockedEditor room={blocked} onClose={() => setBlocked(null)} />}
    </>
  );
}
