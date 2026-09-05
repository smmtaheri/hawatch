import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  AUTH_SESSION_DURATION_MS,
  AUTH_SESSION_KEY,
  DEMO_LOGIN_PHONE,
  isDemoPhone,
  loginDemoSession,
  normalizeIranPhone,
} from "../src/features/auth/authSession";

describe("demo login session", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.useRealTimers();
  });

  it("normalizes the allowed Iranian number in common input forms", () => {
    expect(normalizeIranPhone("+98 938 675 9479")).toBe(DEMO_LOGIN_PHONE);
    expect(normalizeIranPhone("۰۹۳۸۶۷۵۹۴۷۹")).toBe(DEMO_LOGIN_PHONE);
    expect(isDemoPhone("9386759479")).toBe(true);
    expect(isDemoPhone("989121234567")).toBe(false);
  });

  it("stores an expiring first-party session", () => {
    vi.useFakeTimers();
    const now = new Date("2026-09-05T12:00:00Z");
    vi.setSystemTime(now);
    loginDemoSession();
    const stored = JSON.parse(window.localStorage.getItem(AUTH_SESSION_KEY) || "null");
    expect(stored.phone).toBe(DEMO_LOGIN_PHONE);
    expect(stored.expiresAt).toBe(now.getTime() + AUTH_SESSION_DURATION_MS);
  });
});
