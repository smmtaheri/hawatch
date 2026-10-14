import { describe, expect, it } from "vitest";
import { searchCatalogIndex } from "../src/lib/catalogSearch";
import { compactSearchText, normalizeSearchText, searchMatchRange } from "../src/lib/searchText";
import type { CatalogSearchIndex } from "../src/types";
import normalizationCases from "../../api/fixtures/search-normalization.json";

const index: CatalogSearchIndex = {
  revision: "test-revision",
  points: [
    { slug: "tochal", label: "قلهٔ توچال", terms: ["قلهٔ توچال", "توچال"], hint: "تهران · ۳۹۶۰ متر", href: "/points/tochal", category_key: "mountain", place_type: "summit", primary: true },
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

  it.each(normalizationCases)("shares the API normalization for $normalized", ({ normalized, variants }) => {
    for (const value of variants) {
      expect(normalizeSearchText(value)).toBe(normalized);
      expect(compactSearchText(value)).toBe(normalized.replace(/ /g, ""));
    }
  });

  it("matches actual canonical orthography without hand-written spelling aliases", () => {
    const canonical: CatalogSearchIndex = {
      ...index,
      points: [
        { ...index.points[0], slug: "damavand", terms: ["قلهٔ دماوند"], href: "/points/damavand" },
        { ...index.points[0], slug: "alamkuh", terms: ["قلهٔ علم‌کوه"], href: "/points/alamkuh" },
      ],
    };
    for (const query of normalizationCases[0].variants) {
      expect(searchCatalogIndex(canonical, query).map((row) => row.slug)).toEqual(["damavand"]);
    }
    for (const query of ["علمکوه", "علم کوه", "علم‌کوه", "قله ی علمكوه"]) {
      expect(searchCatalogIndex(canonical, query)[0].slug).toBe("alamkuh");
    }
  });

  it("matches words in either order while rejecting incomplete multiword matches", () => {
    for (const query of ["دربند توچال", "توچال دربند"]) {
      expect(searchCatalogIndex(index, query).map((row) => row.slug)).toEqual(["tochal-darband"]);
    }
    expect(searchCatalogIndex(index, "توچال سبلان")).toEqual([]);
  });

  it("keeps highlight ranges on original letters and Persian digits", () => {
    for (const [text, query, expected] of [
      ["قلهٔ دماوند", "قله ی دماوند", "قلهٔ دماوند"],
      ["قلهٔ علم‌کوه", "علمکوه", "علم‌کوه"],
      ["جان‌پناه ۴۰۰۰ دماوند", "4000", "۴۰۰۰"],
    ]) {
      const range = searchMatchRange(text, query);
      expect(range && text.slice(...range)).toBe(expected);
    }
  });
});
