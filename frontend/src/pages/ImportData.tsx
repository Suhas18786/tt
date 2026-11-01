import { ChangeEvent, useState } from "react";
import { api } from "../api";
import { useLookups } from "../lookups";
import { ErrorBanner, PageHeader, Spinner, useToast } from "../ui";

interface Result { dry_run: boolean; rows: number; created: Record<string, number>; already_existed: Record<string, number>; warnings: string[] }
type Kind = "teaching-plan" | "rooms";

const SECTIONS: { kind: Kind; key: "teaching_plan" | "rooms"; title: string; blurb: string; file: string }[] = [
  { kind: "teaching-plan", key: "teaching_plan", title: "Teaching plan", file: "teaching-plan-template.csv",
    blurb: "One row per batch, subject and faculty member. Creates the departments, batches, subjects, faculty and teaching assignments in one go. Records that already exist (matched by code) are reused, not changed." },
  { kind: "rooms", key: "rooms", title: "Classrooms and labs", file: "rooms-template.csv",
    blurb: "One row per room. Rooms that already exist (same building and room number) are skipped." },
];

function Section({ s }: { s: (typeof SECTIONS)[number] }) {
  const toast = useToast();
  const { reload } = useLookups();
  const [text, setText] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);
  const [res, setRes] = useState<Result | null>(null);

  const pick = async (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    setRes(null); setErr(null);
    if (!f) { setText(""); setName(""); return; }
    if (f.size > 1_500_000) { setErr(new Error("That file is too large (limit 1.5 MB).")); return; }
    setText(await f.text()); setName(f.name);
  };
  const template = async () => {
    try {
      const t = await api<Record<string, string>>("/admin/import/templates");
      const url = URL.createObjectURL(new Blob([t[s.key]], { type: "text/csv" }));
      const a = document.createElement("a"); a.href = url; a.download = s.file; a.click(); URL.revokeObjectURL(url);
    } catch (x) { setErr(x); }
  };
  const run = async (dry: boolean) => {
    setBusy(true); setErr(null);
    try {
      const r = await api<Result>(`/admin/import/${s.kind}`, { method: "POST", body: { csv: text, dry_run: dry } });
      setRes(r);
      if (!dry) { toast("success", "Import finished"); await reload(); }
    } catch (x) { setErr(x); setRes(null); } finally { setBusy(false); }
  };
  const line = (o: Record<string, number>) => Object.entries(o).filter(([, n]) => n > 0).map(([k, n]) => `${n} ${k}`).join(", ") || "none";

  return (
    <section className="card mb-5 p-5">
      <h2 className="text-lg font-semibold">{s.title}</h2>
      <p className="mt-1 text-sm text-slate-600">{s.blurb}</p>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button className="btn-secondary" onClick={template}>Download template</button>
        <label className="btn-secondary cursor-pointer">Choose CSV file
          <input type="file" accept=".csv,text/csv" className="sr-only" onChange={pick} /></label>
        {name && <span className="text-sm text-slate-600">{name}</span>}
      </div>
      <div className="mt-4"><ErrorBanner error={err} onClose={() => setErr(null)} /></div>
      <div className="flex flex-wrap gap-2">
        <button className="btn-secondary" disabled={!text || busy} onClick={() => run(true)}>{busy && <Spinner className="h-4 w-4" />}Check file</button>
        <button className="btn-primary" disabled={!text || busy} onClick={() => run(false)}>Import</button>
      </div>
      {res && (
        <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm" role="status">
          <p className="font-medium">{res.dry_run ? "Check passed. Nothing has been saved yet." : "Imported."} {res.rows} rows read.</p>
          <p className="mt-1">{res.dry_run ? "Would create" : "Created"}: {line(res.created)}.</p>
          <p>Already existed: {line(res.already_existed)}.</p>
          {res.warnings.length > 0 && <ul className="mt-2 list-disc space-y-0.5 pl-5 text-amber-800">{res.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>}
        </div>
      )}
    </section>
  );
}

export default function ImportData() {
  return (
    <div>
      <PageHeader title="Import from CSV" subtitle="Load faculty, subjects, batches and rooms from a spreadsheet saved as CSV. Use Check file first to find mistakes without saving anything." />
      {SECTIONS.map((s) => <Section key={s.kind} s={s} />)}
    </div>
  );
}
