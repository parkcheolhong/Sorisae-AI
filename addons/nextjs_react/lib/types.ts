export interface DashboardSummary {
  eyebrow: string;
  headline: string;
  badge: string;
  description: string;
  highlights: string[];
  primaryLabel: string;
  primaryHref: string;
  secondaryLabel: string;
  secondaryHref: string;
}

export interface SummaryMetric {
  label: string;
  value: string;
  detail: string;
}

export interface RuntimeSignal {
  label: string;
  status: string;
  detail: string;
  owner: string;
  tone: 'healthy' | 'watch' | 'planning';
}

export interface FocusItem {
  title: string;
  summary: string;
  owner: string;
}

export interface BriefPayload {
  summary: DashboardSummary;
  metrics: SummaryMetric[];
  runtimeSignals: RuntimeSignal[];
  focusRail: FocusItem[];
  releaseTimeline: string[];
  refreshedAt: string;
}
