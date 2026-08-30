import { useLayoutEffect } from "react";

const DEFAULT_TITLE = "هواچ | هوای مقصد، برنامهٔ مسیر";

/** Keep the browser tab tied to the place or route currently being viewed. */
export function usePageTitle(name?: string) {
  useLayoutEffect(() => {
    document.title = name ? `هوای ${name} | هواچ` : DEFAULT_TITLE;
  }, [name]);
}
