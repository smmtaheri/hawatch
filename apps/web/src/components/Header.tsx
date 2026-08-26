import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";

export function Header() {
  return (
    <header className="site-header">
      <Logo />
      <div className="header-actions">
        <a href="/login" className="account-status" onClick={(event) => event.preventDefault()}>
          ورود
        </a>
        <ThemeToggle />
      </div>
    </header>
  );
}
