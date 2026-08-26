export function ErrorState({ onRetry, message }: { onRetry: () => void; message?: string }) {
  return (
    <div className="hawatch-state error" role="alert">
      <strong>بارگذاری ناموفق بود</strong>
      <p>{message ?? "اتصال به API داخلی هواچ برقرار نشد. دوباره تلاش کن."}</p>
      <button type="button" onClick={onRetry}>
        تلاش دوباره
      </button>
    </div>
  );
}
