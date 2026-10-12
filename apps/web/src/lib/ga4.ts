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

type PageView = {
  path: string;
  title: string;
  generation: number;
};

/**
 * Coordinates React Router and the asynchronously-updated document title.
 * A route transition is counted once only after that route's title is ready.
 */
export function createPageViewCoordinator(send: (page: PageView) => void) {
  let activePath: string | null = null;
  let titleReadyPath: string | null = null;
  let titleReady = "";
  let generation = 0;
  let sentGeneration = -1;

  function flush() {
    if (!activePath || titleReadyPath !== activePath || sentGeneration === generation) return;
    sentGeneration = generation;
    send({ path: activePath, title: titleReady, generation });
  }

  return {
    navigate(pathname: string) {
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
let previousPublicLocation = "";

function safeLocation(path: string): string {
  return `${window.location.origin}${path}`;
}

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
    const pageLocation = safeLocation(page.path);
    const pageReferrer = previousPublicLocation;
    // Keep Google tag's defaults aligned to the clean route before the manual
    // event. This prevents query strings (planner/auth state) and the external
    // document.referrer from being inferred by the tag.
    window.gtag("config", id, {
      send_page_view: false,
      page_location: pageLocation,
      page_referrer: pageReferrer,
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
    });
    window.gtag("event", "page_view", {
      page_title: page.title,
      page_location: pageLocation,
      page_referrer: pageReferrer,
    });
    previousPublicLocation = pageLocation;
  } catch {
    // Analytics is optional; never let a third-party integration affect UI.
  }
}

const pageViewCoordinator = createPageViewCoordinator(sendPageView);

export function initializeGa4(): void {
  const id = measurementId();
  if (!ga4Enabled(id) || configuredMeasurementId === id || window.__hawatchGa4State) return;

  try {
    configuredMeasurementId = id;
    window.dataLayer = window.dataLayer ?? [];
    window.gtag = queueGtag;
    window.gtag("js", new Date());
    window.gtag("config", id, {
      send_page_view: false,
      page_location: safeLocation(publicAnalyticsPath(window.location.pathname) ?? "/"),
      page_referrer: "",
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
    });

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

export function notifyGa4Navigation(pathname: string): void {
  if (!ga4Enabled()) return;
  pageViewCoordinator.navigate(pathname);
}

export function notifyGa4TitleReady(pathname: string, title: string): void {
  if (!ga4Enabled()) return;
  pageViewCoordinator.titleReady(pathname, sanitizeAnalyticsTitle(title));
}
