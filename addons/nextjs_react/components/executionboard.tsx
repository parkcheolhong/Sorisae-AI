export function ExecutionBoard({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="sectionCard">
      <p className="eyebrow">Execution</p>
      <h2>{title}</h2>
      <div className="list">
        {items.map((item, index) => (
          <div key={`${title}-${index}`} className="listItem">
            <strong style={{ color: 'var(--accent)' }}>Step {index + 1}</strong> {item}
          </div>
        ))}
      </div>
    </section>
  );
}
