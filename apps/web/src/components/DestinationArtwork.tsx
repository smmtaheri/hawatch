const ILLUSTRATED_CATEGORIES = new Set([
  "waterfall",
  "desert",
  "meadow",
  "beach",
  "city",
  "village",
  "neighborhood",
  "ski",
]);

function normalizedCategoryKey(categoryKey: string) {
  return String(categoryKey ?? "").trim().toLowerCase();
}

export function hasDestinationArtwork(categoryKey: string) {
  return ILLUSTRATED_CATEGORIES.has(normalizedCategoryKey(categoryKey));
}

/**
 * Approved, text-free artwork for the categories that need a distinct scene.
 * The parent `DestinationIcon` owns the common frame; this component only
 * chooses the unchanged artwork asset inside that frame.
 */
export function DestinationArtwork({ categoryKey }: { categoryKey: string }) {
  const key = normalizedCategoryKey(categoryKey);
  if (!hasDestinationArtwork(key)) return null;

  return <span className={`destination-artwork ${key}`} aria-hidden="true" />;
}
