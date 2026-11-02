type Gtag = (...args: unknown[]) => void;

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: Gtag;
    __hawatchGa4State?: "loading" | "failed";
  }
}

const MEASUREMENT_ID_META = 'meta[name="hawatch-ga4-measurement-id"]';
const MEASUREMENT_ID_PATTERN = /^G-[A-Z0-9]{6,}$/;
const PAGE_PATHS = [
  /^\/$/,
  /^\/destinations(?:\/page\/[1-9][0-9]*)?\/?$/,
  /^\/routes(?:\/page\/[1-9][0-9]*)?\/?$/,
  /^\/account\/plans\/?$/,
  /^\/points\/[a-z0-9-]+\/?$/,
  /^\/routes\/[a-z0-9-]+\/?$/,
];
const CAMPAIGN_PARAMETERS = [
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_id",
  "utm_term",
  "utm_content",
  "utm_source_platform",
  "utm_creative_format",
  "utm_marketing_tactic",
];

export function publicAnalyticsPath(pathname: string): string | null {
  if (!PAGE_PATHS.some((pattern) => pattern.test(pathname))) return null;
  return pathname === "/" ? "/" : pathname.replace(/\/+$/, "");
}

export function shouldEnableGa4(options: {
  measurementId: string;
  hostname: string;
  protocol: string;
  port: string;
  production: boolean;
  qaPreview: boolean;
}): boolean {
  return (
    options.production &&
    !options.qaPreview &&
    options.protocol === "https:" &&
    (options.port === "" || options.port === "443") &&
    ["hawatch.ir", "www.hawatch.ir"].includes(options.hostname.toLowerCase()) &&
    MEASUREMENT_ID_PATTERN.test(options.measurementId.trim())
  );
}

export function sanitizeAnalyticsTitle(title: string): string {
  return title
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "")
    .replace(/(?:\+?[0-9۰-۹][0-9۰-۹\s().-]{7,}[0-9۰-۹])/gu, "")
    .replace(/\b(?:token|access_token|refresh_token|password|email|phone)\s*[:=]\s*[^\s|]+/gi, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 200);
}

export type PageView = {
  path: string;
  title: string;
  generation: number;
  pageLocation: string;
  pageReferrer: string;
};

export type InitialPageContext = {
  path: string | null;
  pageLocation: string;
  pageReferrer: string;
};

function campaignValue(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed || trimmed.length > 100 || /[\u0000-\u001f\u007f]/.test(trimmed)) return null;
  // Campaign tags are operator-supplied labels, not a channel for personal or
  // credential data. If the existing title scrubber would alter a value, drop
  // it instead of sending a partially-redacted campaign label.
  const safe = sanitizeAnalyticsTitle(trimmed);
  return safe === trimmed ? safe : null;
}

/** Keep only standard campaign tags on the initial public page URL. */
export function analyticsPageLocation(origin: string, pathname: string, search = ""): string {
  const path = publicAnalyticsPath(pathname);
  if (!path) return new URL("/", origin).toString();
  const url = new URL(path, origin);
  const query = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  for (const key of CAMPAIGN_PARAMETERS) {
    const value = campaignValue(query.getAll(key)[0] ?? "");
    if (value) url.searchParams.set(key, value);
  }
  return url.toString();
}

/** Keep an external referral source at origin granularity to avoid leaking URL data. */
export function sanitizeAnalyticsReferrer(referrer: string, siteOrigin: string): string {
  try {
    const source = new URL(referrer);
    const site = new URL(siteOrigin);
    if (!["http:", "https:"].includes(source.protocol) || source.username || source.password) return "";
    if (source.origin === site.origin) {
      const path = publicAnalyticsPath(source.pathname);
      return path ? `${site.origin}${path}` : "";
    }
    return `${source.origin}/`;
  } catch {
    return "";
  }
}

export function createInitialPageContext(
  origin: string,
  pathname: string,
  search: string,
  documentReferrer: string,
): InitialPageContext {
  const path = publicAnalyticsPath(pathname);
  return {
    path,
    pageLocation: analyticsPageLocation(origin, path ?? "/", path ? search : ""),
    pageReferrer: path ? sanitizeAnalyticsReferrer(documentReferrer, origin) : "",
  };
}

export function ga4ConfigOptions(pageLocation: string, pageReferrer: string) {
  return {
    send_page_view: false,
    page_location: pageLocation,
    page_referrer: pageReferrer,
    allow_google_signals: false,
    allow_ad_personalization_signals: false,
  };
}

/** The same tested command builder is used for initial config and SPA views. */
export function sendGa4PageView(gtag: Gtag, id: string, page: PageView): void {
  gtag("config", id, ga4ConfigOptions(page.pageLocation, page.pageReferrer));
  gtag("event", "page_view", {
    page_title: sanitizeAnalyticsTitle(page.title),
    page_location: page.pageLocation,
    page_referrer: page.pageReferrer,
  });
}

/**
 * Coordinates React Router and the asynchronously-updated document title.
 * A route transition is counted once only after that route's title is ready.
 */
