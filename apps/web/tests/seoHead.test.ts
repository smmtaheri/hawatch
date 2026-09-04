import { describe, expect, it } from "vitest";
import { canonicalPageUrl, robotsForSearch } from "../src/lib/pageTitle";

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
});
