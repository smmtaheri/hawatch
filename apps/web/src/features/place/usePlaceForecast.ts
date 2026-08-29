import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import { asPeriodId, buildForecastParams } from "../../lib/periods";
import type { PeriodId, PlaceForecastResponse } from "../../types";
import {
  adaptPlaceForecast,
  buildCanonicalRedirectTarget,
  shouldRedirectPointToDestination,
  type PlaceForecastViewModel,
  type PlaceKind,
} from "./placeForecastAdapter";

type LoadStatus = "loading" | "ready" | "error" | "missing";

export function usePlaceForecast(options: { kind: PlaceKind; slug: string }) {
  const { kind, slug } = options;
  const [searchParams, setSearchParams] = useSearchParams();
  const [date, setDate] = useState<string | undefined>(() => searchParams.get("date") || undefined);
  const [period, setPeriod] = useState<PeriodId | undefined>(() => asPeriodId(searchParams.get("period")));
  /** Once the user picks day/period, URL + API params stay in sync (clean URLs stay clean until then). */
  const [selectionCommitted, setSelectionCommitted] = useState(
    () => Boolean(searchParams.get("date") || searchParams.get("period")),
  );
  const [data, setData] = useState<PlaceForecastViewModel | null>(null);
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [canonicalRedirect, setCanonicalRedirect] = useState<string | null>(null);
  const requestId = useRef(0);
  const resolvedDefaultRequestKey = useRef<string | null>(null);
  const explicitDate = Boolean(searchParams.get("date"));
  const explicitPeriod = Boolean(searchParams.get("period"));
  const displayPeriod = period ?? (data?.meta.selected_period as PeriodId | undefined) ?? "morning";

  function requestKey(nextDate = date, nextPeriod = period) {
    return JSON.stringify([kind, slug, nextDate ?? "", nextPeriod ?? ""]);
  }

  function writeQuery(next: Record<string, string | undefined>) {
    const copy = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(next)) {
      if (value) copy.set(key, value);
      else copy.delete(key);
    }
    setSearchParams(copy, { replace: true });
  }

  function selectDate(next: string) {
    setSelectionCommitted(true);
    setDate(next);
    const nextPeriod = period ?? (data?.meta.selected_period as PeriodId | undefined);
    writeQuery({ date: next, period: nextPeriod });
  }

  function selectPeriod(next: PeriodId) {
    setSelectionCommitted(true);
    setPeriod(next);
    const nextDate = date ?? data?.meta.selected_date;
    writeQuery({ date: nextDate, period: next });
  }

  function load() {
    const currentRequest = ++requestId.current;
    setStatus("loading");
    const requestParams = buildForecastParams({
      date,
      period,
      includeDate: explicitDate || selectionCommitted,
      includePeriod: explicitPeriod || selectionCommitted,
    });
    const request =
      kind === "destination"
        ? api.destinationForecast(slug, requestParams)
        : api.pointForecast(slug, requestParams);

    request
      .then((payload: PlaceForecastResponse) => {
        if (currentRequest !== requestId.current) return;
        if (kind === "point") {
          const redirectPath = shouldRedirectPointToDestination(payload);
          if (redirectPath) {
            setCanonicalRedirect(buildCanonicalRedirectTarget(redirectPath, searchParams));
            setStatus("ready");
            return;
          }
        }
        const view = adaptPlaceForecast(payload);
        setData(view);
        if (!date || !period) {
          const resolvedDate = date ?? view.meta.selected_date;
          const resolvedPeriod = period ?? asPeriodId(String(view.meta.selected_period));
          if (resolvedPeriod) {
            resolvedDefaultRequestKey.current = requestKey(resolvedDate, resolvedPeriod);
            if (!date) setDate(resolvedDate);
            if (!period) setPeriod(resolvedPeriod);
          }
        }
        setStatus("ready");
      })
      .catch((error) => {
        if (currentRequest !== requestId.current) return;
        setStatus(error instanceof ApiError && error.status === 404 ? "missing" : "error");
      });
  }

  useEffect(() => {
    if (resolvedDefaultRequestKey.current === requestKey()) {
      resolvedDefaultRequestKey.current = null;
      return;
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind, slug, date, period, selectionCommitted]);

  return {
    date,
    period,
    displayPeriod,
    data,
    status,
    canonicalRedirect,
    selected: date ?? data?.meta.selected_date ?? "",
    selectDate,
    selectPeriod,
    reload: load,
  };
}
