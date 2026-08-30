import { Link } from "react-router-dom";
import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";

export function Header() {
  return (
    <header className="site-header">
      <Logo />
      <div className="header-actions">
        <Link to="/login" className="account-status">
          ورود
        </Link>
        <ThemeToggle />
      </div>
    </header>
  );
}
