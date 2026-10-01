export function normalizeSearchText(value: string) {
  return value
    .normalize("NFKC")
    .replace(/[يى]/g, "ی")
    .replace(/ك/g, "ک")
    .replace(/[\u200c\u200d]/g, " ")
    .replace(/[ًٌٍَُِّْ]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .toLocaleLowerCase("fa");
}
/** Preserve original letters while highlighting normalized Persian matches. */
export function searchMatchRange(
  text: string,
  query: string,
): [number, number] | null {
  const wanted = normalizeSearchText(query);
  if (!wanted) return null;
  const normalized = normalizeSearchText(text);
  const position = normalized.indexOf(wanted);
  if (position < 0) return null;
  // Names are short: map normalized prefix lengths back to original UTF-16.
  let start = 0,
    end = text.length;
  for (let i = 0; i <= text.length; i++) {
    const length = normalizeSearchText(text.slice(0, i)).length;
    if (length <= position) start = i;
    if (length >= position + wanted.length) {
      end = i;
      break;
    }
  }
  return [start, end];
}
