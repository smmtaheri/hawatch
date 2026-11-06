import { afterEach, describe, expect, it, vi } from "vitest";
import { createInternalNavigationTracker, markSearchNavigation } from "../src/lib/internalAnalytics";
import { trackPageView } from "../src/api/client";

const first = { path: "/", search: "?utm_source=telegram&utm_medium=social&utm_campaign=channel&token=secret", referrer: "https://t.me/private?token=secret" };
afterEach(() => { window.localStorage.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('passive internal attribution', () => {
  it('preserves acquisition through home/search/point/route without URL writes', () => {
    const send=vi.fn<typeof trackPageView>();const t=createInternalNavigationTracker(send,first);
    const push=vi.spyOn(window.history,'pushState');const replace=vi.spyOn(window.history,'replaceState');
    t.visit('/');markSearchNavigation('/points/tochal');t.visit('/points/tochal');t.visit('/routes/tochal-darband');
    expect(send).toHaveBeenCalledTimes(3);
    expect(send.mock.calls[0]![0]).toBe('entry');
    expect(send.mock.calls[1]![3]).toMatchObject({utm_source:'telegram',landing_path:'/',previous_path:'/',navigation_source:'site_search',referrer:'https://t.me/'});
    expect(send.mock.calls[2]![3]).toMatchObject({utm_source:'telegram',navigation_source:'point',previous_path:'/points/tochal'});
    expect(send.mock.calls[1]![3]!.session_id).toBe(send.mock.calls[2]![3]!.session_id);
    expect(JSON.stringify(send.mock.calls)).not.toContain('secret');
    expect(push).not.toHaveBeenCalled();expect(replace).not.toHaveBeenCalled();
  });

  it('counts real return visits but deduplicates effects and planner changes', () => {
    const send=vi.fn<typeof trackPageView>();const t=createInternalNavigationTracker(send,first);
    t.visit('/points/tochal');t.visit('/points/tochal');t.visit('/');t.visit('/points/tochal','POP');t.visit('/points/tochal','POP');
    expect(send.mock.calls.filter(c=>c[0]==='point')).toHaveLength(2);
    expect(send.mock.calls.at(-1)![3]!.navigation_source).toBe('history');
    expect(send.mock.calls[0]![2]).not.toBe(send.mock.calls.at(-1)![2]);
  });

  it('creates a new session after30minutes, not on each click or refresh', () => {
    let now=100000;vi.spyOn(Date,'now').mockImplementation(()=>now);
    const send=vi.fn<typeof trackPageView>();const t=createInternalNavigationTracker(send,first);
    t.visit('/points/tochal');const id=send.mock.calls[0]![3]!.session_id;
    now+=60000;const reload=createInternalNavigationTracker(send,{...first,path:'/points/tochal',search:''});reload.visit('/points/tochal');
    expect(send.mock.calls.at(-1)![3]!.session_id).toBe(id);
    now+=30*60*1000;reload.visit('/routes/tochal-darband');
    expect(send.mock.calls.at(-1)![3]!.session_id).not.toBe(id);
  });

  it('does not intercept navigation when storage is unavailable or corrupt', () => {
    window.localStorage.setItem('hawatch.analytics.session.v1','{broken');
    const send=vi.fn<typeof trackPageView>();const t=createInternalNavigationTracker(send,first);
    const setter=vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('disabled')});
    expect(()=>{t.visit('/');t.visit('/points/tochal');t.visit('/routes/tochal-darband')}).not.toThrow();
    expect(send).toHaveBeenCalledTimes(3);setter.mockRestore();
  });

  it('never sends a view for a missing public path or an unrelated page', () => {
    const send=vi.fn<typeof trackPageView>();const t=createInternalNavigationTracker(send,first);
    t.visit('/admin');t.visit('/login');expect(send).not.toHaveBeenCalled();
  });
});
