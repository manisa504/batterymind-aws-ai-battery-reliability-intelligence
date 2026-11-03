import {token} from './auth';

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export async function api<T>(base: string, path: string, init: {method?: string; body?: unknown} = {}): Promise<T> {
  const t = token();
  const r = await fetch(`${base}${path}`, {
    method: init.method ?? 'GET',
    headers: {'Content-Type': 'application/json', ...(t ? {Authorization: `Bearer ${t}`} : {})},
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  });
  if (r.status === 204) return undefined as T;
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(r.status, typeof data.detail === 'string' ? data.detail : `Request failed (${r.status})`);
  return data as T;
}

export const newKey = () => crypto.randomUUID();
