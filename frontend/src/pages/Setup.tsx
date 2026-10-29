import { useState } from "react";
import CrudPage from "../components/CrudPage";
import { useLookups } from "../lookups";
import { Badge, PageHeader } from "../ui";

export default function Setup() {
  const { data } = useLookups();
  const [tab, setTab] = useState<"departments" | "years" | "semesters">("departments");
  const yearName = (id: number) => data.academic_years.find((y) => y.id === id)?.name ?? id;
  return (
    <div>
      <PageHeader title="Departments, academic years & semesters" subtitle="The academic structure that batches, subjects and timetables hang off." />
      <div className="mb-4 flex gap-1 border-b border-slate-200" role="tablist">
        {([["departments", "Departments"], ["years", "Academic years"], ["semesters", "Semesters"]] as const).map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${tab === k ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-800"}`}>{l}</button>
        ))}
      </div>
      {tab === "departments" && <CrudPage embedded title="Departments" noun="department" endpoint="/departments"
        columns={[{ key: "code", label: "Code" }, { key: "name", label: "Name" }]}
        fields={[{ name: "code", label: "Code", type: "text", required: true, maxLength: 20 }, { name: "name", label: "Name", type: "text", required: true, maxLength: 200 }]} />}
      {tab === "years" && <CrudPage embedded title="Academic years" noun="academic year" endpoint="/academic-years"
        columns={[{ key: "name", label: "Year" }, { key: "is_current", label: "Current", render: (r: any) => r.is_current ? <Badge tone="published">Current</Badge> : "" }]}
        fields={[{ name: "name", label: "Name", type: "text", required: true, placeholder: "2026-27", pattern: /^\d{4}-\d{2,4}$/, patternMsg: "Use the format 2026-27" },
          { name: "is_current", label: "Current academic year", type: "checkbox" }]} />}
      {tab === "semesters" && <CrudPage embedded title="Semesters" noun="semester" endpoint="/semesters"
        columns={[{ key: "name", label: "Name" }, { key: "number", label: "Number" }, { key: "academic_year_id", label: "Academic year", render: (r: any) => yearName(r.academic_year_id) }]}
        filters={[{ name: "academic_year_id", label: "Year", options: data.academic_years.map((y) => ({ value: y.id, label: y.name })) }]}
        fields={[{ name: "academic_year_id", label: "Academic year", type: "select", required: true, options: data.academic_years.map((y) => ({ value: y.id, label: y.name })) },
          { name: "number", label: "Semester number", type: "number", required: true, min: 1, max: 12 },
          { name: "name", label: "Name", type: "text", required: true, maxLength: 60 }]} />}
    </div>
  );
}
