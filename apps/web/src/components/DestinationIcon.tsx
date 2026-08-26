export function DestinationIcon({ categoryKey }: { categoryKey: string }) {
  if (categoryKey === "volcano") {
    return (
      <svg viewBox="0 0 48 48" className="destination-icon volcano" aria-hidden="true">
        <path d="M5 39 16 20l7 5 5-10 15 24" />
        <path d="M24 15c-2-4 2-5 0-9M29 13c3-3 1-6 4-8" />
        <path d="M12 39h29" />
      </svg>
    );
  }
  if (categoryKey === "meadow") {
    return (
      <svg viewBox="0 0 48 48" className="destination-icon plain" aria-hidden="true">
        <circle cx="34" cy="12" r="5" />
        <path d="M5 35c6-9 10-10 15-2 4-6 8-7 13 1 4-5 7-4 10 1M5 41h38" />
      </svg>
    );
  }
  if (categoryKey === "forest") {
    return (
      <svg viewBox="0 0 48 48" className="destination-icon forest" aria-hidden="true">
        <path d="M12 38V24M12 12 5 25h5L4 34h16l-6-9h5L12 12ZM34 39V27M34 17l-7 12h5l-6 8h16l-6-8h5l-7-12Z" />
        <path d="M7 41h34" />
      </svg>
    );
  }
  if (categoryKey === "desert") {
    return (
      <svg viewBox="0 0 48 48" className="destination-icon desert" aria-hidden="true">
        <circle cx="35" cy="12" r="5" />
        <path d="M4 34c9-8 15-8 23-2 7 5 12 5 17 1M4 40c10-5 17-3 24 1 6 3 10 2 16-1" />
      </svg>
    );
  }
  if (categoryKey === "lake") {
    return (
      <svg viewBox="0 0 48 48" className="destination-icon sea" aria-hidden="true">
        <path d="M5 20c5-5 9-5 14 0s9 5 14 0 9-5 10 0M5 29c5-5 9-5 14 0s9 5 14 0 9-5 10 0M5 38c5-5 9-5 14 0s9 5 14 0 9-5 10 0" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 48 48" className="destination-icon peak" aria-hidden="true">
      <path d="M5 36 19 16l7 10 4-6 13 16" />
      <path d="m13 36 6-9 5 6 5-7 9 10" />
      <path d="M19 16l3 4" />
    </svg>
  );
}
