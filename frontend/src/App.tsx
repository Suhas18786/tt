import { ReactNode, useState } from "react";
import { Navigate, NavLink, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import { LogoMark, Spinner } from "./ui";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Setup from "./pages/Setup";
import FacultyPage from "./pages/FacultyPage";
import SubjectsPage from "./pages/SubjectsPage";
import BatchesPage from "./pages/BatchesPage";
import RoomsPage from "./pages/RoomsPage";
import AssignmentsPage from "./pages/AssignmentsPage";
import Generator from "./pages/Generator";
import Timetables from "./pages/Timetables";
import Reports from "./pages/Reports";
import MyTimetable from "./pages/MyTimetable";
import MyAvailability from "./pages/MyAvailability";
import ConflictReports from "./pages/ConflictReports";
import ImportData from "./pages/ImportData";

type NavGroup = { title: string; items: [string, string][] };
const ADMIN_NAV: NavGroup[] = [
  { title: "Schedule", items: [["/", "Dashboard"], ["/generator", "Generate timetable"], ["/timetables", "Timetables"], ["/reports", "Reports"], ["/conflicts", "Conflict reports"]] },
  { title: "Data", items: [["/faculty", "Faculty"], ["/subjects", "Subjects"], ["/batches", "Student batches"], ["/assignments", "Teaching assignments"], ["/rooms", "Classrooms & labs"], ["/setup", "Departments & terms"], ["/import", "Import from CSV"]] },
];
const FACULTY_NAV: NavGroup[] = [
  { title: "My schedule", items: [["/", "My timetable"], ["/availability", "My availability"], ["/conflicts", "Report a conflict"]] },
];

function Shell() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  const groups = user?.role === "admin" ? ADMIN_NAV : FACULTY_NAV;
  const initials = (user?.full_name ?? "?").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  return (
    <div className="flex min-h-screen">
      {open && <div className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden" onClick={() => setOpen(false)} />}
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-200 bg-white transition-transform lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}
        aria-label="Main navigation">
        <div className="flex items-center gap-2.5 px-5 py-5">
          <LogoMark />
          <div className="font-display text-lg font-bold leading-none text-slate-900">Timetable</div>
        </div>
        <nav className="flex-1 space-y-5 overflow-y-auto px-3 pb-4">
          {groups.map((g) => (
            <div key={g.title}>
              <p className="px-3 pb-1.5 text-xs font-semibold text-slate-400">{g.title}</p>
              <div className="space-y-0.5">
                {g.items.map(([to, label]) => (
                  <NavLink key={to} to={to} end={to === "/"} onClick={() => setOpen(false)}
                    className={({ isActive }) => `block rounded-lg px-3 py-2 text-sm font-medium transition ${isActive ? "bg-brand-50 font-semibold text-brand-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"}`}>
                    {label}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>
        <div className="m-3 flex items-center gap-3 rounded-xl bg-slate-50 p-3">
          <div className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-brand-600 text-sm font-bold text-white">{initials}</div>
          <div className="min-w-0 flex-1 leading-tight">
            <div className="truncate text-sm font-semibold text-slate-900">{user?.full_name}</div>
            <div className="truncate text-xs capitalize text-slate-500">{user?.role}</div>
          </div>
          <button onClick={logout} className="rounded-md px-2 py-1 text-xs font-semibold text-slate-500 hover:bg-white hover:text-slate-900" aria-label="Sign out">Sign out</button>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur lg:hidden">
          <button className="btn-secondary !px-2.5" onClick={() => setOpen(true)} aria-label="Open menu">☰</button>
          <LogoMark size={26} /><span className="font-display font-bold">Timetable</span>
        </header>
        <main className="min-w-0 flex-1 p-4 sm:p-6 lg:p-10" key={loc.pathname}><div className="mx-auto max-w-[1400px]"><Outlet /></div></main>
      </div>
    </div>
  );
}

function Protected() {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex h-screen items-center justify-center text-slate-500"><Spinner className="h-8 w-8" /></div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Shell />;
}

function AdminOnly({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  return user?.role === "admin" ? <>{children}</> : <Navigate to="/" replace />;
}
function FacultyOnly({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  return user?.role === "faculty" ? <>{children}</> : <Navigate to="/" replace />;
}
function Home() {
  const { user } = useAuth();
  return user?.role === "admin" ? <Dashboard /> : <MyTimetable />;
}

export default function App() {
  const { user } = useAuth();
  const A = (el: ReactNode) => <AdminOnly>{el}</AdminOnly>;
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route element={<Protected />}>
        <Route path="/" element={<Home />} />
        <Route path="/generator" element={A(<Generator />)} />
        <Route path="/timetables" element={A(<Timetables />)} />
        <Route path="/timetables/:id" element={A(<Timetables />)} />
        <Route path="/reports" element={A(<Reports />)} />
        <Route path="/faculty" element={A(<FacultyPage />)} />
        <Route path="/subjects" element={A(<SubjectsPage />)} />
        <Route path="/batches" element={A(<BatchesPage />)} />
        <Route path="/assignments" element={A(<AssignmentsPage />)} />
        <Route path="/rooms" element={A(<RoomsPage />)} />
        <Route path="/setup" element={A(<Setup />)} />
        <Route path="/import" element={A(<ImportData />)} />
        <Route path="/availability" element={<FacultyOnly><MyAvailability /></FacultyOnly>} />
        <Route path="/conflicts" element={<ConflictReports />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
