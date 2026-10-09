import type { CatalogSearchIndex, SearchSuggestion } from "../types";

function normalizeCatalogTerm(value: string): string {
  return value
    .trim()
    .replace(/[يى]/g, "ی")
    .replace(/ك/g, "ک")
    .replace(/\u200c/g, "")
    .replace(/\s+/g, "")
    .toLocaleLowerCase("fa");
}

/** Filter the CDN-cached catalog locally while preserving server result order. */
export function searchCatalogIndex(index: CatalogSearchIndex, rawQuery: string): SearchSuggestion[] {
  const query = normalizeCatalogTerm(rawQuery);
  if (query.length < 2) return [];

  const points = index.points
    .map((point) => {
      let best: { position: number; rank: number; match_kind: "name" | "alias" } | null = null;
      for (const [termIndex, term] of point.terms.entries()) {
        const normalized = normalizeCatalogTerm(term);
        if (!normalized) continue;
        const position = normalized === query ? 0 : normalized.startsWith(query) ? 1 : normalized.includes(query) ? 2 : -1;
        if (position < 0) continue;
        const match = {
          position,
          rank: termIndex === 0 || point.primary ? 0 : 1,
          match_kind: termIndex === 0 ? "name" as const : "alias" as const,
        };
        if (!best || match.position < best.position || (match.position === best.position && match.rank < best.rank)) {
          best = match;
        }
      }
      return best ? {
        result: {
          type: "point" as const,
          slug: point.slug,
          label: point.label,
          hint: point.hint,
          href: point.href,
          match_kind: best.match_kind,
          category_key: point.category_key,
          place_type: point.place_type,
        },
        position: best.position,
        rank: best.rank,
      } : null;
    })
    .filter((item): item is NonNullable<typeof item> => item !== null)
    .sort((left, right) => left.position - right.position || left.rank - right.rank ||
      left.result.label.localeCompare(right.result.label, "fa") || left.result.slug.localeCompare(right.result.slug))
    .slice(0, 8)
    .map((item) => item.result);

  const routes = index.routes
    .filter((route) => route.terms.some((term) => normalizeCatalogTerm(term).includes(query)))
    .slice(0, 8)
    .map((route): SearchSuggestion => ({
      type: "route",
      slug: route.slug,
      label: route.label,
      hint: route.hint,
      href: route.href,
      match_kind: "name",
    }));

  return [...points, ...routes];
}
