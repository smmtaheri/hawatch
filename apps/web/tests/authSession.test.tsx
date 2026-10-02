import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAuth, useAuthChangeVersion } from "../src/features/auth/authSession";

let channel: FakeChannel;
class FakeChannel {
  onmessage: ((event: { data: unknown }) => void) | null = null;
  postMessage = vi.fn();
  constructor() { channel = this; }
}
vi.stubGlobal("BroadcastChannel", FakeChannel);
const loggedIn = { authenticated: true, plan: null, forecast_access: {} };
const response = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body });
let loggedInOnServer = true;
let fetchMock: ReturnType<typeof vi.fn>;
let nonce = 0;
const storageSignal = (action: string) => window.dispatchEvent(new StorageEvent("storage", {
  key: "hawatch.auth-change", newValue: JSON.stringify({ action, nonce: String(++nonce) }),
}));

beforeEach(() => {
  loggedInOnServer = true;
  localStorage.clear();
  fetchMock = vi.fn(async (input: string) => {
    if (input.includes("auth/logout/")) { loggedInOnServer = false; return response({ authenticated: false }); }
    if (input.includes("auth/csrf/")) return response({ csrf_token: "test" });
    return response(loggedInOnServer ? loggedIn : { authenticated: false });
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(cleanup);

describe("browser tab session synchronization", () => {
  it("broadcasts only successful logout and clears all local consumers", async () => {
    const a = renderHook(useAuth), b = renderHook(useAuth);
    await waitFor(() => expect(a.result.current.isAuthenticated && b.result.current.isAuthenticated).toBe(true));
    await act(async () => { await a.result.current.logout(); });
    expect(a.result.current.isAuthenticated || b.result.current.isAuthenticated).toBe(false);
    expect(JSON.parse(localStorage.getItem("hawatch.auth-change")!).action).toBe("logout");
    expect(channel.postMessage).toHaveBeenCalledWith(expect.objectContaining({ action: "logout" }));
  });

  it("clears a peer tab immediately and rejects its late pre-logout account response", async () => {
    const auth = renderHook(useAuth), revision = renderHook(useAuthChangeVersion);
    await waitFor(() => expect(auth.result.current.isAuthenticated).toBe(true));
    let complete!: (value: unknown) => void;
    fetchMock.mockImplementationOnce(() => new Promise(resolve => { complete = resolve; }));
    act(() => window.dispatchEvent(new Event("focus")));
    act(() => storageSignal("logout"));
    expect(auth.result.current.isAuthenticated).toBe(false);
    expect(revision.result.current).toBe(1);
    await act(async () => { complete(response(loggedIn)); });
    expect(auth.result.current.isAuthenticated).toBe(false);
  });

  it("handles BroadcastChannel and storage delivery of the same signal once", async () => {
    const auth = renderHook(useAuth), revision = renderHook(useAuthChangeVersion);
    await waitFor(() => expect(auth.result.current.isAuthenticated).toBe(true));
    const message = { action: "logout", nonce: String(++nonce) };
    act(() => {
      channel.onmessage?.({ data: message });
      window.dispatchEvent(new StorageEvent("storage", { key: "hawatch.auth-change", newValue: JSON.stringify(message) }));
    });
    expect(auth.result.current.isAuthenticated).toBe(false);
    expect(revision.result.current).toBe(1);
  });

  it("revalidates a suspended tab on focus and restored Back navigation", async () => {
    const auth = renderHook(useAuth), revision = renderHook(useAuthChangeVersion);
    await waitFor(() => expect(auth.result.current.isAuthenticated).toBe(true));
    loggedInOnServer = false;
    act(() => window.dispatchEvent(new Event("focus")));
    await waitFor(() => expect(auth.result.current.isAuthenticated).toBe(false));
    expect(revision.result.current).toBe(1);
    loggedInOnServer = true;
    act(() => window.dispatchEvent(new PageTransitionEvent("pageshow", { persisted: true })));
    await waitFor(() => expect(auth.result.current.isAuthenticated).toBe(true));
  });

  it("does not announce logout when the server rejects the request", async () => {
    const auth = renderHook(useAuth);
    await waitFor(() => expect(auth.result.current.isAuthenticated).toBe(true));
    fetchMock.mockImplementation(async (input: string) => input.includes("logout") ? response({}, 403) : response({ csrf_token: "test" }));
    await act(async () => { await expect(auth.result.current.logout()).rejects.toThrow(); });
    expect(auth.result.current.isAuthenticated).toBe(true);
    expect(localStorage.getItem("hawatch.auth-change")).toBeNull();
  });

  it("keeps the last verified account state on a temporary revalidation failure", async () => {
    const auth = renderHook(useAuth);
    await waitFor(() => expect(auth.result.current.isAuthenticated).toBe(true));
    fetchMock.mockRejectedValueOnce(new Error("offline"));
    await act(async () => window.dispatchEvent(new Event("focus")));
    expect(auth.result.current.isAuthenticated).toBe(true);
  });
});
