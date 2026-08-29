import type {
  ApiMeta,
  DestinationForecast,
  DestinationSummary,
  PlaceForecastResponse,
  PointForecast,
  RouteForecast,
  RoutePointForecast,
  RouteSummary,
  SearchSuggestion,
} from "../types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/+$/, "");

function apiUrl(path: string) {
  const base = API_BASE.startsWith("/")
    ? `${window.location.origin}${API_BASE}/`
    : `${API_BASE}/`;
  return new URL(path.replace(/^\/+/, ""), base);
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function getJson<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const url = apiUrl(path);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value) url.searchParams.set(key, value);
    }
  }
  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new ApiError("بارگذاری داده ناموفق بود.", response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  destinations: (query?: string) =>
    getJson<{ results: DestinationSummary[]; empty: boolean; query: string; meta: ApiMeta }>("destinations/", {
      query,
    }),
  destination: (slug: string) =>
    getJson<{ destination: DestinationSummary & { routes: RouteSummary[] }; meta: ApiMeta }>(`destinations/${slug}/`),
  destinationForecast: (slug: string, params: { date?: string; period?: string }) =>
    getJson<DestinationForecast & PlaceForecastResponse>(`destinations/${slug}/forecast/`, params),
  routeForecast: (
    slug: string,
    params: { date?: string; period?: string; start_time?: string; speed?: string },
  ) => getJson<RouteForecast>(`routes/${slug}/forecast/`, params),
  routePointForecast: (
    routeSlug: string,
    pointSlug: string,
    params: { date?: string; period?: string },
  ) => getJson<RoutePointForecast>(`routes/${routeSlug}/points/${pointSlug}/forecast/`, params),
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
