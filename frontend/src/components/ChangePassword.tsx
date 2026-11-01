import { FormEvent, useState } from "react";
import { api } from "../api";
import { ErrorBanner, Field, Modal, Spinner, useToast } from "../ui";

export default function ChangePassword({ onClose }: { onClose: () => void }) {
  const toast = useToast();
  const [cur, setCur] = useState("");
  const [next, setNext] = useState("");
  const [again, setAgain] = useState("");
  const [fe, setFe] = useState<{ cur?: string; next?: string; again?: string }>({});
  const [err, setErr] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const f: typeof fe = {};
    if (!cur) f.cur = "Enter your current password";
    if (next.length < 8) f.next = "Use at least 8 characters";
    else if (next === cur) f.next = "Choose a password different from the current one";
    if (again !== next) f.again = "The two passwords do not match";
    setFe(f);
    if (Object.keys(f).length) return;
    setBusy(true); setErr(null);
    try {
      await api("/auth/change-password", { method: "POST", body: { current_password: cur, new_password: next } });
      toast("success", "Password changed");
      onClose();
    } catch (x) { setErr(x); } finally { setBusy(false); }
  };

  return (
    <Modal title="Change password" onClose={onClose}
      footer={<><button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
        <button type="submit" form="change-password-form" className="btn-primary" disabled={busy}>{busy && <Spinner className="h-4 w-4" />}Change password</button></>}>
      <form id="change-password-form" onSubmit={submit} noValidate className="space-y-4">
        <ErrorBanner error={err} />
        <Field label="Current password" error={fe.cur} required>
          <input className="input" type="password" autoComplete="current-password" value={cur} onChange={(e) => setCur(e.target.value)} autoFocus />
        </Field>
        <Field label="New password" error={fe.next} hint="At least 8 characters." required>
          <input className="input" type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />
        </Field>
        <Field label="Repeat new password" error={fe.again} required>
          <input className="input" type="password" autoComplete="new-password" value={again} onChange={(e) => setAgain(e.target.value)} />
        </Field>
      </form>
    </Modal>
  );
}
