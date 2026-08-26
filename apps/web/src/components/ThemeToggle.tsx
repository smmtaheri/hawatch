import { useTheme } from "../app/theme";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      className={`theme-toggle ${theme}`}
      type="button"
      aria-label="تغییر تم"
      aria-pressed={theme === "dark"}
      onClick={toggle}
    >
      <span className="theme-option-dark" aria-hidden="true">
        ☼
      </span>
      <span className="theme-option-light" aria-hidden="true">
        ◐
      </span>
      <small className="theme-option-dark">روشن</small>
      <small className="theme-option-light">تیره</small>
    </button>
  );
}
