import { useTheme } from "../app/theme";
import { DesignIcon } from "./DesignIcon";
export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      className="nav-button theme-toggle"
      type="button"
      aria-label="تغییر تم"
      aria-pressed={theme === "dark"}
      onClick={toggle}
    >
      <DesignIcon name={theme === "dark" ? "sun" : "moon"} />
    </button>
  );
}
