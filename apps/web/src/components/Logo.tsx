import { Link } from "react-router-dom";
import brand from "./brandMark.svg?raw";
export function Logo() {
  return (
    <Link to="/" className="brand" aria-label="هواچ، خانه">
      <span aria-hidden="true" dangerouslySetInnerHTML={{ __html: brand }} />
    </Link>
  );
}
