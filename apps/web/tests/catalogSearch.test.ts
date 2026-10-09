import { describe, expect, it } from "vitest";
import { searchCatalogIndex } from "../src/lib/catalogSearch";
import type { CatalogSearchIndex } from "../src/types";

const index: CatalogSearchIndex = {
  revision: "test-revision",
  points: [
    { slug: "tochal", label: "قلهٔ توچال", terms: ["توچال", "قله توچال"], hint: "تهران · ۳۹۶۰ متر", href: "/points/tochal", category_key: "mountain", place_type: "summit", primary: true },
    { slug: "tochal-village", label: "روستای پس‌قلعه", terms: ["پس‌قلعه", "پس قلعه", "پسغلعه"], hint: "تهران", href: "/points/tochal-village", category_key: "village", place_type: "village", primary: false },
  ],
  routes: [
    { slug: "tochal-darband", label: "توچال تا دربند", terms: ["توچال تا دربند", "سربند", "قلهٔ توچال"], hint: "۵ نقطه · ۱۰ کیلومتر", href: "/routes/tochal-darband" },
  ],
};

describe("CDN catalog search", () => {
  it("matches canonical names, aliases, Persian letter variants, and route waypoints locally", () => {
    expect(searchCatalogIndex(index, "توچال").map((item) => item.slug)).toEqual(["tochal", "tochal-darband"]);
    expect(searchCatalogIndex(index, "قله‌ توچال")[0].slug).toBe("tochal");
    expect(searchCatalogIndex(index, "پسغل")[0]).toMatchObject({ slug: "tochal-village", match_kind: "alias" });
  });

  it("keeps the existing two-character minimum", () => {
    expect(searchCatalogIndex(index, "ت")).toEqual([]);
  });
});
