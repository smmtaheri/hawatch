import { useEffect, useRef } from "react";

export function AccountDialog({ planTitle, onClose, onLogout }: { planTitle: string; onClose: () => void; onLogout: () => void }) {
  const panelRef = useRef<HTMLElement>(null);

  useEffect(() => {
    panelRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    const onPointerDown = (event: PointerEvent) => {
      if (!panelRef.current?.contains(event.target as Node)) onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [onClose]);

  return (
    <section id="account-menu" ref={panelRef} className="account-menu-popover" role="dialog" aria-labelledby="account-dialog-title" tabIndex={-1}>
        <h2 id="account-dialog-title">حساب کاربری</h2>
        <p>طرح فعلی: <strong>{planTitle}</strong></p>
        <div className="account-menu-actions">
          <button type="button" className="account-menu-logout" onClick={onLogout}>خروج از حساب</button>
        </div>
    </section>
  );
}
