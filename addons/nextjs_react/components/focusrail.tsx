import type { FocusItem } from '../lib/types';

export function FocusRail({ title, items }: { title: string; items: FocusItem[] }) {
  return (
    <section className="sectionCard">
      <p className="eyebrow">Focus</p>
      <h2>{title}</h2>
      <div className="railList">
        {items.map((item) => (
          <article key={item.title} className="railItem">
            <div className="microLabel">{item.owner}</div>
            <h3 style={{ marginTop: 8 }}>{item.title}</h3>
            <p className="muted" style={{ marginTop: 8 }}>{item.summary}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
