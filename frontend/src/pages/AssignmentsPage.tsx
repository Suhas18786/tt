import CrudPage from "../components/CrudPage";
import { useLookups } from "../lookups";

export default function AssignmentsPage() {
  const { data } = useLookups();
  const batch = (id: number) => data.batches.find((b) => b.id === id)?.code ?? id;
  const subject = (id: number) => { const s = data.subjects.find((x) => x.id === id); return s ? `${s.code} – ${s.name}` : id; };
  const fac = (id: number) => data.faculty.find((f) => f.id === id)?.name ?? id;
  return (
    <CrudPage<any> title="Teaching assignments" noun="assignment" endpoint="/assignments" searchPlaceholder="Filter using the dropdowns…"
      subtitle="Which faculty member teaches which subject to which batch. Different batches can have different faculty for the same subject."
      filters={[
        { name: "batch_id", label: "Batch", options: data.batches.map((b) => ({ value: b.id, label: b.code })) },
        { name: "faculty_id", label: "Faculty", options: data.faculty.map((f) => ({ value: f.id, label: f.name })) },
        { name: "subject_id", label: "Subject", options: data.subjects.map((s) => ({ value: s.id, label: s.code })) },
      ]}
      columns={[
        { key: "batch_id", label: "Batch", render: (r) => batch(r.batch_id) },
        { key: "subject_id", label: "Subject", render: (r) => subject(r.subject_id) },
        { key: "faculty_id", label: "Faculty", render: (r) => fac(r.faculty_id) },
        { key: "hours", label: "Weekly hours", render: (r) => data.subjects.find((s) => s.id === r.subject_id)?.weekly_hours ?? "" },
      ]}
      fields={[
        { name: "batch_id", label: "Student batch", type: "select", required: true, options: data.batches.map((b) => ({ value: b.id, label: `${b.code} – ${b.name}` })) },
        { name: "subject_id", label: "Subject", type: "select", required: true, options: data.subjects.map((s) => ({ value: s.id, label: `${s.code} – ${s.name}` })) },
        { name: "faculty_id", label: "Faculty", type: "select", required: true, options: data.faculty.map((f) => ({ value: f.id, label: `${f.name} (${f.code})` })),
          hint: "Must be qualified for the subject (set on the Faculty page)." },
      ]} />
  );
}
