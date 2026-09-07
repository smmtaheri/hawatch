import { useLayoutEffect } from "react";
import { useLocation } from "react-router-dom";

export const DEFAULT_TITLE = "هواچ | هوای نقطه، برنامهٔ مسیر";
export const DEFAULT_DESCRIPTION = "هواچ؛ هوای نقاط و برنامهٔ مسیر.";
const INITIAL_DOCUMENT_LOCATION =
  typeof window === "undefined" ? "" : `${window.location.pathname}${window.location.search}`;

type PageTitleOptions = {
  robots?: "index,follow" | "noindex,follow";
  canonical?: boolean;
  title?: string;
  description?: string;
};

export function canonicalPageUrl(origin: string, pathname: string) {
  return `${origin}${pathname}`;
}

export function robotsForSearch(search: string) {
  return search ? "noindex,follow" : "index,follow";
}

/** Keep the browser tab tied to the place or route currently being viewed. */
export function usePageTitle(name?: string, options: PageTitleOptions = {}) {
  const location = useLocation();
  useLayoutEffect(() => {
    const title = options.title || (name ? `هوای ${name} | هواچ` : DEFAULT_TITLE);
    document.title = title;
    let link = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
    if (options.canonical === false) {
      link?.remove();
    } else {
      if (!link) {
        link = document.createElement("link");
        link.rel = "canonical";
        document.head.appendChild(link);
      }
      const cleanPath = location.pathname === "/" ? "/" : location.pathname.replace(/\/+$/, "");
      link.href = canonicalPageUrl(window.location.origin, cleanPath);
    }
    let description = document.head.querySelector<HTMLMetaElement>('meta[name="description"]');
    if (!description) {
      description = document.createElement("meta");
      description.name = "description";
      document.head.appendChild(description);
    }
    description.content = options.description || (name ? `پیش‌بینی هوا و وضعیت مسیر برای ${name} در هواچ.` : DEFAULT_DESCRIPTION);
    let robots = document.head.querySelector<HTMLMetaElement>('meta[name="robots"]');
    if (!robots) {
      robots = document.createElement("meta");
      robots.name = "robots";
      document.head.appendChild(robots);
    }
    // Keep an SSR noindex decision while the page data is loading. This avoids
    // briefly turning an active but non-indexable point into an indexable page
    // during hydration; explicit page/query policies still take precedence.
    const serverRobots = robots.content;
    const isInitialNonIndexableDocument =
      `${location.pathname}${location.search}` === INITIAL_DOCUMENT_LOCATION &&
      !location.search &&
      serverRobots === "noindex,follow";
    robots.content =
      options.robots ??
      (isInitialNonIndexableDocument ? serverRobots : robotsForSearch(location.search));
  }, [location.pathname, location.search, name, options.canonical, options.description, options.robots, options.title]);
}
