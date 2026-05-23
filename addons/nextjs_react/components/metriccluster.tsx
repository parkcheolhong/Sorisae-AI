import type { SummaryMetric } from '../lib/types';

export function MetricCluster({ metrics, compact = false }: { metrics: SummaryMetric[]; compact?: boolean }) {
  return (
    <section className={compact ? 'metricGrid compactMetrics' : 'metricGrid'}>
      {metrics.map((metric) => (
        <article key={metric.label} className="metricCard">
          <div className="metricLabel">{metric.label}</div>
          <div className="metricValue">{metric.value}</div>
          <p className="metricDetail">{metric.detail}</p>
        </article>
      ))}
    </section>
  );
}
