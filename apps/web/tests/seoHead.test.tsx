import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { canonicalPageUrl, robotsForSearch, usePageTitle } from "../src/lib/pageTitle";

function SeoHarness() {
  usePageTitle(undefined, {
    title: "آب‌وهوای دریاچهٔ آزمایشی؛ دما، باد و بارش | هواچ",
    description: "توضیح یکتای مبتنی بر دادهٔ واقعی.",
  });
  return null;
}

function LoadingSeoHarness({ ready = false }: { ready?: boolean }) {
  usePageTitle(
    undefined,
    ready
      ? {
          title: "آب‌وهوای قلهٔ توچال؛ دما، باد و بارش | هواچ",
          description: "پیش‌بینی آب‌وهوای قلهٔ توچال در ارتفاع ۳۹۵۵ متر در تهران؛ دما، باد، تندباد، بارش، برف و وضعیت ساعتی.",
        }
      : {},
  );
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

  it("preserves semantic SSR metadata while loading, then applies page data", () => {
    document.title = "آب‌وهوای قلهٔ توچال؛ دما، باد و بارش | هواچ";
    const description = document.head.querySelector('meta[name="description"]') ?? document.createElement("meta");
    description.setAttribute("name", "description");
    description.content = "توضیح SSR قلهٔ توچال.";
    document.head.appendChild(description);

    const view = render(
      <MemoryRouter initialEntries={["/points/tochal"]}>
        <LoadingSeoHarness />
      </MemoryRouter>,
    );
    expect(document.title).toBe("آب‌وهوای قلهٔ توچال؛ دما، باد و بارش | هواچ");
    expect(description).toHaveAttribute("content", "توضیح SSR قلهٔ توچال.");

    view.rerender(
      <MemoryRouter initialEntries={["/points/tochal"]}>
        <LoadingSeoHarness ready />
      </MemoryRouter>,
    );
    expect(document.title).toBe("آب‌وهوای قلهٔ توچال؛ دما، باد و بارش | هواچ");
    expect(description).toHaveAttribute(
      "content",
      "پیش‌بینی آب‌وهوای قلهٔ توچال در ارتفاع ۳۹۵۵ متر در تهران؛ دما، باد، تندباد، بارش، برف و وضعیت ساعتی.",
    );
  });

  it("clears the previous page metadata during SPA navigation before new data arrives", () => {
    const previous = render(
      <MemoryRouter initialEntries={["/points/old"]}>
        <SeoHarness />
      </MemoryRouter>,
    );
    previous.unmount();

    render(
      <MemoryRouter initialEntries={["/points/new"]}>
        <LoadingSeoHarness />
      </MemoryRouter>,
    );
    expect(document.title).toBe("هواچ | هوای نقطه، برنامهٔ مسیر");
    expect(document.head.querySelector('meta[name="description"]')).toHaveAttribute(
      "content",
      "هواچ؛ هوای نقاط و برنامهٔ مسیر.",
    );
    expect(document.head.querySelector('link[rel="canonical"]')).toHaveAttribute(
      "href",
      `${window.location.origin}/points/new`,
    );
    expect(document.head.querySelector('meta[name="robots"]')).toHaveAttribute("content", "index,follow");
  });

  it("keeps the data-derived title and description after SPA hydration", () => {
    render(<MemoryRouter initialEntries={["/points/seo-test-lake"]}><SeoHarness /></MemoryRouter>);
    expect(document.title).toBe("آب‌وهوای دریاچهٔ آزمایشی؛ دما، باد و بارش | هواچ");
    expect(document.head.querySelector('meta[name="description"]')?.getAttribute("content")).toBe("توضیح یکتای مبتنی بر دادهٔ واقعی.");
  });
});
