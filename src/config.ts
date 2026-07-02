const rawUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';
export const API_BASE_URL = rawUrl.endsWith('/api/v1') ? rawUrl : `${rawUrl.replace(/\/$/, '')}/api/v1`;

