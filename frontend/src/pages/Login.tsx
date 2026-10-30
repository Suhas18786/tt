import { FormEvent, useState } from "react";
import { useAuth } from "../auth";
import { ErrorBanner, Field, LogoMark, Spinner } from "../ui";

// Decorative week grid: columns are days, blocks are classes of different length (purely visual).
const BLOCKS: { col: number; row: number; span: number; tone: string }[] = [
  { col: 0, row: 0, span: 1, tone: "bg-indigo-300" }, { col: 0, row: 2, span: 2, tone: "bg-emerald-300" },
  { col: 1, row: 1, span: 1, tone: "bg-amber-300" }, { col: 1, row: 3, span: 1, tone: "bg-indigo-300" },
  { col: 2, row: 0, span: 2, tone: "bg-rose-300" }, { col: 2, row: 3, span: 1, tone: "bg-emerald-300" },
  { col: 3, row: 1, span: 1, tone: "bg-emerald-300" }, { col: 3, row: 2, span: 1, tone: "bg-amber-300" },
  { col: 4, row: 0, span: 1, tone: "bg-amber-300" }, { col: 4, row: 2, span: 2, tone: "bg-indigo-300" },
];

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
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <section className="relative hidden flex-col justify-between overflow-hidden bg-brand-950 p-12 text-white lg:flex" aria-hidden="true">
        <div className="flex items-center gap-2.5"><LogoMark size={34} /><span className="font-display text-xl font-bold">Timetable</span></div>
        <div>
          <div className="mb-10 grid max-w-md grid-cols-5 gap-2.5" style={{ gridTemplateRows: "repeat(4, 3.2rem)" }}>
            {BLOCKS.map((b, i) => (
              <div key={i} className={`rounded-lg ${b.tone} opacity-90`} style={{ gridColumn: b.col + 1, gridRow: `${b.row + 1} / span ${b.span}` }} />
            ))}
          </div>
          <h2 className="max-w-md font-display text-4xl font-bold leading-tight">Every class in its place, with no clashes.</h2>
          <p className="mt-4 max-w-md text-brand-200">Faculty, rooms and student batches are checked against each other, so the week fits before anyone sees it.</p>
        </div>
        <p className="text-sm text-brand-200/70">University scheduling</p>
      </section>

      <section className="flex items-center justify-center bg-paper p-6">
        <form onSubmit={submit} noValidate className="w-full max-w-sm space-y-5">
          <div className="lg:hidden"><LogoMark size={36} /></div>
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Sign in</h1>
            <p className="mt-1.5 text-sm text-slate-500">Use your administrator or faculty account.</p>
          </div>
          <ErrorBanner error={err} />
          <Field label="Email" error={fieldErr.email}>
            <input className="input !py-2.5" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
          </Field>
          <Field label="Password" error={fieldErr.password}>
            <input className="input !py-2.5" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <button className="btn-primary w-full !py-2.5" disabled={busy}>{busy && <Spinner className="h-4 w-4" />}Sign in</button>
          <p className="rounded-lg border border-slate-200 bg-white p-3 text-xs leading-relaxed text-slate-500">
            Sample data: <code className="font-semibold text-slate-700">admin@university.edu</code> with <code className="font-semibold text-slate-700">Admin@123</code>. Faculty accounts use <code className="font-semibold text-slate-700">Faculty@123</code>. Change these before real use.
          </p>
        </form>
      </section>
    </div>
  );
}
