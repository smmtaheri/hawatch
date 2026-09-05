import { describe, expect, it } from "vitest";
import { normalizeIranPhone } from "../src/features/auth/authSession";

describe("login phone normalization", () => {
  it("normalizes the allowed Iranian number in common input forms", () => {
    expect(normalizeIranPhone("+98 912 345 6789")).toBe("989123456789");
    expect(normalizeIranPhone("۰۹۱۲۳۴۵۶۷۸۹")).toBe("989123456789");
    expect(normalizeIranPhone("9123456789")).toBe("989123456789");
  });
});
