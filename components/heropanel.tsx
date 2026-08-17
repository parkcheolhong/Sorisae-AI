import type { DashboardSummary } from '../lib/types';

export function HeroPanel({ summary }: { summary: DashboardSummary }) {
  return (
    <section className="hero">
      <div className="heroHeader">
        <div>
          <p className="eyebrow">{summary.eyebrow}</p>
          <h1 className="heroTitle">{summary.headline}</h1>
        </div>
        <div className="heroBadge">{summary.badge}</div>
      </div>
      <p className="heroCopy">{summary.description}</p>
      <div className="heroHighlights">
        {summary.highlights.map((item) => (
          <div key={item} className="heroHighlight">{item}</div>
        ))}
      </div>
      <div className="heroActions">
        <a href={summary.primaryHref} className="primaryButton">{summary.primaryLabel}</a>
        <a href={summary.secondaryHref} className="secondaryButton">{summary.secondaryLabel}</a>
      </div>
    </section>
  );
}
