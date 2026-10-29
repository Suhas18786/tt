import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { Badge, EmptyState, ErrorBanner, Field, Modal, PageHeader, Spinner, useToast } from "../ui";

interface Report { id: number; faculty_name: string; generation_id: number | null; message: string; status: string; admin_note: string; created_at: string; resolved_at: string | null }

export default function ConflictReports() {
  const { user } = useAuth();
  const admin = user?.role === "admin";
  const toast = useToast();
  const [rows, setRows] = useState<Report[] | null>(null);
  const [err, setErr] = useState<unknown>(null);
  const [msg, setMsg] = useState("");
  const [msgErr, setMsgErr] = useState("");
  const [saving, setSaving] = useState(false);
  const [resolve, setResolve] = useState<Report | null>(null);
  const [note, setNote] = useState("");

  const load = useCallback(() => { api<Report[]>("/conflict-reports").then(setRows).catch(setErr); }, []);
  useEffect(load, [load]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (msg.trim().length < 5) { setMsgErr("Please describe the conflict (at least 5 characters)."); return; }
    setMsgErr(""); setSaving(true);
    try { await api("/conflict-reports", { method: "POST", body: { message: msg.trim() } }); setMsg(""); toast("success", "Report sent to the administrator"); load(); }
    catch (x) { setErr(x); } finally { setSaving(false); }
  };
  const doResolve = async () => {
    if (!resolve) return;
    setSaving(true);
    try { await api(`/conflict-reports/${resolve.id}/resolve`, { method: "POST", body: { admin_note: note } }); toast("success", "Marked as resolved"); setResolve(null); setNote(""); load(); }
    catch (x) { setErr(x); setResolve(null); } finally { setSaving(false); }
  };

  return (
    <div>
      <PageHeader title={admin ? "Conflict reports" : "Report a timetable conflict"} subtitle={admin ? "Issues raised by faculty about the published timetable." : "Tell the administrator about a clash or problem with your timetable."} />
      <ErrorBanner error={err} onClose={() => setErr(null)} />
      {!admin && (
        <form onSubmit={submit} noValidate className="card mb-5 space-y-3 p-4">
          <Field label="What is the conflict?" error={msgErr} required>
            <textarea className="input min-h-[96px]" maxLength={2000} value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="e.g. I teach CS201 in Room B-204 on Monday 10:00 but that room is booked for an exam." />
          </Field>
          <button className="btn-primary" disabled={saving}>{saving && <Spinner className="h-4 w-4" />}Send report</button>
        </form>
      )}
      <div className="card overflow-hidden">
        {!rows ? <div className="p-8 text-center"><Spinner /></div> : rows.length === 0 ? <EmptyState title="No reports" hint={admin ? "Nothing has been reported." : "You haven't reported anything."} /> : (
          <ul className="divide-y divide-slate-100">
            {rows.map((r) => (
              <li key={r.id} className="p-4">
                <div className="flex flex-wrap items-center gap-2"><Badge>{r.status}</Badge>{admin && <span className="font-medium">{r.faculty_name}</span>}
                  <span className="text-xs text-slate-500">{new Date(r.created_at).toLocaleString()}</span>
                  {admin && r.status === "open" && <button className="btn-secondary ml-auto !py-1" onClick={() => { setResolve(r); setNote(""); }}>Resolve</button>}</div>
                <p className="mt-2 whitespace-pre-wrap text-sm">{r.message}</p>
                {r.admin_note && <p className="mt-2 rounded-md bg-slate-50 p-2 text-sm text-slate-600"><b>Admin note:</b> {r.admin_note}</p>}
              </li>
            ))}
          </ul>
        )}
      </div>
      {resolve && (
        <Modal title="Resolve report" onClose={() => setResolve(null)} footer={<><button className="btn-secondary" onClick={() => setResolve(null)}>Cancel</button>
          <button className="btn-primary" onClick={doResolve} disabled={saving}>Mark resolved</button></>}>
          <p className="mb-3 text-sm text-slate-600">{resolve.message}</p>
          <Field label="Note to faculty (optional)"><textarea className="input" maxLength={2000} value={note} onChange={(e) => setNote(e.target.value)} /></Field>
        </Modal>
      )}
    </div>
  );
}
