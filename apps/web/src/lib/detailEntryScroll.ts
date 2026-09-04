/**
 * Put a detail page at the beginning of its place/route identity header.
 *
 * The public header is already at the top of a fresh document, so scrolling
 * it into view is a no-op. The identity hero is the useful entry point: it
 * makes the point/route title visible after opening a deep link or
 * switching to another route. Use both the document scroll and the native
 * document scroll position and the native element API so this also works when
 * the app is embedded in a scrollable shell instead of being the document's
 * direct scroller.
 */
export function scrollToDetailHero(selector: string) {
  const target = document.querySelector<HTMLElement>(selector);
  if (!target) return;

  const top = Math.max(0, target.getBoundingClientRect().top + window.scrollY);
  if (document.scrollingElement) document.scrollingElement.scrollTop = top;
  target.scrollIntoView?.({ block: "start", behavior: "auto" });
}
