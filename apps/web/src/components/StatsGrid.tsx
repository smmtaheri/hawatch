export function StatsGrid({ items }: { items: { label: string; value: string }[] }) {
  return (
    <section className="stats-grid">
      {items.map((item) => (
        <div className="route-stat card-surface" key={item.label}>
          <strong>{item.value}</strong>
          <span>{item.label}</span>
        </div>
      ))}
    </section>
  );
}
