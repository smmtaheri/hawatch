import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { asPeriodId } from "../../lib/periods";
import { useDayBundle } from "../../lib/useDayBundle";
import type { PeriodId, PointDayBundle } from "../../types";
import { adaptPlaceForecast, type PlaceKind } from "./placeForecastAdapter";

export function usePlaceForecast({ slug }: { kind: PlaceKind; slug: string }) {
  const [params, setParams] = useSearchParams();
  const {
    data: bundle,
    context,
    status,
    reload,
  } = useDayBundle<PointDayBundle>("point", slug);
  const displayPeriod =
    asPeriodId(params.get("period")) ??
    asPeriodId((bundle ?? context)?.forecast.meta.selected_period) ??
    "morning";
  const selected =
    params.get("date") ??
    (bundle ?? context)?.forecast.meta.selected_date ??
    "";
  const data = useMemo(() => {
    if (!bundle) return null;
    const selection = bundle.periods[displayPeriod];
    return adaptPlaceForecast({
      ...bundle,
      ...selection,
      forecast: {
        ...bundle.forecast,
        ...selection,
        meta: { ...bundle.forecast.meta, selected_period: displayPeriod },
      },
    });
  }, [bundle, displayPeriod]);
  function update(date: string, period: PeriodId) {
    const next = new URLSearchParams(params);
    next.set("date", date);
    next.set("period", period);
    setParams(next, { replace: true });
  }
  return {
    data,
    frame: data ?? (context ? adaptPlaceForecast(context) : null),
    bundle,
    status,
    displayPeriod,
    selected,
    reload,
    selectDate: (date: string) => update(date, displayPeriod),
    selectPeriod: (period: PeriodId) => update(selected, period),
  };
}
