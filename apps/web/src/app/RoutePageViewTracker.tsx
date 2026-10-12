import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { notifyGa4Navigation } from "../lib/ga4";

export function RoutePageViewTracker({
  onPathname = notifyGa4Navigation,
}: {
  onPathname?: (pathname: string) => void;
}) {
  const { pathname } = useLocation();
  useEffect(() => onPathname(pathname), [onPathname, pathname]);
  return null;
}
