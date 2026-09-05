const INSTAGRAM_URL = "https://www.instagram.com/hawatchir/";
const TELEGRAM_URL = "https://t.me/hawatchir";

export function SocialLinks() {
  return (
    <nav className="header-social" aria-label="شبکه‌های اجتماعی هواچ">
      <a
        className="header-social-link"
        href={INSTAGRAM_URL}
        target="_blank"
        rel="noopener noreferrer"
        aria-label="اینستاگرام هواچ"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <rect x="3.25" y="3.25" width="17.5" height="17.5" rx="5" />
          <circle cx="12" cy="12" r="4.1" />
          <circle className="header-social-icon-dot" cx="17.35" cy="6.7" r="1" />
        </svg>
      </a>
      <a
        className="header-social-link"
        href={TELEGRAM_URL}
        target="_blank"
        rel="noopener noreferrer"
        aria-label="تلگرام هواچ"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path d="m21 3-3.2 17.8c-.24 1.28-.93 1.6-1.88 1L10.7 17.4l-2.53 2.43c-.28.28-.52.52-1.07.52l.38-5.34L17.2 7.3c.38-.34-.08-.53-.59-.19L6.25 13.7.96 12.05c-1.15-.36-1.17-1.15.24-1.7L19.9 3.1C20.84 2.75 21.66 3.32 21 3Z" />
        </svg>
      </a>
    </nav>
  );
}
