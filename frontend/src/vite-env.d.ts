/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_API_TIMEOUT: string;
  readonly VITE_SSE_RECONNECT_INTERVAL: string;
  readonly VITE_SSE_MAX_RECONNECT_ATTEMPTS: string;
  readonly VITE_SSE_HEARTBEAT_TIMEOUT: string;
  readonly VITE_DEV_MODE: string;
  readonly VITE_LOG_API_REQUESTS: string;
  readonly VITE_TEST_TOKEN: string;
  readonly VITE_TEST_USER_EMAIL: string;
  readonly VITE_TEST_USER_ID: string;
  readonly VITE_FRONTEND_PORT: string;
  readonly VITE_BACKEND_PORT: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
