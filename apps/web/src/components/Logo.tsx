import { Link } from "react-router-dom";

export function Logo() {
  return (
    <Link to="/" className="brand" aria-label="هواچ، خانه">
      <span className="brand-logo-picture" aria-hidden="true">
        <img
          className="brand-logo brand-logo--dark-surface"
          src="/brand/hawatch-logo-light.svg"
          alt=""
        />
        <img
          className="brand-logo brand-logo--light-surface"
          src="/brand/hawatch-logo-dark.svg"
          alt=""
        />
      </span>
    </Link>
  );
}
