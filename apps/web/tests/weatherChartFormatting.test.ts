import { expect, it } from "vitest";
import { charts } from "../src/features/week/vendor/charts";

it("rounds temperature and wind labels to whole values, with half values away from zero", () => {
  const temperature = charts.temperature(
    [
      { felt: -2.5 },
      { felt: 2.5 },
      { felt: 2.3 },
      { felt: -0.3 },
    ],
    [30, 20, 10, 0],
    40,
  );
  expect(temperature).toContain(">−۳</text>");
  expect(temperature).toContain(">+۳</text>");
  expect(temperature).toContain(">+۲</text>");
  expect(temperature).not.toContain("−۰</text>");

  const wind = charts.stems([{ wind: 2.5 }], [20], 40, "wind", 10);
  expect(wind).toContain(">۳</text>");
  expect(wind).not.toContain("۲٫۵");
});

it("keeps one decimal only for positive rainfall below one millimeter", () => {
  const rain = charts.rain(
    [{ rain: 0 }, { rain: 0.4 }, { rain: 1.4 }, { rain: 1.5 }],
    [30, 20, 10, 0],
    40,
  );
  expect(rain).toContain(">۰</text>");
  expect(rain).toContain(">۰٫۴</text>");
  expect(rain).toContain(">۱</text>");
  expect(rain).toContain(">۲</text>");
  expect(rain).not.toContain("۱٫۴");
});
