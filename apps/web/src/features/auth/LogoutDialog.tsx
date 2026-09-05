import { useEffect, useRef } from "react";

export function LogoutDialog({ onCancel, onConfirm }: { onCancel: () => void; onConfirm: () => void }) {
  const panelRef = useRef<HTMLElement>(null);

  useEffect(() => {
    panelRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onCancel]);

  return (
    <div className="logout-dialog" role="presentation">
      <button className="logout-dialog-backdrop" type="button" aria-label="بستن خروج" onClick={onCancel} />
      <section
        ref={panelRef}
        className="logout-dialog-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="logout-dialog-title"
        tabIndex={-1}
      >
        <h2 id="logout-dialog-title">خروج از حساب</h2>
        <p>آیا می‌خواهی از حساب هواچ خارج شوی؟</p>
        <div className="logout-dialog-actions">
          <button type="button" className="logout-dialog-cancel" onClick={onCancel}>انصراف</button>
          <button type="button" className="logout-dialog-confirm" onClick={onConfirm}>خروج</button>
        </div>
      </section>
    </div>
  );
}
