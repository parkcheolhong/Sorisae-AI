import type { BriefPayload, DashboardSummary, FocusItem, RuntimeSignal, SummaryMetric } from './types';

export const dashboardSummary: DashboardSummary = {
  eyebrow: 'Operations canvas',
  headline: 'Release confidence with visible ownership.',
  badge: 'Template 2026.03',
  description: 'The generated dashboard acts like an editorial control room: planning context, runtime signals, and ship-readiness cues all sit in one deliberately designed surface.',
  highlights: [
    'Planning, validation, and release ownership are separated into clear lanes instead of one noisy feed.',
    'Each runtime card explains the operational meaning, not only the current color.',
    'Landing and dashboard surfaces share one data contract so the generated output remains deterministic.',
  ],
  primaryLabel: 'Open dashboard',
  primaryHref: '/dashboard',
  secondaryLabel: 'Read live brief',
  secondaryHref: '/api/brief',
};

export const summaryMetrics: SummaryMetric[] = [
  { label: 'Evidence coverage', value: '92%', detail: 'Traceability rows already linked to implementation and validation artifacts.' },
  { label: 'Runtime window', value: '14m', detail: 'Average time from checklist freeze to release handoff in the last dry-run.' },
  { label: 'Approval delta', value: '+3', detail: 'Three ownership gaps were closed before the final shipment review.' },
  { label: 'Recovery headroom', value: '2.4x', detail: 'Queue and incident buffers remain below the recovery escalation threshold.' },
];

export const runtimeSignals: RuntimeSignal[] = [
  { label: 'Approval gate', status: 'Green and locked', detail: 'Completion and semantic gates passed with no missing release evidence.', owner: 'Reviewer', tone: 'healthy' },
  { label: 'Queue watch', status: '6 tasks waiting', detail: 'Background queue remains under the recovery threshold with room for one more rollout.', owner: 'Runtime', tone: 'watch' },
  { label: 'Brief posture', status: 'Ready for live handoff', detail: 'The release brief is already reduced to operator-facing language for the final check.', owner: 'Reasoner', tone: 'planning' },
  { label: 'Evidence sync', status: 'Docs and code aligned', detail: 'The dashboard and route payloads use the same typed contract and update together.', owner: 'Planner', tone: 'healthy' },
];

export const focusRail: FocusItem[] = [
  { title: 'Lock scope early', summary: 'Freeze the visible release promise before the implementation lane expands and turns into rework.', owner: 'Planner' },
  { title: 'Explain runtime meaning', summary: 'Turn raw metrics into operator language so the release conversation stays decision-oriented.', owner: 'Reasoner' },
  { title: 'Ship only with evidence', summary: 'Keep route checks, build output, and ownership traces attached to the final handoff packet.', owner: 'Reviewer' },
];

export const releaseTimeline = [
  'Morning: freeze the change brief and confirm the live evidence packet.',
  'Midday: compare dashboard payloads, queue state, and route contract drift.',
  'Afternoon: finalize owner handoff notes, then ship from the same release canvas.',
];

export const defaultBriefPayload: BriefPayload = {
  summary: dashboardSummary,
  metrics: summaryMetrics,
  runtimeSignals,
  focusRail,
  releaseTimeline,
  refreshedAt: 'seeded-static-brief',
};
