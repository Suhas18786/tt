import CrudPage from "../components/CrudPage";
import { useLookups } from "../lookups";
import { ROOM_TYPES, SUBJECT_TYPES } from "../types";

const toOpts = (r: Record<string, string>) => Object.entries(r).map(([value, label]) => ({ value, label }));

export default function SubjectsPage() {
  const { data } = useLookups();
  const dept = (id: number) => data.departments.find((d) => d.id === id)?.code ?? id;
  return (
    <CrudPage<any> title="Subjects" noun="subject" endpoint="/subjects" searchPlaceholder="Search by code or name…"
      subtitle="Weekly hours are counted in periods. A lab with consecutive periods is scheduled as one continuous block."
      filters={[
        { name: "department_id", label: "Department", options: data.departments.map((d) => ({ value: d.id, label: d.name })) },
        { name: "subject_type", label: "Type", options: toOpts(SUBJECT_TYPES) },
        { name: "semester_number", label: "Semester", options: Array.from({ length: 8 }, (_, i) => ({ value: i + 1, label: `Semester ${i + 1}` })) },
      ]}
      columns={[
        { key: "code", label: "Code" }, { key: "name", label: "Name" },
        { key: "department_id", label: "Dept", render: (r) => dept(r.department_id) },
        { key: "semester_number", label: "Sem" },
        { key: "subject_type", label: "Type", render: (r) => SUBJECT_TYPES[r.subject_type] },
        { key: "weekly_hours", label: "Hrs/wk" },
        { key: "session_duration", label: "Session", render: (r) => `${r.session_duration}${r.consecutive_required ? " (consecutive)" : ""}` },
        { key: "room_type", label: "Room", render: (r) => ROOM_TYPES[r.room_type] },
      ]}
      fields={[
        { name: "code", label: "Subject code", type: "text", required: true, maxLength: 30 },
        { name: "name", label: "Subject name", type: "text", required: true, maxLength: 200 },
        { name: "department_id", label: "Department", type: "select", required: true, options: data.departments.map((d) => ({ value: d.id, label: `${d.code} – ${d.name}` })) },
        { name: "semester_number", label: "Semester", type: "number", required: true, min: 1, max: 12 },
        { name: "subject_type", label: "Type", type: "select", required: true, default: "lecture", options: toOpts(SUBJECT_TYPES) },
        { name: "room_type", label: "Required room type", type: "select", required: true, default: "lecture_room", options: toOpts(ROOM_TYPES) },
        { name: "weekly_hours", label: "Required weekly hours (periods)", type: "number", required: true, min: 1, max: 30 },
        { name: "session_duration", label: "Session duration (periods)", type: "number", required: true, min: 1, max: 6, default: 1 },
        { name: "difficulty", label: "Difficulty (1–3)", type: "number", required: true, min: 1, max: 3, default: 1, hint: "Used to avoid stacking hard subjects on one day." },
        { name: "consecutive_required", label: "Session periods must be consecutive", type: "checkbox" },
        { name: "required_equipment", label: "Required equipment", type: "tags", placeholder: "projector, lab-kit" },
      ]} />
  );
}
