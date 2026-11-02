import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { notifyGa4Navigation } from "../lib/ga4";

export function RoutePageViewTracker({
  onLocation = notifyGa4Navigation,
}: {
  onLocation?: (pathname: string, search: string) => void;
}) {
  const { pathname, search } = useLocation();
  useEffect(() => onLocation(pathname, search), [onLocation, pathname, search]);
  return null;
}
