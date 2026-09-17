const MOUNTAIN_CATEGORY_KEYS = new Set(["mountain", "ridge", "highland", "highlands"]);
const BEACH_CATEGORY_KEYS = new Set(["beach", "coast"]);
const PLACE_TYPE_CATEGORY_KEYS: Record<string, string> = {
  summit: "mountain",
  ridge: "ridge",
  volcano: "volcano",
  waterfall: "waterfall",
  lake: "lake",
  meadow: "meadow",
  forest: "forest",
  desert: "desert",
  beach: "beach",
};

export function resolvePointCategoryKey(categoryKey: string, placeType?: string) {
  const explicit = String(categoryKey ?? "").trim().toLowerCase();
  if (explicit) return explicit;
  return PLACE_TYPE_CATEGORY_KEYS[String(placeType ?? "").trim().toLowerCase()] || "";
}

export function PointIcon({ categoryKey, placeType }: { categoryKey: string; placeType?: string }) {
  const key = resolvePointCategoryKey(categoryKey, placeType);

  // Ridges and highlands belong to the mountain family visually. Keeping the
  // alias here lets the catalog retain its more precise semantic type without
  // falling back to the generic nature icon.
  if (MOUNTAIN_CATEGORY_KEYS.has(key)) {
    return (
      <svg viewBox="0 0 48 48" className="point-icon mountain" aria-hidden="true">
        <path d="M5 36 19 16l7 10 4-6 13 16" />
        <path d="m13 36 6-9 5 6 5-7 9 10" />
        <path d="M19 16l3 4" />
      </svg>
    );
  }
  if (key === "volcano") {
    return (
      <svg viewBox="0 0 48 48" className="point-icon volcano" aria-hidden="true">
        <path d="M5 39 16 20l7 5 5-10 15 24" />
        <path d="M24 15c-2-4 2-5 0-9M29 13c3-3 1-6 4-8" />
        <path d="M12 39h29" />
      </svg>
    );
  }
  if (key === "meadow") {
    return (
      <svg viewBox="0 0 48 48" className="point-icon meadow plain" aria-hidden="true">
        <path d="M5 29c7-7 13-8 20-3 5 4 10 5 18 0" />
        <path d="M5 40h38" />
        <path d="M12 36c0-3 2-5 4-7M16 37c1-3 3-5 5-6M36 37c0-3-2-5-4-7M32 37c-1-3-3-5-5-6" />
      </svg>
    );
  }
  if (key === "forest") {
    return (
      <svg viewBox="0 0 48 48" className="point-icon forest" aria-hidden="true">
        <path d="M12 38V24M12 12 5 25h5L4 34h16l-6-9h5L12 12ZM34 39V27M34 17l-7 12h5l-6 8h16l-6-8h5l-7-12Z" />
        <path d="M7 41h34" />
      </svg>
    );
  }
  if (key === "desert") {
    return (
      <svg viewBox="0 0 48 48" className="point-icon desert" aria-hidden="true">
        <circle cx="35" cy="12" r="5" />
        <path d="M4 34c9-8 15-8 23-2 7 5 12 5 17 1M4 40c10-5 17-3 24 1 6 3 10 2 16-1" />
      </svg>
    );
  }
  if (key === "lake") {
    return (
      <svg viewBox="0 0 48 48" className="point-icon lake sea" aria-hidden="true">
        <path d="M5 20c5-5 9-5 14 0s9 5 14 0 9-5 10 0M5 29c5-5 9-5 14 0s9 5 14 0 9-5 10 0M5 38c5-5 9-5 14 0s9 5 14 0 9-5 10 0" />
      </svg>
    );
  }
  if (key === "waterfall") {
    return (
      <svg viewBox="0 0 48 48" className="point-icon waterfall" aria-hidden="true">
        <path d="M6 13c7 5 12 5 18 0 5-4 10-4 18 1" />
        <path d="M14 17v13M21 17v16M29 16v14M36 18v10" />
        <path d="M8 36c5-3 9-3 14 0s9 3 14 0 5-3 7-1M5 41h38" />
      </svg>
    );
  }
  if (BEACH_CATEGORY_KEYS.has(key)) {
    return (
      <svg viewBox="0 0 48 48" className="point-icon beach" aria-hidden="true">
        <path d="M5 19c7-1 11 2 13 8 2 6 7 10 14 11 5 1 8 2 11 4" />
        <path d="M24 16c5-3 10-3 17 0M26 23c5-2 10-2 16 0" />
        <path d="M5 41h38" />
      </svg>
    );
  }
  // Unknown keys must not silently claim that a place is a mountain. The
  // database remains free to use new semantic keys, while an unsupported key
  // gets a neutral nature mark until its visual is intentionally introduced.
  return (
    <svg viewBox="0 0 48 48" className="point-icon nature" aria-hidden="true">
      <circle cx="34" cy="12" r="5" />
      <path d="M5 36c7-8 12-8 18-2 5 5 10 5 20-2M5 41h38" />
    </svg>
  );
}
