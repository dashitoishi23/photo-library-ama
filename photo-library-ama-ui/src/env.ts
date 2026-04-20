interface AppEnv {
    VITE_BACKEND_HOST: string;
    VITE_BACKEND_PORT: string;
}

declare global {
    interface Window {
        _env_?: Partial<AppEnv>
    }
}

export const env: AppEnv = {
    VITE_BACKEND_HOST: window._env_?.VITE_BACKEND_HOST ?? import.meta.env.VITE_BACKEND_HOST ?? 'localhost',
    VITE_BACKEND_PORT: window._env_?.VITE_BACKEND_PORT ?? import.meta.env.VITE_BACKEND_PORT ?? '8081'
}