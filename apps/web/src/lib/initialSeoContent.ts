// Capture only the server-rendered article, before createRoot replaces it.
// It is trusted, escaped Django HTML, never API/user-supplied markup.
let initial: { pathname: string; search: string; article: string } | null = null;
export interface InitialHomeData {
  popular_points: Array<{
    slug: string;
    tile_name: string;
    name: string;
    short_category: string;
    category: string;
    category_key: string;
    place_type: string;
    region: string;
    elevation_m: number | null;
    elevation_label: string;
    image: string;
    image_alt: string;
    href: string;
    is_popular: boolean;
    seo_indexable: boolean;
  }>;
  catalog_counts: { points: number; routes: number };
  freshness: string;
}
let homeData: InitialHomeData | null = null;

export function captureInitialSeoContent() {
  const article = document.querySelector('[data-seo-initial="true"] > article');
  initial = article
    ? { pathname: window.location.pathname, search: window.location.search, article: article.outerHTML }
    : null;
  const serializedHomeData = document.getElementById("home-initial-data")?.textContent;
  try {
    homeData = serializedHomeData ? JSON.parse(serializedHomeData) as InitialHomeData : null;
  } catch {
    homeData = null;
  }
}

export function initialSeoContentFor(pathname: string, search: string): string | null {
  return initial?.pathname === pathname && initial.search === search ? initial.article : null;
}

export function initialHomeDataFor(): InitialHomeData | null {
  return homeData;
}
