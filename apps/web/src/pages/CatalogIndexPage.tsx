import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Header } from "../components/Header";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { usePageTitle } from "../lib/pageTitle";
import type { PointSummary } from "../types";

const pointTypeLabels: Record<string, string> = {
  summit: "قله‌ها",
  lake: "دریاچه‌ها",
  waterfall: "آبشارها",
  forest: "جنگل‌ها",
  desert: "کویرها",
  village: "روستاها",
  shelter: "پناهگاه‌ها",
  pass: "گردنه‌ها",
  spring: "چشمه‌ها",
  meadow: "دشت‌ها",
  ridge: "یال‌ها",
};

type CatalogData = {
  points: PointSummary[];
  routes: Array<{ title: string; origin: string; target_label: string; href: string; region: string }>;
};
type CatalogItem = PointSummary | CatalogData["routes"][number];

export function CatalogIndexPage({ kind }: { kind: "points" | "routes" }) {
  usePageTitle(undefined, {
    title: kind === "points" ? "همهٔ نقاط هواچ | پیش‌بینی آب‌وهوا" : "همهٔ مسیرهای هواچ | پیش‌بینی آب‌وهوا",
    description: kind === "points" ? "فهرست نقاط عمومی هواچ برای مشاهدهٔ پیش‌بینی آب‌وهوا و مسیرهای مرتبط." : "فهرست مسیرهای پیاده‌روی عمومی هواچ با پیوند به نقاط و پیش‌بینی مسیر.",
  });
  const [data, setData] = useState<CatalogData | null>(null);
  const [error, setError] = useState(false);

  const load = () => {
    setError(false);
    api.catalogIndex().then(setData).catch(() => setError(true));
  };

  useEffect(load, []);
  const items: CatalogItem[] = kind === "points" ? data?.points ?? [] : data?.routes ?? [];
  const grouped = new Map<string, CatalogItem[]>();
  for (const item of items) {
    const key = kind === "points"
      ? pointTypeLabels[(item as PointSummary).place_type ?? ""] ?? "سایر نقاط"
      : (item as CatalogData["routes"][number]).region || "سایر مناطق";
    grouped.set(key, [...(grouped.get(key) ?? []), item]);
  }

  return (
    <main className="catalog-index-page">
      <div className="point-shell">
        <Header />
        <section className="catalog-index-heading">
          <p className="eyebrow">فهرست هواچ</p>
          <h1>{kind === "points" ? "نقاط هواچ" : "مسیرهای هواچ"}</h1>
          <p>{kind === "points" ? "نقطهٔ موردنظرت را بر اساس نوع عارضه پیدا کن." : "مسیرهای عمومی را بر اساس منطقه مرور کن."}</p>
        </section>
        {!data && !error ? <LoadingState label="در حال بارگذاری فهرست…" /> : null}
        {error ? <ErrorState onRetry={load} /> : null}
        {data ? (
          <div className="catalog-index-groups">
            {[...grouped.entries()].map(([label, group]) => (
              <section className="catalog-index-group card-surface" key={label}>
                <h2>{label}</h2>
                <ul>
                  {group.map((item) => {
                    const isPoint = kind === "points";
                    const point = item as PointSummary;
                    const route = item as CatalogData["routes"][number];
                    return (
                      <li key={item.href}>
                        <Link to={item.href}>{isPoint ? point.name : route.title}</Link>
                        <small>{isPoint ? point.region : `از ${route.origin} تا ${route.target_label}`}</small>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ))}
          </div>
        ) : null}
      </div>
    </main>
  );
}
