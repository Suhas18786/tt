import CrudPage from "../components/CrudPage";
import { useLookups } from "../lookups";

export default function BatchesPage() {
  const { data } = useLookups();
  const dept = (id: number) => data.departments.find((d) => d.id === id)?.code ?? id;
  const sem = (id: number) => {
    const s = data.semesters.find((x) => x.id === id);
    const y = s && data.academic_years.find((a) => a.id === s.academic_year_id);
    return s ? `${s.name}${y ? ` (${y.name})` : ""}` : id;
  };
  const semOpts = data.semesters.map((s) => ({ value: s.id, label: `${s.name} – ${data.academic_years.find((a) => a.id === s.academic_year_id)?.name ?? ""}` }));
  return (
    <CrudPage<any> title="Student batches" noun="batch" endpoint="/batches" searchPlaceholder="Search batches…"
      filters={[
        { name: "department_id", label: "Department", options: data.departments.map((d) => ({ value: d.id, label: d.name })) },
        { name: "semester_id", label: "Semester", options: semOpts },
      ]}
      columns={[
        { key: "code", label: "Code" }, { key: "name", label: "Name" }, { key: "section", label: "Section" },
        { key: "department_id", label: "Dept", render: (r) => dept(r.department_id) },
        { key: "semester_id", label: "Semester", render: (r) => sem(r.semester_id) },
        { key: "strength", label: "Students" },
      ]}
      fields={[
        { name: "code", label: "Batch code", type: "text", required: true, maxLength: 30 },
        { name: "name", label: "Batch name", type: "text", required: true, maxLength: 200 },
        { name: "section", label: "Section", type: "text", maxLength: 10, default: "A" },
        { name: "strength", label: "Number of students", type: "number", required: true, min: 1, max: 1000, hint: "Rooms must seat at least this many." },
        { name: "department_id", label: "Department", type: "select", required: true, options: data.departments.map((d) => ({ value: d.id, label: `${d.code} – ${d.name}` })) },
        { name: "semester_id", label: "Semester", type: "select", required: true, options: semOpts },
      ]} />
  );
}
