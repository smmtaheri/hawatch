import { Link, useLocation } from "react-router-dom";
import { Logo } from "./Logo";
import { SocialLinks } from "./SocialLinks";
import { ThemeToggle } from "./ThemeToggle";
import { LogoutDialog } from "../features/auth/LogoutDialog";
import { useAuth } from "../features/auth/authSession";
import { useState } from "react";

export function Header() {
  const location = useLocation();
  const { pathname } = location;
  const returnTo = `${location.pathname}${location.search}`;
  const { isAuthenticated, logout } = useAuth();
  const [logoutOpen, setLogoutOpen] = useState(false);

  const confirmLogout = () => {
    logout();
    setLogoutOpen(false);
  };

  return (
    <header className="site-header">
      <Logo />
      <div className="header-actions">
        <SocialLinks />
        {pathname !== "/login" && !isAuthenticated ? (
          <Link
            to={{ pathname: "/login", search: `?${new URLSearchParams({ returnTo }).toString()}` }}
            state={{ backgroundLocation: location }}
            className="account-status"
          >
            ورود
          </Link>
        ) : null}
        {pathname !== "/login" && isAuthenticated ? (
          <button type="button" className="account-status signed-in" onClick={() => setLogoutOpen(true)}>
            خروج
          </button>
        ) : null}
        <ThemeToggle />
      </div>
      {logoutOpen ? <LogoutDialog onCancel={() => setLogoutOpen(false)} onConfirm={confirmLogout} /> : null}
    </header>
  );
}
