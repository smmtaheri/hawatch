import { useEffect, useRef, useState } from "react";
import { apiUrl } from "../../api/client";
import type { ForecastAccess } from "../../types";

export type AuthSession = {
  authenticated: true;
  plan: { code: string; title: string; tier: "free" | "paid"; duration_months?: number | null } | null;
  forecast_access: ForecastAccess;
  days_remaining?: number | null;
  expires_at?: string | null;
};

const AUTH_CHANGED_EVENT = "hawatch-auth-changed";
const AUTH_SYNC_KEY = "hawatch.auth-change";
type AuthAction = "login" | "logout";
let syncStarted = false;
let syncChannel: BroadcastChannel | null = null;
const seenSignals = new Set<string>();

function notifyLocalAuthChanged(action: AuthAction) {
  window.dispatchEvent(new CustomEvent(AUTH_CHANGED_EVENT, { detail: { action } }));
}

function receiveAuthChange(message: unknown) {
  const action = (message as { action?: unknown } | null)?.action;
  const nonce = (message as { nonce?: unknown } | null)?.nonce;
  if ((action !== "login" && action !== "logout") || typeof nonce !== "string") return;
  if (seenSignals.has(nonce)) return;
  seenSignals.add(nonce);
  if (seenSignals.size > 100) seenSignals.delete(seenSignals.values().next().value!);
  notifyLocalAuthChanged(action);
}

function ensureAuthSync() {
  if (syncStarted) return;
  syncStarted = true;
  try {
    syncChannel = new BroadcastChannel(AUTH_SYNC_KEY);
    syncChannel.onmessage = (event) => receiveAuthChange(event.data);
  } catch { /* Storage events remain available when BroadcastChannel is blocked. */ }
  window.addEventListener("storage", (event) => {
    if (event.key !== AUTH_SYNC_KEY || !event.newValue) return;
    try { receiveAuthChange(JSON.parse(event.newValue)); } catch { /* Ignore unrelated malformed data. */ }
  });
}

function notifyAuthChanged(action: AuthAction) {
  ensureAuthSync();
  notifyLocalAuthChanged(action);
  // No account, cookie or credential is persisted: just an invalidation signal.
  const message = { action, nonce: `${Date.now()}:${Math.random()}` };
  seenSignals.add(message.nonce);
  try { localStorage.setItem(AUTH_SYNC_KEY, JSON.stringify(message)); } catch { /* Private/blocked storage. */ }
  try { syncChannel?.postMessage(message); } catch { /* Focus revalidation remains available. */ }
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

/**
 * A forecast response contains access flags that are evaluated by Django for
 * the current session. Keep a small shared revision for consumers of those
 * responses so a completed login or logout re-reads the flags immediately,
 * rather than waiting for a browser refresh.
 */
export function useAuthChangeVersion() {
  const [version, setVersion] = useState(0);

  useEffect(() => {
    ensureAuthSync();
    const bumpVersion = () => setVersion((current) => current + 1);
    window.addEventListener(AUTH_CHANGED_EVENT, bumpVersion);
    return () => window.removeEventListener(AUTH_CHANGED_EVENT, bumpVersion);
  }, []);

  return version;
}

async function csrfHeaders(): Promise<Record<string, string>> {
  try {
    const response = await fetch(apiUrl("auth/csrf/").toString(), { credentials: "same-origin", cache: "no-store" });
    const payload = await response.json() as { csrf_token?: string };
    return payload.csrf_token ? { "X-CSRFToken": payload.csrf_token } : {};
  } catch {
    return {};
  }
}

async function readMe(): Promise<AuthSession | null | undefined> {
  try {
    const response = await fetch(apiUrl("auth/me/").toString(), { credentials: "same-origin", cache: "no-store" });
    if (!response.ok) return response.status === 401 || response.status === 403 ? null : undefined;
    const payload = await response.json() as Partial<AuthSession>;
    // Some proxies normalize an unauthenticated response to HTTP 200. The
    // explicit server flag must remain authoritative for the client session.
    return payload.authenticated === true ? payload as AuthSession : null;
  } catch {
    return undefined;
  }
}

async function postAuth(path: string, payload?: object): Promise<AuthSession | null> {
  const csrf = await csrfHeaders();
  const response = await fetch(apiUrl(path).toString(), {
    method: "POST",
    credentials: "same-origin",
    cache: "no-store",
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
  const requestVersionRef = useRef(0);
  const sessionRef = useRef<AuthSession | null>(null);
  sessionRef.current = session;

  useEffect(() => {
    ensureAuthSync();
    let mounted = true;
    const refresh = (revalidate = false) => {
      const requestVersion = ++requestVersionRef.current;
      void readMe().then((next) => {
        if (!mounted || requestVersion !== requestVersionRef.current) return;
        if (next === undefined) {
          setLoading(false);
          return;
        }
        const changed = !!sessionRef.current !== !!next;
        sessionRef.current = next;
        setSession(next);
        setLoading(false);
        if (revalidate && changed) notifyLocalAuthChanged(next ? "login" : "logout");
      });
    };
    const onAuthChanged = (event: Event) => {
      if ((event as CustomEvent<{ action?: AuthAction }>).detail?.action === "logout") {
        // Clear immediately, and invalidate any pre-logout /me response.
        ++requestVersionRef.current;
        sessionRef.current = null;
        setSession(null);
        setLoading(false);
      } else refresh();
    };
    const onFocus = () => refresh(true);
    const onVisible = () => { if (document.visibilityState === "visible") refresh(true); };
    const onPageShow = (event: PageTransitionEvent) => { if (event.persisted) refresh(true); };
    refresh();
    window.addEventListener(AUTH_CHANGED_EVENT, onAuthChanged);
    window.addEventListener("focus", onFocus);
    window.addEventListener("pageshow", onPageShow);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      mounted = false;
      window.removeEventListener(AUTH_CHANGED_EVENT, onAuthChanged);
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("pageshow", onPageShow);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);

  return {
    session,
    loading,
    isAuthenticated: session !== null,
    async login(phone: string, code: string) {
      ++requestVersionRef.current;
      const next = await postAuth("auth/login/", { phone: normalizeIranPhone(phone), code });
      setSession(next);
      setLoading(false);
      notifyAuthChanged("login");
      return next;
    },
    async logout() {
      ++requestVersionRef.current;
      await postAuth("auth/logout/");
      setSession(null);
      setLoading(false);
      notifyAuthChanged("logout");
    },
  };
}
