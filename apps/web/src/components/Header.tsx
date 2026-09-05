import { Link, useLocation } from "react-router-dom";
import { Logo } from "./Logo";
import { SocialLinks } from "./SocialLinks";
import { ThemeToggle } from "./ThemeToggle";
import { AccountDialog } from "../features/auth/AccountDialog";
import { useAuth } from "../features/auth/authSession";
import { useState } from "react";

export function Header() {
  const location = useLocation();
  const { pathname } = location;
  const returnTo = `${location.pathname}${location.search}`;
  const { isAuthenticated, logout, session } = useAuth();
  const [accountOpen, setAccountOpen] = useState(false);

  const confirmLogout = async () => {
    try {
      await logout();
    } finally {
      setAccountOpen(false);
    }
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
          <div className="account-menu-anchor">
            <button
              type="button"
              className="account-status signed-in"
              aria-expanded={accountOpen}
              aria-controls="account-menu"
              onClick={() => setAccountOpen(true)}
            >
              حساب
            </button>
            {accountOpen ? <AccountDialog planTitle={session?.plan?.title || "عضویت رایگان"} onClose={() => setAccountOpen(false)} onLogout={() => { void confirmLogout(); }} /> : null}
          </div>
        ) : null}
        <ThemeToggle />
      </div>
    </header>
  );
}
