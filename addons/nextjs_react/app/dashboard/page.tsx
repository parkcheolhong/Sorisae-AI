import { DashboardClient } from '../../components/dashboardclient';
import { defaultBriefPayload } from '../../lib/data';

export default function DashboardPage() {
  return <DashboardClient variant="detail" initialPayload={defaultBriefPayload} />;
}
