import { useEffect, useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { DesignIcon } from "./DesignIcon";
export function Dialog({
  title,
  onClose,
  children,
  className = "",
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    if (el.showModal) el.showModal();
    else el.setAttribute("open", "");
    return () => {
      el.close?.();
      document.body.style.overflow = overflow;
      previous?.focus?.({ preventScroll: true });
    };
  }, []);
  return createPortal(
    <dialog
      ref={ref}
      className={className}
      aria-labelledby={id}
      onCancel={(e) => {
        e.preventDefault();
        closeRef.current();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          const r = e.currentTarget.getBoundingClientRect();
          if (
            e.clientX < r.left ||
            e.clientX > r.right ||
            e.clientY < r.top ||
            e.clientY > r.bottom
          )
            closeRef.current();
        }
      }}
    >
      <span className="sheet-handle" aria-hidden="true" />
      <div className="dialog-header">
        <h2 id={id}>{title}</h2>
        <button
          className="close-button"
          type="button"
          aria-label="بستن"
          onClick={onClose}
        >
          <DesignIcon name="close" />
        </button>
      </div>
      {children}
    </dialog>,
    document.body,
  );
}
