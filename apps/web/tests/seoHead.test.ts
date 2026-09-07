import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { canonicalPageUrl, robotsForSearch, usePageTitle } from "../src/lib/pageTitle";

function SeoHarness() {
  usePageTitle(undefined, {
    title: "پیش‌بینی آب‌وهوای دریاچهٔ آزمایشی | هواچ",
    description: "توضیح یکتای مبتنی بر دادهٔ واقعی.",
  });
  return null;
}

describe("SEO document helpers", () => {
  it("keeps canonical URLs free of planner query parameters", () => {
    expect(canonicalPageUrl("https://hawatch.ir", "/routes/tochal-darband")).toBe(
      "https://hawatch.ir/routes/tochal-darband",
    );
  });

  it("marks URL variants with a query as noindex while preserving links", () => {
    expect(robotsForSearch("?date=2026-09-04&period=morning")).toBe("noindex,follow");
    expect(robotsForSearch("")).toBe("index,follow");
  });

  it("keeps the data-derived title and description after SPA hydration", () => {
    render(<MemoryRouter initialEntries={["/points/seo-test-lake"]}><SeoHarness /></MemoryRouter>);
    expect(document.title).toBe("پیش‌بینی آب‌وهوای دریاچهٔ آزمایشی | هواچ");
    expect(document.head.querySelector('meta[name="description"]')?.getAttribute("content")).toBe("توضیح یکتای مبتنی بر دادهٔ واقعی.");
  });
});
