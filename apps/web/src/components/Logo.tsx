import { Link } from "react-router-dom";

export function Logo() {
  return (
    <Link to="/" className="brand" aria-label="هواچ، خانه">
      <span className="brand-logo-picture" aria-hidden="true">
        <img className="brand-logo brand-logo--dark-surface" src="/brand/hawatch-logo-mark-dark.svg" alt="" />
        <img className="brand-logo brand-logo--light-surface" src="/brand/hawatch-logo-mark-light.svg" alt="" />
      </span>
    </Link>
  );
}
