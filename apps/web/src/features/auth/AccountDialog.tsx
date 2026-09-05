import { useEffect, useRef } from "react";

export function AccountDialog({ planTitle, onClose, onLogout }: { planTitle: string; onClose: () => void; onLogout: () => void }) {
  const panelRef = useRef<HTMLElement>(null);

  useEffect(() => {
    panelRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div className="logout-dialog" role="presentation">
      <button className="logout-dialog-backdrop" type="button" aria-label="بستن حساب" onClick={onClose} />
      <section ref={panelRef} className="logout-dialog-panel account-dialog-panel" role="dialog" aria-modal="true" aria-labelledby="account-dialog-title" tabIndex={-1}>
        <h2 id="account-dialog-title">حساب کاربری</h2>
        <p>طرح فعلی: <strong>{planTitle}</strong></p>
        <div className="logout-dialog-actions">
          <button type="button" className="logout-dialog-confirm" onClick={onLogout}>خروج از حساب</button>
        </div>
      </section>
    </div>
  );
}
