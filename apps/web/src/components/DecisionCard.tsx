export function DecisionCard({
  chip,
  title,
  text,
}: {
  chip: string;
  title: string;
  text: string;
}) {
  return (
    <section className="destination-decision-card card-surface">
      <span className="decision-chip">{chip}</span>
      <h2>{title}</h2>
      <p>{text}</p>
    </section>
  );
}
