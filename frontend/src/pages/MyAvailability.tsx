import AvailabilityPanel from "../components/AvailabilityPanel";
import { useAuth } from "../auth";
import { EmptyState, PageHeader } from "../ui";

export default function MyAvailability() {
  const { user } = useAuth();
  return (
    <div>
      <PageHeader title="My availability & preferences" subtitle="The scheduler never places classes in periods you mark unavailable, and tries to use your preferred periods." />
      <div className="card p-4">
        {user?.faculty_id ? <AvailabilityPanel facultyId={user.faculty_id} /> : <EmptyState title="No faculty profile linked" hint="Ask the administrator to link your account to a faculty record." />}
      </div>
    </div>
  );
}
