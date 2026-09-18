import { Link } from "react-router-dom";
import type { SimilarDestinationSummary } from "../types";
import { DestinationIcon } from "./PointIcon";

function SimilarDestinationCard({ destination }: { destination: SimilarDestinationSummary }) {
  return (
    <Link to={destination.href} className="similar-destination-card">
      <DestinationIcon
        categoryKey={destination.category_key}
        placeType={destination.place_type}
        className="similar-destination-icon"
      />
      <span className="similar-destination-copy">
        <strong>{destination.name}</strong>
        <small>
          {destination.place_type_label}
          {destination.region ? ` · ${destination.region}` : ""}
        </small>
        <small>{destination.elevation_label}</small>
      </span>
      <span className="similar-destination-arrow" aria-hidden="true">
        ←
      </span>
    </Link>
  );
}

export function SimilarDestinations({
  destinations,
  title,
  variant,
}: {
  destinations: SimilarDestinationSummary[];
  title: string;
  variant: "mobile" | "desktop";
}) {
  if (!destinations.length) return null;

  return (
    <section
      className={`similar-destinations-card card-surface similar-destinations-card--${variant}`}
      aria-label={title}
    >
      <div className="similar-destinations-heading">
        <div>
          <span className="eyebrow teal-text">تصمیم بعدی</span>
          <h2>{title}</h2>
        </div>
        <span className="similar-destinations-count">{destinations.length} مقصد</span>
      </div>
      <div className="similar-destinations-grid">
        {destinations.map((destination) => (
          <SimilarDestinationCard key={destination.slug} destination={destination} />
        ))}
      </div>
    </section>
  );
}
