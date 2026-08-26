export function StaleDataNotice({ generatedAt }: { generatedAt?: string | null }) {
  return (
    <div className="hawatch-state stale" role="status">
      دادهٔ نمایش‌داده‌شده ممکن است قدیمی باشد
      {generatedAt ? <p>آخرین تولید: {generatedAt}</p> : null}
    </div>
  );
}
