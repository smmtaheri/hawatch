import { Link, useLocation } from "react-router-dom";
import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";

export function Header() {
  const { pathname } = useLocation();

  return (
    <header className="site-header">
      <Logo />
      <div className="header-actions">
        {pathname !== "/login" ? (
          <Link to="/login" className="account-status">
            ورود
          </Link>
        ) : null}
        <ThemeToggle />
      </div>
    </header>
  );
}
