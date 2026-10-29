import { FormEvent, useState } from "react";
import { useAuth } from "../auth";
import { ErrorBanner, Field, Spinner } from "../ui";

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [fieldErr, setFieldErr] = useState<{ email?: string; password?: string }>({});

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const fe: typeof fieldErr = {};
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) fe.email = "Enter a valid email address";
    if (!password) fe.password = "Enter your password";
    setFieldErr(fe);
    if (Object.keys(fe).length) return;
    setBusy(true);
    try { await login(email.trim(), password); } catch (x) { setErr(x); } finally { setBusy(false); }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-900 to-brand-700 p-4">
      <form onSubmit={submit} noValidate className="card w-full max-w-sm space-y-4 p-7">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">University Timetable Generator</h1>
          <p className="mt-1 text-sm text-slate-500">Sign in as an administrator or faculty member.</p>
        </div>
        <ErrorBanner error={err} />
        <Field label="Email" error={fieldErr.email}>
          <input className="input" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
        </Field>
        <Field label="Password" error={fieldErr.password}>
          <input className="input" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <button className="btn-primary w-full" disabled={busy}>{busy && <Spinner className="h-4 w-4" />}Sign in</button>
        <p className="rounded-md bg-slate-50 p-3 text-xs text-slate-500">
          Sample data accounts: <code>admin@university.edu</code> / <code>Admin@123</code>. Faculty accounts use <code>Faculty@123</code>. Change these before any real deployment.
        </p>
      </form>
    </div>
  );
}
