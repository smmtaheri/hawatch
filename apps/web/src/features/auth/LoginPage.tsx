import { Navigate, useLocation } from "react-router-dom";
// Preserve old login links while all interaction lives below the header avatar.
export function LoginPage() {
  const location = useLocation();
  const value = new URLSearchParams(location.search).get("returnTo");
  const target =
    value?.startsWith("/") &&
    !value.startsWith("//") &&
    !value.startsWith("/login")
      ? value
      : "/";
  return <Navigate to={target} replace state={{ openAccountLogin: true }} />;
}
export const LoginOverlay = LoginPage;
