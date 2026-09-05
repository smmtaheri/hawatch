import { useEffect, useState } from "react";
import { apiUrl } from "../../api/client";
import type { ForecastAccess } from "../../types";

export type AuthSession = {
  authenticated: true;
  plan: { code: string; title: string; tier: "free" | "paid" } | null;
  forecast_access: ForecastAccess;
};

const AUTH_CHANGED_EVENT = "hawatch-auth-changed";

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

async function csrfHeaders(): Promise<Record<string, string>> {
  try {
    const response = await fetch(apiUrl("auth/csrf/").toString(), { credentials: "same-origin" });
    const payload = await response.json() as { csrf_token?: string };
    return payload.csrf_token ? { "X-CSRFToken": payload.csrf_token } : {};
  } catch {
    return {};
  }
}

async function readMe(): Promise<AuthSession | null> {
  try {
    const response = await fetch(apiUrl("auth/me/").toString(), { credentials: "same-origin" });
    if (!response.ok) return null;
    return await response.json() as AuthSession;
  } catch {
    return null;
  }
}

async function postAuth(path: string, payload?: object): Promise<AuthSession | null> {
  const csrf = await csrfHeaders();
  const response = await fetch(apiUrl(path).toString(), {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...csrf },
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const body = await response.json().catch(() => ({})) as AuthSession & { detail?: string };
  if (!response.ok) throw new Error(body.detail || "ورود ناموفق بود.");
  return body.authenticated ? body : null;
}

export function useAuth() {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const refresh = () => {
      void readMe().then((next) => {
        if (!mounted) return;
        setSession(next);
        setLoading(false);
      });
    };
    refresh();
    window.addEventListener(AUTH_CHANGED_EVENT, refresh);
    return () => {
      mounted = false;
      window.removeEventListener(AUTH_CHANGED_EVENT, refresh);
    };
  }, []);

  return {
    session,
    loading,
    isAuthenticated: session !== null,
    async login(phone: string, code: string) {
      const next = await postAuth("auth/login/", { phone: normalizeIranPhone(phone), code });
      setSession(next);
      setLoading(false);
      notifyAuthChanged();
      return next;
    },
    async logout() {
      await postAuth("auth/logout/");
      setSession(null);
      notifyAuthChanged();
    },
  };
}
