/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_QA_PREVIEW?: string;
  readonly VITE_PUBLIC_SITE_ORIGIN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
