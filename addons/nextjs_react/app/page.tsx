import { DashboardClient } from '../components/dashboardclient';
import { defaultBriefPayload } from '../lib/data';

export default function HomePage() {
  return <DashboardClient variant="overview" initialPayload={defaultBriefPayload} />;
}
