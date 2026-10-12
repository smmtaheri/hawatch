/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_GA4_MEASUREMENT_ID?: string;
  readonly VITE_QA_PREVIEW?: string;
  readonly VITE_PUBLIC_SITE_ORIGIN?: string;
  readonly PROD: boolean;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