export function createPageViewCoordinator(
  send: (page: PageView) => void,
  options: { origin?: string; initialPage?: InitialPageContext } = {},
) {
  const origin = options.origin ?? "https://hawatch.ir";
  let initialPagePending = Boolean(options.initialPage?.path);
  let activePath: string | null = null;
  let titleReadyPath: string | null = null;
  let titleReady = "";
  let generation = 0;
  let sentGeneration = -1;
  let previousPublicLocation = "";

  function flush() {
    if (!activePath || titleReadyPath !== activePath || sentGeneration === generation) return;
    sentGeneration = generation;
    const isInitialPage = initialPagePending && options.initialPage?.path === activePath;
    const pageLocation = isInitialPage
      ? options.initialPage!.pageLocation
      : analyticsPageLocation(origin, activePath);
    const pageReferrer = isInitialPage
      ? options.initialPage!.pageReferrer
      : previousPublicLocation;
    send({ path: activePath, title: titleReady, generation, pageLocation, pageReferrer });
    initialPagePending = false;
    // Subsequent virtual referrers deliberately omit landing UTMs and planner state.
    previousPublicLocation = `${origin}${activePath}`;
  }

  return {
    navigate(pathname: string, _search = "") {
      const path = publicAnalyticsPath(pathname);
      if (!path) {
        if (activePath !== null) generation += 1;
        activePath = null;
        titleReadyPath = null;
        titleReady = "";
        sentGeneration = -1;
        return;
      }
      if (path === activePath) return;
      generation += 1;
      activePath = path;
      if (titleReadyPath !== path) {
        titleReadyPath = null;
        titleReady = "";
      }
      flush();
    },
    titleReady(pathname: string, title: string) {
      const path = publicAnalyticsPath(pathname);
      const safeTitle = title.trim();
      if (!path || !safeTitle) return;
      titleReadyPath = path;
      titleReady = safeTitle;
      flush();
    },
  };
}

function measurementId(): string {
  return (
    document.querySelector<HTMLMetaElement>(MEASUREMENT_ID_META)?.content.trim() ||
    import.meta.env.VITE_GA4_MEASUREMENT_ID?.trim() ||
    ""
  );
}

function ga4Enabled(id = measurementId()): boolean {
  return typeof window !== "undefined" && typeof document !== "undefined" && shouldEnableGa4({
    measurementId: id,
    hostname: window.location.hostname,
    protocol: window.location.protocol,
    port: window.location.port,
    production: import.meta.env.PROD,
    qaPreview: import.meta.env.VITE_QA_PREVIEW === "true",
  });
}

let configuredMeasurementId: string | null = null;

function queueGtag(..._args: unknown[]) {
  window.dataLayer?.push(arguments);
}

export function handleGa4ScriptFailure(): void {
  try {
    window.__hawatchGa4State = "failed";
    // A blocked request must not leave a queue that grows on later routes.
    window.dataLayer?.splice(0);
    if (window.gtag === queueGtag) delete window.gtag;
  } catch {
    // Failure cleanup is best-effort and must never escape into the app.
  }
}

function sendPageView(page: PageView) {
  const id = configuredMeasurementId;
  if (!id || window.__hawatchGa4State === "failed" || typeof window.gtag !== "function") return;

  try {
    sendGa4PageView(window.gtag, id, page);
  } catch {
    // Analytics is optional; never let a third-party integration affect UI.
  }
}

let pageViewCoordinator = createPageViewCoordinator(sendPageView);

export function initializeGa4(): void {
  const id = measurementId();
  if (!ga4Enabled(id) || configuredMeasurementId === id || window.__hawatchGa4State) return;

  try {
    configuredMeasurementId = id;
    const initialPage = createInitialPageContext(
      window.location.origin,
      window.location.pathname,
      window.location.search,
      document.referrer,
    );
    pageViewCoordinator = createPageViewCoordinator(sendPageView, {
      origin: window.location.origin,
      initialPage,
    });
    window.dataLayer = window.dataLayer ?? [];
    window.gtag = queueGtag;
    window.gtag("js", new Date());
    window.gtag("config", id, ga4ConfigOptions(initialPage.pageLocation, initialPage.pageReferrer));

    const existingScript = document.querySelector<HTMLScriptElement>(
      `script[src^="https://www.googletagmanager.com/gtag/js?id=${id}"]`,
    );
    if (existingScript) {
      window.__hawatchGa4State = "loading";
      return;
    }

    const script = document.createElement("script");
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
    window.__hawatchGa4State = "loading";
    script.onerror = handleGa4ScriptFailure;
    document.head.appendChild(script);
  } catch {
    handleGa4ScriptFailure();
  }
}

export function notifyGa4Navigation(pathname: string, search = ""): void {
  if (!ga4Enabled()) return;
  pageViewCoordinator.navigate(pathname, search);
}

export function notifyGa4TitleReady(pathname: string, title: string): void {
  if (!ga4Enabled()) return;
  pageViewCoordinator.titleReady(pathname, sanitizeAnalyticsTitle(title));
}
