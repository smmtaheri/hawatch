import { Link } from "react-router-dom";
import type { SimilarDestinationSummary } from "../types";
import { DestinationIcon } from "./PointIcon";

function SimilarDestinationCard({ destination }: { destination: SimilarDestinationSummary }) {
  const meta = [destination.short_category || destination.category, destination.region].filter(Boolean).join(" · ");

  return (
    <Link to={destination.href} className="route-card similar-destination-card">
      <DestinationIcon
        categoryKey={destination.category_key}
        placeType={destination.place_type}
        className="route-icon similar-destination-icon"
      />
      <span className="route-copy similar-destination-copy">
        <h3>{destination.name}</h3>
        <small className="route-details">
          <span className="route-detail">{meta || "مقصد"}</span>
          <span className="route-detail">{destination.elevation_label}</span>
        </small>
      </span>
      <span className="compact-route-arrow similar-destination-arrow" aria-hidden="true">
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

  const desktop = variant === "desktop";

  return (
    <section
      className={desktop
        ? "similar-destinations-card desktop-route-selection top-routes-card compact-route-box card-surface"
        : "similar-destinations-card mobile-route-selection"}
      aria-label={title}
    >
      <div className={desktop ? "compact-route-heading" : "mobile-route-selection-heading"}>
        <div>
          <span className="eyebrow teal-text">تصمیم بعدی</span>
          <h2>{title}</h2>
        </div>
        {!desktop ? <span className="mobile-route-selection-count">{destinations.length} مقصد</span> : null}
      </div>
      <div className={desktop ? "route-cards desktop-route-cards" : "mobile-route-selection-top"}>
        {destinations.map((destination) => (
          <SimilarDestinationCard key={destination.slug} destination={destination} />
        ))}
      </div>
    </section>
  );
}
