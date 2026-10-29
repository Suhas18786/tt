import { ReactNode, useState } from "react";
import { Navigate, NavLink, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import { Spinner } from "./ui";
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

const ADMIN_NAV: [string, string][] = [
  ["/", "Dashboard"], ["/generator", "Generate timetable"], ["/timetables", "Timetables"], ["/reports", "Reports"],
  ["/faculty", "Faculty"], ["/subjects", "Subjects"], ["/batches", "Student batches"], ["/assignments", "Teaching assignments"],
  ["/rooms", "Classrooms & labs"], ["/setup", "Departments & terms"], ["/conflicts", "Conflict reports"],
];
const FACULTY_NAV: [string, string][] = [
  ["/", "My timetable"], ["/availability", "My availability"], ["/conflicts", "Report a conflict"],
];

function Shell() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  const nav = user?.role === "admin" ? ADMIN_NAV : FACULTY_NAV;
  return (
    <div className="flex min-h-screen">
      {open && <div className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden" onClick={() => setOpen(false)} />}
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-brand-900 text-brand-100 transition-transform lg:static lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}
        aria-label="Main navigation">
        <div className="flex items-center gap-2 px-5 py-5 text-white">
          <svg width="28" height="28" viewBox="0 0 100 100"><rect width="100" height="100" rx="18" fill="#2f6bb3" /><path d="M22 30h56M22 50h56M22 70h56M40 22v56M62 22v56" stroke="white" strokeWidth="6" fill="none" /></svg>
          <div className="leading-tight"><div className="font-semibold">Timetable</div><div className="text-xs text-brand-200">University scheduler</div></div>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 pb-4">
          {nav.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"} onClick={() => setOpen(false)}
              className={({ isActive }) => `block rounded-md px-3 py-2 text-sm font-medium ${isActive ? "bg-brand-700 text-white" : "hover:bg-brand-800 hover:text-white"}`}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-brand-800 p-4 text-sm">
          <div className="truncate font-medium text-white">{user?.full_name}</div>
          <div className="truncate text-xs capitalize text-brand-200">{user?.role} · {user?.email}</div>
          <button onClick={logout} className="mt-3 w-full rounded-md border border-brand-700 px-3 py-1.5 text-sm hover:bg-brand-800">Sign out</button>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
          <button className="btn-secondary !px-2.5" onClick={() => setOpen(true)} aria-label="Open menu">☰</button>
          <span className="font-semibold">Timetable Generator</span>
        </header>
        <main className="min-w-0 flex-1 p-4 sm:p-6 lg:p-8" key={loc.pathname}><Outlet /></main>
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
        <Route path="/availability" element={<FacultyOnly><MyAvailability /></FacultyOnly>} />
        <Route path="/conflicts" element={<ConflictReports />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
