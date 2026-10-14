export function normalizeSearchText(value: string) {
  return value
    .normalize("NFKD")
    .replace(/[يى]/g, "ی")
    .replace(/ك/g, "ک")
    .replace(/[ۀةە]/g, "ه")
    .replace(/[\u200c\u200d]/g, " ")
    .replace(/[\p{M}\p{Cf}ـ]/gu, "")
    .replace(/[۰-۹٠-٩]/g, (digit) => String(digit.charCodeAt(0) - (digit >= "۰" ? 0x6f0 : 0x660)))
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase()
    .replace(/(^| )(\S*ه) ی(?= |$)/g, "$1$2");
}

export function compactSearchText(value: string) {
  return normalizeSearchText(value).replace(/ /g, "");
}

export function prepareSearchTerms(values: string[], cache?: Map<string, string>): string[] {
  return [...new Set(values.map((value) => {
    const existing = cache?.get(value);
    if (existing !== undefined) return existing;
    const normalized = compactSearchText(value);
    cache?.set(value, normalized);
    return normalized;
  }).filter(Boolean))];
}

export function parseSearchQuery(value: string) {
  const words = normalizeSearchText(value);
  return { compact: words.replace(/ /g, ""), tokens: [...new Set(words.split(" ").filter(Boolean))] };
}

export function searchTermScore(terms: string[], query: ReturnType<typeof parseSearchQuery>): [number, number] | null {
  if (!query.compact) return null;
  let best: [number, number] | null = null;
  for (let index = 0; index < terms.length; index++) {
    const term = terms[index];
    const position = term === query.compact ? 0 : term.startsWith(query.compact) ? 1 : term.includes(query.compact) ? 2 : -1;
    if (position >= 0 && (!best || position < best[0])) {
      best = [position, index];
      if (position === 0) return best;
    }
  }
  if (best) return best;
  return query.tokens.length > 1 && query.tokens.every((token) => terms.some((term) => term.includes(token))) ? [3, 0] : null;
}
/** Preserve original letters while highlighting normalized Persian matches. */
export function searchMatchRange(
  text: string,
  query: string,
): [number, number] | null {
  const wanted = compactSearchText(query);
  if (!wanted) return null;
  const normalized = compactSearchText(text);
  const position = normalized.indexOf(wanted);
  if (position < 0) return null;
  // Names are short: map normalized prefix lengths back to original UTF-16.
  let start = 0,
    end = text.length;
  for (let i = 0; i <= text.length; i++) {
    const length = compactSearchText(text.slice(0, i)).length;
    if (length <= position) start = i;
    if (length >= position + wanted.length) {
      end = i;
      break;
    }
  }
  return [start, end];
}
