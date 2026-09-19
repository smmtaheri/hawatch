import { Link } from "react-router-dom";

export function Logo() {
  return (
    <Link to="/" className="brand" aria-label="هواچ، خانه">
      <span className="brand-logo-picture" aria-hidden="true">
        <img className="brand-logo" src="/brand/hawatch-logo-mark.svg" alt="" />
      </span>
    </Link>
  );
}
