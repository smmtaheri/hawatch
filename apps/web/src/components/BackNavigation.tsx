import { useNavigate } from "react-router-dom";

/** Return to the actual page the visitor came from, with Home as a direct-entry fallback. */
export function BackNavigation({ ariaLabel }: { ariaLabel?: string }) {
  const navigate = useNavigate();

  function goBack() {
    if (window.history.length > 1) {
      navigate(-1);
      return;
    }
    navigate("/");
  }

  return (
    <button type="button" className="page-back-link" onClick={goBack} aria-label={ariaLabel ?? "بازگشت به صفحهٔ قبل"}>
      <span>بازگشت</span>
      <span aria-hidden="true">←</span>
    </button>
  );
}
