export function LoadingState({ label = "در حال بارگذاری پیش‌بینی…" }: { label?: string }) {
  return (
    <div className="hawatch-state loading" role="status" aria-live="polite">
      {label}
    </div>
  );
}
