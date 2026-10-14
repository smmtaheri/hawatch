import type { CatalogSearchIndex, SearchSuggestion } from "../types";
import { parseSearchQuery, prepareSearchTerms, searchTermScore } from "./searchText";

type SearchRow = { result: SearchSuggestion; terms: string[]; primary: boolean };
const preparedIndexes = new WeakMap<CatalogSearchIndex, { points: SearchRow[]; routes: SearchRow[] }>();
const collator = new Intl.Collator("fa");

function preparedIndex(index: CatalogSearchIndex) {
  let prepared = preparedIndexes.get(index);
  if (prepared) return prepared;
  // A waypoint can occur in many routes; normalize shared names only once.
  const terms = new Map<string, string>();
  prepared = {
    points: index.points.map((point): SearchRow => ({
      result: {
        type: "point", slug: point.slug, label: point.label, hint: point.hint,
        href: point.href, match_kind: "name", category_key: point.category_key, place_type: point.place_type,
      },
      terms: prepareSearchTerms(point.terms, terms),
      primary: point.primary,
    })),
    routes: index.routes.map((route): SearchRow => ({
      result: { type: "route", slug: route.slug, label: route.label, hint: route.hint, href: route.href, match_kind: "name" },
      terms: prepareSearchTerms(route.terms, terms),
      primary: false,
    })),
  };
  preparedIndexes.set(index, prepared);
  return prepared;
}

/** Normalize each catalog once; keystrokes only normalize the query. */
export function searchCatalogIndex(index: CatalogSearchIndex, rawQuery: string): SearchSuggestion[] {
  const query = parseSearchQuery(rawQuery);
  if (query.compact.length < 2 || query.compact.length > 160) return [];
  const prepared = preparedIndex(index);
  function matches(rows: SearchRow[]) {
    return rows.flatMap((row) => {
      const score = searchTermScore(row.terms, query);
      return score ? [{ row, score }] : [];
    }).sort((left, right) => left.score[0] - right.score[0] || Number(right.row.primary) - Number(left.row.primary) ||
      collator.compare(left.row.result.label, right.row.result.label) || collator.compare(left.row.result.slug, right.row.result.slug))
      .slice(0, 8)
      .map(({ row, score }): SearchSuggestion => ({ ...row.result, match_kind: score[1] === 0 ? "name" : "alias" }));
  }
  return [...matches(prepared.points), ...matches(prepared.routes)];
}
