import { DestinationIcon } from "./PointIcon";

const ILLUSTRATED_CATEGORIES = new Set(["waterfall", "desert", "meadow", "beach"]);

function normalizedCategoryKey(categoryKey: string) {
  return String(categoryKey ?? "").trim().toLowerCase();
}

export function hasDestinationArtwork(categoryKey: string) {
  return ILLUSTRATED_CATEGORIES.has(normalizedCategoryKey(categoryKey));
}

/**
 * Backward-compatible facade for callers that still use the old name. The
 * glyph now goes through the same SVG renderer as every other destination
 * surface, so it cannot reintroduce the raster artwork's different weight or
 * dimensions.
 */
export function DestinationArtwork({ categoryKey, placeType }: { categoryKey: string; placeType?: string }) {
  if (!hasDestinationArtwork(categoryKey)) return null;
  return <DestinationIcon className="destination-card-icon" categoryKey={categoryKey} placeType={placeType} />;
}
