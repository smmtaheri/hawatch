import { Link } from "react-router-dom";

export function Logo() {
  return (
    <Link to="/" className="brand" aria-label="هواچ، خانه">
      <svg className="brand-mark" viewBox="0 0 76 34" aria-hidden="true">
        <path className="brand-route" d="M6 9 37 25 69 6" />
        <circle className="brand-node node-start" cx="6" cy="9" r="3.5" />
        <circle className="brand-node node-mid" cx="37" cy="25" r="3.5" />
        <circle className="brand-node node-end" cx="69" cy="6" r="3.5" />
      </svg>
      <span>هواچ</span>
    </Link>
  );
}
