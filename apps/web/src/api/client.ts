import type { DestinationForecast, DestinationSummary, RouteForecast } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function getJson<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const url = new URL(path.replace(/^\//, ""), API_BASE.endsWith("/") ? API_BASE : `${API_BASE}/`);
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
    getJson<{ results: DestinationSummary[]; empty: boolean; query: string; meta: { freshness: string } }>(
      "destinations/",
      { query },
    ),
  destination: (slug: string) =>
    getJson<{ destination: DestinationSummary & { routes: unknown[] } }>(`destinations/${slug}/`),
  destinationForecast: (slug: string, params: { date?: string; period?: string }) =>
    getJson<DestinationForecast>(`destinations/${slug}/forecast/`, params),
  routeForecast: (
    slug: string,
    params: { date?: string; period?: string; start_time?: string; speed?: string },
  ) => getJson<RouteForecast>(`routes/${slug}/forecast/`, params),
};

export { API_BASE };
