type InitialPageRequest = {
  url: string;
  credentials: RequestCredentials;
  response: Promise<Response>;
};

declare global {
  interface Window {
    __hawatchPageLoad?: {
      start(pathname: string): void;
      complete(pathname: string): void;
      fail(pathname: string): void;
    };
    __hawatchInitialPageRequest?: InitialPageRequest;
  }
}

/** Consume the read started in the initial HTML, never a second request. */
export function takeInitialPageRequest(url: string, credentials: RequestCredentials): Promise<Response> | undefined {
  const initial = window.__hawatchInitialPageRequest;
  if (!initial || initial.url !== new URL(url, window.location.origin).href || initial.credentials !== credentials) return;
  delete window.__hawatchInitialPageRequest;
  return initial.response;
}

export function startPageLoad(pathname: string) {
  window.__hawatchPageLoad?.start(pathname);
}
export function completePageLoad(pathname: string) {
  window.__hawatchPageLoad?.complete(pathname);
}
export function failPageLoad(pathname: string) {
  window.__hawatchPageLoad?.fail(pathname);
}
