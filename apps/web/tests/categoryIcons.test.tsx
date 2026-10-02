import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CategoryIcon, resolveCategoryIcon } from "../src/components/DesignIcon";
import icons from "../src/components/designIcons.json";

const categoryNames = Object.keys(icons)
  .filter((key) => key.startsWith("category-"))
  .map((key) => key.slice("category-".length));

describe("shared destination icon resolution", () => {
  it.each(categoryNames)("uses the packaged %s artwork even with a landmark type", (name) => {
    expect(resolveCategoryIcon(name, "landmark")).toBe(name);
    const { container } = render(<CategoryIcon category={name} placeType="landmark" />);
    const expected = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    expected.innerHTML = icons[`category-${name}` as keyof typeof icons];
    const svg = container.querySelector(".category-icon")!;
    expect(svg.innerHTML).toBe(expected.innerHTML);
    expect(svg.getAttribute("viewBox")).toBe("0 0 32 32");
    expect(svg.getAttribute("stroke")).toBe("currentColor");
  });

  it.each([
    ["ski_resort", "landmark", "ski"],
    ["ridge", "ridge", "mountain"],
    ["ridge", "summit", "mountain"],
    ["mountain", "shelter", "shelter"],
    ["mountain", "pass", "pass"],
    ["mountain", "trailhead", "trailhead"],
    ["landmark", "village", "village"],
    ["volcano", "summit", "volcano"],
    ["marsh", "lake", "marsh"],
    ["dam", "lake", "dam"],
    ["hot_spring", "spring", "hot_spring"],
    ["meadow", "meadow", "plain"],
    ["beach", "beach", "coast"],
    ["unknown-category", "summit", "mountain"],
    ["unknown-category", "unknown-type", "landmark"],
    ["", "", "landmark"],
    [" CAVE ", " LANDMARK ", "cave"],
  ])("resolves category %s and type %s to %s", (category, placeType, expected) => {
    expect(resolveCategoryIcon(category, placeType)).toBe(expected);
  });
});

const expectedCategories: Record<string, string> = {
  "avisho-cave": "cave", "bornik-cave": "cave", "gol-zard-cave": "cave",
  "rudafshan-cave": "cave", "yakh-morad-cave": "cave",
  "kafar-keli-cave": "cave",
  "shirabad-div-sepid-cave": "cave", "dorfak-east-ghar-yakhi": "cave",
  "hasal-marsh": "marsh", "qaleh-roudkhan": "fort", "malek-bahman-castle": "fort",
  "veresk-bridge": "bridge", "vardij-ghost-stones": "rocks",
  "golabdarreh-park": "park", "tochal-jamshidieh-park": "park",
  "berenjestanak-dam": "dam", "lafour-dam": "dam", "amir-kabir-dam": "dam",
  "bijar-dam": "dam", "lar-dam": "dam", "namrud-dam": "dam", "sefidrud-reservoir": "dam",
  "abgarm-larijan": "hot_spring", "flakdeh-hot-spring": "hot_spring",
  "sehezar-hot-spring": "hot_spring", "sabalan-qotur-sui": "hot_spring",
  "badab-surt": "terrace", "shahdad-kaluts": "kalut", "kal-jeni": "gorge", "almeh-valley": "valley",
  "abali-ski-resort": "ski", "darbandsar-ski-resort": "ski", "dizin-ski-resort": "ski",
  "sabalan-alvares-ski-resort": "ski", "tochal-ski-resort": "ski",
};

describe("catalog categories reach the shared renderer without a generic fallback", () => {
  const catalogs = Object.values(import.meta.glob<{
    weather_points: Record<string, { category_key?: string; place_type?: string }>;
    point?: { slug: string; category_key?: string };
  }>("../../api/fixtures/catalog/*.json", { eager: true, import: "default" }));

  it.each(Object.entries(expectedCategories))("keeps %s in the %s visual family", (slug, category) => {
    const owners = catalogs.filter((catalog) => catalog.weather_points?.[slug]);
    expect(owners).toHaveLength(1);
    const owner = owners[0];
    const point = owner.weather_points[slug];
    expect(point.category_key).toBe(category);
    expect(resolveCategoryIcon(point.category_key, point.place_type)).toBe(category);
    if (owner.point?.slug === slug) expect(owner.point.category_key).toBe(category);
  });
});
