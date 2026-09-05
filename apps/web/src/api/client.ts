import type {
  ApiMeta,
  PlaceForecastResponse,
  PointSummary,
  PointForecast,
  RouteForecast,
  RouteSummary,
  SearchSuggestion,
} from "../types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/+$/, "");

export function apiUrl(path: string) {
  const base = API_BASE.startsWith("/")
    ? `${window.location.origin}${API_BASE}/`
    : `${API_BASE}/`;
  return new URL(path.replace(/^\/+/, ""), base);
}

function randomToken(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
}

const ANALYTICS_VISITOR_KEY = "hawatch.analytics.visitor";

function visitorToken(): string {
  try {
    const existing = window.localStorage.getItem(ANALYTICS_VISITOR_KEY);
    if (existing && /^[A-Za-z0-9_-]{16,128}$/.test(existing)) return existing;
    const token = randomToken();
    window.localStorage.setItem(ANALYTICS_VISITOR_KEY, token);
    return token;
  } catch {
    // Private browsing or blocked storage: this navigation remains anonymous.
    return randomToken();
  }
}

/** Fire-and-forget first-party page-view tracking; failures never affect UI. */
export function trackPageView(pageType: "point" | "route", slug: string, navigationId = randomToken()): void {
  void fetch(apiUrl("analytics/pageview/").toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ page_type: pageType, slug, visitor_id: visitorToken(), navigation_id: navigationId }),
    keepalive: true,
  }).catch(() => undefined);
}

export class ApiError extends Error {
  status: number;
  code?: string;
  payload?: unknown;
  constructor(message: string, status: number, code?: string, payload?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.payload = payload;
  }
}

async function getJson<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const url = apiUrl(path);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value) url.searchParams.set(key, value);
    }
  }
  const response = await fetch(url.toString(), { credentials: "same-origin" });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string; code?: string } | null;
    throw new ApiError(payload?.detail || "بارگذاری داده ناموفق بود.", response.status, payload?.code, payload);
  }
  return (await response.json()) as T;
}

export const api = {
  points: (query?: string) =>
    getJson<{ results: PointSummary[]; empty: boolean; query: string; meta: ApiMeta }>("points/", {
      query,
    }),
  routeForecast: (
    slug: string,
    params: { date?: string; period?: string; start_time?: string; speed?: string },
  ) => getJson<RouteForecast>(`routes/${slug}/forecast/`, params),
  pointForecast: (slug: string, params: { date?: string; period?: string }) =>
    getJson<PointForecast & PlaceForecastResponse>(`points/${slug}/forecast/`, params),
  searchSuggestions: (query: string, signal?: AbortSignal) => {
    const url = apiUrl("search/suggestions/");
    url.searchParams.set("q", query);
    return fetch(url.toString(), { signal }).then(async (response) => {
      if (!response.ok) {
        throw new ApiError("جست‌وجو ناموفق بود.", response.status);
      }
      return (await response.json()) as {
        query: string;
        results: SearchSuggestion[];
        empty: boolean;
        meta: ApiMeta;
      };
    });
  },
};

export { API_BASE };
