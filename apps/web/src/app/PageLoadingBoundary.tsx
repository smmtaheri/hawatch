import { Component, Suspense, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { PageShell } from "../components/PageShell";
import { LoadingState } from "../components/LoadingState";

function PagePreparation({ failed = false }: { failed?: boolean }) {
  const { pathname } = useLocation();
  const className = pathname.startsWith('/routes') ? 'route-page' : pathname.startsWith('/points/') ? 'point-page' : 'destinations-page';
  return <PageShell className={className} back showInitialContent loadingState={failed ? 'error' : 'loading'}>
    {failed ? <p role="alert">بارگذاری صفحه کامل نشده؛ لطفاً صفحه را رفرش کنید.</p> : <LoadingState label="در حال آماده‌سازی صفحه…" />}
  </PageShell>;
}

class PageErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <PagePreparation failed /> : this.props.children; }
}

export function PageLoadingBoundary({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  return <PageErrorBoundary key={pathname}>
    <Suspense fallback={<PagePreparation />}>{children}</Suspense>
  </PageErrorBoundary>;
}
