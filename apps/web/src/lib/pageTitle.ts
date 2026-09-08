import { useLayoutEffect, useRef } from "react";
import { useLocation } from "react-router-dom";

export const DEFAULT_TITLE = "هواچ | هوای نقطه، برنامهٔ مسیر";
export const DEFAULT_DESCRIPTION = "هواچ؛ هوای نقاط و برنامهٔ مسیر.";
// The API sends a semantic SSR document for public detail pages. Capture this
// before React replaces #root so the first loading effect can leave that
// document head untouched. A static SPA shell has no marker and therefore
// still receives the normal client-side fallback metadata.
const HAS_INITIAL_SEMANTIC_HTML =
  typeof document !== "undefined" && Boolean(document.querySelector('[data-seo-initial="true"]'));
let initialSsrMetadataHandled = false;

function hasInitialSemanticMetadata() {
  if (HAS_INITIAL_SEMANTIC_HTML) return true;
  if (typeof document === "undefined") return false;
  // Keep this fallback useful for a server that omits the body marker while
  // still distinguishing the generic Vite shell (whose title is the default).
  return Boolean(document.title && document.title !== DEFAULT_TITLE && document.head.querySelector('meta[name="description"]'));
}

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

function setNamedMeta(name: string, content: string) {
  let meta = document.head.querySelector<HTMLMetaElement>(`meta[name="${name}"]`);
  if (!meta) {
    meta = document.createElement("meta");
    meta.name = name;
    document.head.appendChild(meta);
  }
  meta.content = content;
}

function setPropertyMeta(property: string, content: string) {
  let meta = document.head.querySelector<HTMLMetaElement>(`meta[property="${property}"]`);
  if (!meta) {
    meta = document.createElement("meta");
    meta.setAttribute("property", property);
    document.head.appendChild(meta);
  }
  meta.content = content;
}

/** Keep the browser tab tied to the place or route currently being viewed. */
export function usePageTitle(name?: string, options: PageTitleOptions = {}) {
  const location = useLocation();
  const initialLocationRef = useRef(`${location.pathname}${location.search}`);
  const preserveSsrWhileLoadingRef = useRef<boolean | null>(null);
  useLayoutEffect(() => {
    const hasExplicitMetadata = Boolean(
      name || options.title || options.description || options.robots || options.canonical === false,
    );
    if (preserveSsrWhileLoadingRef.current === null) {
      preserveSsrWhileLoadingRef.current =
        !hasExplicitMetadata &&
        hasInitialSemanticMetadata() &&
        !initialSsrMetadataHandled &&
        `${location.pathname}${location.search}` === initialLocationRef.current;
      if (preserveSsrWhileLoadingRef.current) initialSsrMetadataHandled = true;
    }
    const isInitialDocument =
      preserveSsrWhileLoadingRef.current &&
      !hasExplicitMetadata &&
      `${location.pathname}${location.search}` === initialLocationRef.current;

    // During the first data request for an SSR detail page, preserving the
    // server-rendered head avoids replacing its correct title/description with
    // the generic application fallback. Once data arrives, the explicit
    // metadata below runs; SPA navigations do not qualify and clear the old
    // page metadata immediately while the new page loads.
    if (!hasExplicitMetadata && isInitialDocument) {
      return;
    }
    initialSsrMetadataHandled = true;

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
    const description = options.description || (name ? `پیش‌بینی هوا و وضعیت مسیر برای ${name} در هواچ.` : DEFAULT_DESCRIPTION);
    setNamedMeta("description", description);
    setPropertyMeta("og:title", title);
    setPropertyMeta("og:description", description);
    if (options.canonical === false) {
      document.head.querySelector('meta[property="og:url"]')?.remove();
    } else {
      setPropertyMeta("og:url", canonicalPageUrl(window.location.origin, location.pathname.replace(/\/+$/, "") || "/"));
    }
    const robots = document.head.querySelector<HTMLMetaElement>('meta[name="robots"]') ?? document.createElement("meta");
    if (!robots.parentElement) {
      robots.name = "robots";
      document.head.appendChild(robots);
    }
    // The loading branch above preserves an SSR noindex decision. Once data is
    // ready, explicit point policy wins; query variants remain noindex while
    // retaining their clean canonical links.
    robots.content = options.robots ?? robotsForSearch(location.search);
  }, [location.pathname, location.search, name, options.canonical, options.description, options.robots, options.title]);
}
