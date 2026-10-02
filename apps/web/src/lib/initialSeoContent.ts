// Capture only the server-rendered article, before createRoot replaces it.
// It is trusted, escaped Django HTML, never API/user-supplied markup.
let initial: { pathname: string; search: string; article: string } | null = null;

export function captureInitialSeoContent() {
  const article = document.querySelector('[data-seo-initial="true"] > article');
  initial = article
    ? { pathname: window.location.pathname, search: window.location.search, article: article.outerHTML }
    : null;
}

export function initialSeoContentFor(pathname: string, search: string): string | null {
  return initial?.pathname === pathname && initial.search === search ? initial.article : null;
}
