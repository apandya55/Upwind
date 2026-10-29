/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_SURFACE?: "local" | "explorer";
  readonly VITE_SITE_URL?: string;
  readonly VITE_API_BASE_URL?: string;
}
