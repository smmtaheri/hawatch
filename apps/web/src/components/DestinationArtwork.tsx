const ILLUSTRATED_CATEGORIES = new Set(["waterfall", "desert", "meadow", "beach"]);

function normalizedCategoryKey(categoryKey: string) {
  return String(categoryKey ?? "").trim().toLowerCase();
}

export function hasDestinationArtwork(categoryKey: string) {
  return ILLUSTRATED_CATEGORIES.has(normalizedCategoryKey(categoryKey));
}

/**
 * Small, text-free destination scenes. The source PNGs are used only as
 * alpha masks, so their illustration inherits the active Hawatch teal token
 * instead of introducing a second colour system in light or dark theme.
 */
export function DestinationArtwork({ categoryKey }: { categoryKey: string }) {
  const key = normalizedCategoryKey(categoryKey);
  if (!hasDestinationArtwork(key)) return null;

  return <span className={`destination-artwork ${key}`} aria-hidden="true" />;
}
