import { useState } from "react";
import CrudPage from "../components/CrudPage";
import AvailabilityPanel from "../components/AvailabilityPanel";
import { useLookups } from "../lookups";
import { Badge, Modal } from "../ui";

interface Fac {
  id: number; faculty_code: string; full_name: string; email: string; department_id: number; max_hours_per_day: number;
  max_hours_per_week: number; qualified_subject_ids: number[]; assigned: { subject_code: string; hours: number }[]; assigned_hours: number; has_login: boolean;
}

export default function FacultyPage() {
  const { data } = useLookups();
  const [avail, setAvail] = useState<Fac | null>(null);
  const dept = (id: number) => data.departments.find((d) => d.id === id)?.code ?? id;
  return (
    <>
      <CrudPage<Fac> title="Faculty" noun="faculty member" endpoint="/faculty" searchPlaceholder="Search by ID, name or email…"
        filters={[{ name: "department_id", label: "Department", options: data.departments.map((d) => ({ value: d.id, label: d.name })) }]}
        columns={[
          { key: "faculty_code", label: "ID" }, { key: "full_name", label: "Name" }, { key: "email", label: "Email" },
          { key: "department_id", label: "Dept", render: (r) => dept(r.department_id) },
          { key: "hours", label: "Load", render: (r) => <span className={r.assigned_hours > r.max_hours_per_week ? "text-red-600" : ""}>{r.assigned_hours}/{r.max_hours_per_week} h/wk</span> },
          { key: "q", label: "Qualified", render: (r) => `${r.qualified_subject_ids.length} subjects` },
          { key: "login", label: "Login", render: (r) => r.has_login ? <Badge tone="published">Enabled</Badge> : <Badge>None</Badge> },
        ]}
        fields={[
          { name: "faculty_code", label: "Faculty ID", type: "text", required: true, maxLength: 30 },
          { name: "full_name", label: "Full name", type: "text", required: true, maxLength: 200 },
          { name: "email", label: "Email", type: "email", required: true },
          { name: "department_id", label: "Department", type: "select", required: true, options: data.departments.map((d) => ({ value: d.id, label: `${d.code} – ${d.name}` })) },
          { name: "max_hours_per_day", label: "Max teaching hours / day", type: "number", required: true, min: 1, max: 12, default: 5 },
          { name: "max_hours_per_week", label: "Max teaching hours / week", type: "number", required: true, min: 1, max: 60, default: 18 },
          { name: "initial_password", label: "Login password", type: "password", hint: "Optional. Set (or reset) the password this faculty member signs in with (min 8 characters)." },
          { name: "qualified_subject_ids", label: "Subjects qualified to teach", type: "multiselect", options: data.subjects.map((s) => ({ value: s.id, label: `${s.code} – ${s.name}` })) },
        ]}
        toForm={(r) => ({ ...r, initial_password: "" })}
        rowActions={(r) => <button className="btn-ghost !px-2 !py-1" onClick={() => setAvail(r)}>Availability</button>} />
      {avail && <Modal wide title={`Availability – ${avail.full_name}`} onClose={() => setAvail(null)}>
        <AvailabilityPanel facultyId={avail.id} onSaved={() => setAvail(null)} />
      </Modal>}
    </>
  );
}
