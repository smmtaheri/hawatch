import { Link, useLocation } from "react-router-dom";
import { Logo } from "./Logo";
import { SocialLinks } from "./SocialLinks";
import { ThemeToggle } from "./ThemeToggle";

export function Header() {
  const location = useLocation();
  const { pathname } = location;
  const returnTo = `${location.pathname}${location.search}`;

  return (
    <header className="site-header">
      <Logo />
      <div className="header-actions">
        <SocialLinks />
        {pathname !== "/login" ? (
          <Link
            to={{ pathname: "/login", search: `?${new URLSearchParams({ returnTo }).toString()}` }}
            state={{ backgroundLocation: location }}
            className="account-status"
          >
            ورود
          </Link>
        ) : null}
        <ThemeToggle />
      </div>
    </header>
  );
}
