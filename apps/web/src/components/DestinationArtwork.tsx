const ILLUSTRATED_CATEGORIES = new Set(["waterfall", "desert", "meadow", "beach"]);

function normalizedCategoryKey(categoryKey: string) {
  return String(categoryKey ?? "").trim().toLowerCase();
}

export function hasDestinationArtwork(categoryKey: string) {
  return ILLUSTRATED_CATEGORIES.has(normalizedCategoryKey(categoryKey));
}

/**
 * Category artwork based on the approved destination references.  It stays
 * inline (rather than as a raster screenshot) so the same artwork can use
 * Hawatch's light/dark surface tokens without changing the catalog contract.
 */
export function DestinationArtwork({ categoryKey }: { categoryKey: string }) {
  const key = normalizedCategoryKey(categoryKey);

  if (key === "waterfall") {
    return (
      <svg viewBox="0 0 88 104" className="destination-artwork waterfall" aria-hidden="true" focusable="false">
        <rect className="destination-artwork-surface" x="1" y="1" width="86" height="102" rx="15" />
        <rect className="destination-artwork-frame" x="13" y="10" width="62" height="63" rx="15" />
        <path className="destination-artwork-line" d="M13 39c10 7 18 7 27 0 8-6 17-6 35 1" />
        <path className="destination-artwork-line" d="M25 42v18M35 42v21M45 41v19M56 43v16" />
        <path className="destination-artwork-line" d="M16 65c7-4 13-4 20 0s13 4 20 0 8-4 12-1M13 71h62" />
        <text className="destination-artwork-label" x="44" y="91" textAnchor="middle">آبشار</text>
      </svg>
    );
  }

  if (key === "desert") {
    return (
      <svg viewBox="0 0 88 104" className="destination-artwork desert" aria-hidden="true" focusable="false">
        <rect className="destination-artwork-surface" x="1" y="1" width="86" height="102" rx="15" />
        <rect className="destination-artwork-frame" x="13" y="10" width="62" height="63" rx="15" />
        <circle className="destination-artwork-line" cx="61" cy="23" r="6" />
        <path className="destination-artwork-line" d="M13 42c11-9 18-11 27-4 8 6 15 11 23 8 4-2 8-5 12-3" />
        <path className="destination-artwork-line" d="M13 58c11-6 20-5 29 0 8 5 17 7 33 0M13 68c12-5 21-3 30 1 9 4 17 3 32-2" />
        <text className="destination-artwork-label" x="44" y="91" textAnchor="middle">کویر</text>
      </svg>
    );
  }

  if (key === "meadow") {
    return (
      <svg viewBox="0 0 88 104" className="destination-artwork meadow" aria-hidden="true" focusable="false">
        <rect className="destination-artwork-surface" x="1" y="1" width="86" height="102" rx="15" />
        <rect className="destination-artwork-frame" x="13" y="10" width="62" height="63" rx="15" />
        <path className="destination-artwork-line" d="M13 45c10-6 17-7 26-3 8 4 17 6 36 0" />
        <path className="destination-artwork-line" d="M13 70h62M24 66c0-5 2-8 5-11M31 68c1-5 3-8 6-10M61 68c0-5-2-8-5-11M55 68c-1-5-3-8-6-10" />
        <text className="destination-artwork-label" x="44" y="91" textAnchor="middle">دشت</text>
      </svg>
    );
  }

  if (key === "beach") {
    return (
      <svg viewBox="0 0 88 104" className="destination-artwork beach" aria-hidden="true" focusable="false">
        <rect className="destination-artwork-surface" x="1" y="1" width="86" height="102" rx="15" />
        <rect className="destination-artwork-frame" x="13" y="10" width="62" height="63" rx="15" />
        <path className="destination-artwork-line" d="M13 39c9-1 14 2 17 9 3 8 8 13 17 15 7 1 12 2 15 5" />
        <path className="destination-artwork-line" d="M43 28c7-4 14-4 25 0M46 37c8-3 15-3 25 0M13 71h62" />
        <text className="destination-artwork-label" x="44" y="91" textAnchor="middle">ساحل</text>
      </svg>
    );
  }

  return null;
}
