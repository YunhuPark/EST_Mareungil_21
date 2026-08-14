/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 백엔드 주소. 비워두면 vite.config.ts 의 /api 프록시를 쓴다. */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
