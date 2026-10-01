import { DesignIcon } from "./DesignIcon";
export function SocialLinks() {
  return (
    <>
      <a
        className="nav-button social-full"
        href="https://t.me/hawatchir"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="تلگرام هواچ"
      >
        <DesignIcon name="telegram" />
      </a>
      <a
        className="nav-button social-full"
        href="https://www.instagram.com/hawatchir/"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="اینستاگرام هواچ"
      >
        <DesignIcon name="instagram" />
      </a>
    </>
  );
}
