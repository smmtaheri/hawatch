/** Passive attribution: no URL/history writes, rendering state, polling or DOM scans. */
import { trackPageView } from "../api/client";
import { analyticsPageLocation, publicAnalyticsPath, sanitizeAnalyticsReferrer } from "./ga4";

const STORAGE_KEY = "hawatch.analytics.session.v1";
const SESSION_IDLE_MS = 30 * 60 * 1000;
const enabled = () => import.meta.env.VITE_ANALYTICS_ATTRIBUTION_ENABLED !== "false";
const token = () => typeof crypto.randomUUID === "function" ? crypto.randomUUID() : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-anonymous`;
type Session = { id: string; last: number; context: Record<string, string> };
let initial: { path: string; search: string; referrer: string } | undefined;
let pendingSearch: { path: string; at: number } | undefined;

export function initializeInternalAnalytics() {
  initial = { path: window.location.pathname, search: window.location.search, referrer: document.referrer };
}

/** Used by both keyboard and normal search-link selection. Never prevents a click. */
export function markSearchNavigation(href: string) {
  try {
    const url = new URL(href, window.location.origin);
    if (url.origin === window.location.origin && publicAnalyticsPath(url.pathname)) {
      pendingSearch = { path: url.pathname, at: Date.now() };
    }
  } catch { /* Attribution is optional. */ }
}

export function createInternalNavigationTracker(
  send = trackPageView,
  first = initial ?? { path: window.location.pathname, search: window.location.search, referrer: document.referrer },
) {
  let previous: string | null = null;
  let memory: Session | undefined;
  let sentEntrySession = "";
  function visit(pathname: string, navigationType = "PUSH") {
    try {
      const path = publicAnalyticsPath(pathname);
      if (pathname === previous) return; // StrictMode effects and planner query changes.
      const oldPath = previous;
      previous = pathname; // Includes home/hubs, fixing point→home→same-point suppression.
      const match = path?.match(/^\/(points|routes)\/([a-z0-9-]+)$/);
      if (!path) return;
      if (!enabled()) {
        if (match) send(match[1] === "points" ? "point" : "route", match[2], token());
        return;
      }
      const now = Date.now();
      try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (raw) {
          const parsed = JSON.parse(raw) as Session;
          if (typeof parsed.id === "string" && /^[A-Za-z0-9_-]{16,128}$/.test(parsed.id) && Number.isFinite(parsed.last) && parsed.context && typeof parsed.context === "object") memory = parsed;
        }
      } catch { /* Memory fallback preserves navigation if storage is unavailable. */ }
      const fresh = !memory || now - memory.last >= SESSION_IDLE_MS || memory.last > now;
      if (fresh) {
        const landingSearch = oldPath === null && path === first.path ? first.search : "";
        const landing = new URL(analyticsPageLocation(window.location.origin, path, landingSearch));
        const context: Record<string, string> = { landing_path: path };
        const ref = oldPath === null ? sanitizeAnalyticsReferrer(first.referrer, window.location.origin) : "";
        if (ref) context.referrer = ref;
        for (const key of ["utm_source", "utm_medium", "utm_campaign"]) {
          const value = landing.searchParams.get(key);
          if (value) context[key] = value.slice(0, 48);
        }
        memory = { id: token(), last: now, context };
      }
      memory!.last = now;
      try { window.localStorage.setItem(STORAGE_KEY, JSON.stringify(memory)); } catch { /* Best effort. */ }
      let previousPath = oldPath ? publicAnalyticsPath(oldPath) ?? "" : "";
      if (!oldPath && first.referrer) {
        try {
          const ref = new URL(first.referrer);
          if (ref.origin === window.location.origin) previousPath = publicAnalyticsPath(ref.pathname) ?? "";
        } catch { /* Unknown referrer. */ }
      }
      let navigation = oldPath === null ? "entry" : navigationType === "POP" ? "history" : previousPath === "/" ? "home" : previousPath.startsWith("/points/") ? "point" : /^\/routes\/[a-z]/.test(previousPath) ? "route" : previousPath.startsWith("/destinations") ? "destinations" : previousPath.startsWith("/routes") ? "routes" : "internal";
      if (oldPath !== null && navigationType !== "POP" && pendingSearch?.path === path && now-pendingSearch.at < 5000) navigation = "site_search";
      pendingSearch = undefined;
      const context = { ...memory!.context, session_id: memory!.id, previous_path: previousPath, navigation_source: navigation };
      if (match) {
        send(match[1] === "points" ? "point" : "route", match[2], token(), context);
        sentEntrySession = memory!.id;
      } else if (sentEntrySession !== memory!.id) {
        send("entry", "landing", token(), context);
        sentEntrySession = memory!.id;
      }
    } catch {
      // Attribution must never break navigation, including malformed stored JSON.
      const match = pathname.match(/^\/(points|routes)\/([a-z0-9-]+)\/?$/);
      if (match) send(match[1] === "points" ? "point" : "route", match[2]);
    }
  }
  return { visit };
}
