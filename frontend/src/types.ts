export interface User { id: number; email: string; full_name: string; role: "admin" | "faculty"; faculty_id: number | null }
export interface Period { index: number; start: string; end: string; kind: "class" | "break" | "lunch" }
export interface Config {
  working_days: number[]; periods: Period[]; blocked_slots: number[][]; weights: Record<string, number>;
  max_consecutive: number; time_limit_seconds: number; max_daily_hours_override: number | null; weight_keys?: string[];
}
export interface Lookups {
  departments: { id: number; code: string; name: string }[];
  academic_years: { id: number; name: string; is_current: boolean }[];
  semesters: { id: number; academic_year_id: number; number: number; name: string }[];
  batches: { id: number; code: string; name: string; department_id: number; semester_id: number; strength: number }[];
  faculty: { id: number; name: string; code: string; department_id: number; max_hours_per_day: number; max_hours_per_week: number }[];
  subjects: { id: number; code: string; name: string; department_id: number; semester_number: number; weekly_hours: number }[];
  rooms: { id: number; label: string; room_type: string; capacity: number }[];
}
export interface Session {
  id: number; assignment_id: number; batch_id: number; batch_code: string; department_id: number; department_code: string;
  semester_id: number; subject_id: number; subject_code: string; subject_name: string; subject_type: string;
  faculty_id: number; faculty_name: string; room_id: number; room_label: string; room_type: string;
  day: number; start_period: number; duration: number;
}
export interface Violation { code: string; message: string; session_ids: number[] }
export interface Unscheduled { assignment_id: number; session: string; subject_code: string; subject_name: string; batch_id: number; faculty_id: number; duration: number; reason: string }
export interface Issue { severity: string; code: string; message: string }
export interface Generation {
  id: number; name: string; status: "preview" | "draft" | "published" | "archived" | "infeasible";
  semester_id: number | null; department_id: number | null; batch_ids: number[]; solver_status: string;
  objective: number | null; solve_seconds: number | null; created_at: string; published_at: string | null;
  unscheduled_count: number; expected_sessions: number;
  config?: { working_days: number[]; periods: Period[]; blocked_slots: number[][] };
  report?: { complete: boolean; issues: Issue[]; unscheduled: Unscheduled[]; stats: Record<string, number>; expected_sessions: number };
  sessions?: Session[];
  workload?: { faculty_id: number; faculty_name: string; hours: number; required: number; max_hours_per_week: number }[];
  validation?: { ok: boolean; violations: Violation[]; unscheduled: number };
}
export interface Page<T> { items: T[]; total: number; page: number; page_size: number }
export const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
export const ROOM_TYPES: Record<string, string> = { lecture_room: "Lecture room", computer_lab: "Computer lab", laboratory: "Laboratory" };
export const SUBJECT_TYPES: Record<string, string> = { lecture: "Lecture", tutorial: "Tutorial", lab: "Laboratory" };
