import { useLayoutEffect } from "react";

const DEFAULT_TITLE = "هواچ | هوای نقطه، برنامهٔ مسیر";

type PageTitleOptions = {
  robots?: "index,follow" | "noindex,follow";
  canonical?: boolean;
};

/** Keep the browser tab tied to the place or route currently being viewed. */
export function usePageTitle(name?: string, options: PageTitleOptions = {}) {
  useLayoutEffect(() => {
    const title = name ? `هوای ${name} | هواچ` : DEFAULT_TITLE;
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
      link.href = `${window.location.origin}${window.location.pathname}`;
    }
    let description = document.head.querySelector<HTMLMetaElement>('meta[name="description"]');
    if (!description) {
      description = document.createElement("meta");
      description.name = "description";
      document.head.appendChild(description);
    }
    description.content = name ? `پیش‌بینی هوا و وضعیت مسیر برای ${name} در هواچ.` : "هواچ؛ هوای نقاط و برنامهٔ مسیر.";
    let robots = document.head.querySelector<HTMLMetaElement>('meta[name="robots"]');
    if (!robots) {
      robots = document.createElement("meta");
      robots.name = "robots";
      document.head.appendChild(robots);
    }
    robots.content = options.robots ?? (window.location.search ? "noindex,follow" : "index,follow");
  }, [name, options.canonical, options.robots]);
}
