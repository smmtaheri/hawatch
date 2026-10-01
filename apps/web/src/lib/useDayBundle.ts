import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuthChangeVersion } from "../features/auth/authSession";
import type { PointDayBundle, RouteDayBundle } from "../types";
import {
  dayCacheKey,
  expireDayCache,
  fetchDayCache,
  readDayCache,
} from "./dayCache";

export function useDayBundle<T extends PointDayBundle | RouteDayBundle>(
  kind: "point" | "route",
  slug: string,
) {
  const [params, setParams] = useSearchParams();
  const date = params.get("date") || undefined;
  const authVersion = useAuthChangeVersion();
  const [retry, setRetry] = useState(0);
  const key = dayCacheKey(kind, slug, date);
  const [result, setResult] = useState<{
    key: string;
    data: T | null;
    context: T | null;
    status: "loading" | "ready" | "error" | "missing";
  }>({ key: "", data: null, context: null, status: "loading" });
  const cached = readDayCache<T>(key);
  const data = cached ?? (result.key === key ? result.data : null);
  const status = cached
    ? "ready"
    : result.key === key
      ? result.status
      : "loading";

  useEffect(() => {
    let active = true;
    let succeeded = Boolean(readDayCache<T>(key));
    const reload = () => {
      expireDayCache(key);
      setRetry((value) => value + 1);
    };
    setResult((current) => {
      const stored = readDayCache<T>(key);
      const previous = current.key === key ? current.data : null;
      const sameSubject =
        current.key &&
        JSON.stringify(JSON.parse(current.key).slice(0, 3)) ===
          JSON.stringify(JSON.parse(key).slice(0, 3));
      return {
        key,
        data: stored ?? previous,
        context:
          stored ?? (sameSubject ? (current.data ?? current.context) : null),
        status: stored || previous ? "ready" : "loading",
      };
    });
    const query = Object.fromEntries(params) as Record<string, string>;
    const load = () =>
      (kind === "point"
        ? api.pointDay(slug, query)
        : api.routeDay(slug, query)) as Promise<T>;
    void fetchDayCache<T>(key, load, kind, slug)
      .then((payload) => {
        succeeded = true;
        if (active)
          setResult({ key, data: payload, context: payload, status: "ready" });
      })
      .catch((error) => {
        if (!active) return;
        if (
          error instanceof ApiError &&
          error.status === 403 &&
          ["login_required", "plan_required"].includes(error.code || "")
        ) {
          const next = new URLSearchParams(params);
          for (const name of ["date", "period", "start_time"])
            next.delete(name);
          setParams(next, { replace: true });
        } else if (
          error instanceof ApiError &&
          error.status === 400 &&
          query.start_time
        ) {
          const next = new URLSearchParams(params);
          next.delete("start_time");
          setParams(next, { replace: true });
          reload();
        } else
          setResult({
            key,
            data: null,
            context: null,
            status:
              error instanceof ApiError && error.status === 404
                ? "missing"
                : "error",
          });
      });
    const interval = window.setInterval(() => {
      if (succeeded && !readDayCache(key)) reload();
    }, 30000);
    const onFocus = () => {
      if (succeeded && !readDayCache(key)) reload();
    };
    window.addEventListener("focus", onFocus);
    return () => {
      active = false;
      window.clearInterval(interval);
      window.removeEventListener("focus", onFocus);
    };
    // Only date/identity, entitlement and expiry trigger a weather request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, kind, slug, date, authVersion, retry]);

  // Retain identity and selectors across days, only within the same account
  // epoch and subject. Callers never render previous-day weather from context.
  const previousIdentity = result.key
    ? JSON.parse(result.key).slice(0, 3)
    : null;
  const currentIdentity = JSON.parse(key).slice(0, 3);
  const context =
    data ??
    (JSON.stringify(previousIdentity) === JSON.stringify(currentIdentity)
      ? (result.data ?? result.context)
      : null);
  return {
    data,
    context,
    status,
    reload: () => {
      expireDayCache(key);
      setRetry((value) => value + 1);
    },
  };
}
