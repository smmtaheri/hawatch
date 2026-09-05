import { useEffect, useState } from "react";

/** Temporary first-party demo login; replace with the real OTP contract later. */
export const DEMO_LOGIN_PHONE = "989386759479";
export const DEMO_LOGIN_OTP = "1234";
export const AUTH_SESSION_KEY = "hawatch.auth.session";
export const AUTH_SESSION_DURATION_MS = 30 * 24 * 60 * 60 * 1000;

type StoredSession = {
  phone: string;
  expiresAt: number;
};

const AUTH_CHANGED_EVENT = "hawatch-auth-changed";
const MAX_TIMEOUT_MS = 2_147_000_000;

function readSession(): StoredSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(AUTH_SESSION_KEY);
    if (!raw) return null;
    const session = JSON.parse(raw) as Partial<StoredSession>;
    if (session.phone !== DEMO_LOGIN_PHONE || typeof session.expiresAt !== "number" || session.expiresAt <= Date.now()) {
      window.localStorage.removeItem(AUTH_SESSION_KEY);
      return null;
    }
    return { phone: session.phone, expiresAt: session.expiresAt };
  } catch {
    return null;
  }
}

function notifyAuthChanged() {
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

export function normalizeIranPhone(value: string): string {
  const persianDigits = "۰۱۲۳۴۵۶۷۸۹";
  const arabicDigits = "٠١٢٣٤٥٦٧٨٩";
  let digits = value
    .split("")
    .map((character) => {
      const persianIndex = persianDigits.indexOf(character);
      if (persianIndex >= 0) return String(persianIndex);
      const arabicIndex = arabicDigits.indexOf(character);
      return arabicIndex >= 0 ? String(arabicIndex) : character;
    })
    .join("")
    .replace(/\D/g, "");
  if (digits.startsWith("00")) digits = digits.slice(2);
  if (digits.startsWith("0")) digits = `98${digits.slice(1)}`;
  if (digits.length === 10 && digits.startsWith("9")) digits = `98${digits}`;
  return digits;
}

export function isDemoPhone(value: string): boolean {
  return normalizeIranPhone(value) === DEMO_LOGIN_PHONE;
}

export function loginDemoSession(): StoredSession {
  const session: StoredSession = {
    phone: DEMO_LOGIN_PHONE,
    expiresAt: Date.now() + AUTH_SESSION_DURATION_MS,
  };
  window.localStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(session));
  notifyAuthChanged();
  return session;
}

export function logoutSession() {
  window.localStorage.removeItem(AUTH_SESSION_KEY);
  notifyAuthChanged();
}

export function useAuth() {
  const [session, setSession] = useState<StoredSession | null>(() => readSession());

  useEffect(() => {
    const refresh = () => setSession(readSession());
    const timer = session
      ? window.setTimeout(refresh, Math.min(Math.max(0, session.expiresAt - Date.now()), MAX_TIMEOUT_MS))
      : undefined;
    window.addEventListener(AUTH_CHANGED_EVENT, refresh);
    window.addEventListener("storage", refresh);
    return () => {
      if (timer !== undefined) window.clearTimeout(timer);
      window.removeEventListener(AUTH_CHANGED_EVENT, refresh);
      window.removeEventListener("storage", refresh);
    };
  }, [session]);

  return {
    session,
    isAuthenticated: session !== null,
    login: loginDemoSession,
    logout: logoutSession,
  };
}
