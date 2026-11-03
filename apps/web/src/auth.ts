// Cognito hosted-UI sign-in using the authorization-code flow with PKCE (no client secret in the browser).
export type AppConfig = {apiBase: string; cognitoDomain: string; clientId: string};

const KEY = 'bm.idToken';
const VERIFIER = 'bm.pkce';

export async function loadConfig(): Promise<AppConfig | null> {
  try {
    const r = await fetch('/config.json', {cache: 'no-store'});
    if (!r.ok || !(r.headers.get('content-type') ?? '').includes('json')) return null;
    return (await r.json()) as AppConfig;
  } catch {
    return null;
  }
}

const b64url = (buf: ArrayBuffer) =>
  btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

const redirectUri = () => `${window.location.origin}/`;

export async function startLogin(cfg: AppConfig): Promise<void> {
  const verifier = b64url(crypto.getRandomValues(new Uint8Array(32)).buffer);
  sessionStorage.setItem(VERIFIER, verifier);
  const challenge = b64url(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier)));
  const q = new URLSearchParams({
    response_type: 'code', client_id: cfg.clientId, redirect_uri: redirectUri(), scope: 'openid email',
    code_challenge: challenge, code_challenge_method: 'S256',
  });
  window.location.assign(`${cfg.cognitoDomain}/oauth2/authorize?${q}`);
}

/** Completes the redirect from Cognito, if present, and stores the ID token for this tab only. */
export async function completeLogin(cfg: AppConfig): Promise<void> {
  const params = new URLSearchParams(window.location.search);
  const code = params.get('code');
  const verifier = sessionStorage.getItem(VERIFIER);
  if (!code || !verifier) return;
  window.history.replaceState({}, '', window.location.pathname);
  const r = await fetch(`${cfg.cognitoDomain}/oauth2/token`, {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: new URLSearchParams({
      grant_type: 'authorization_code', client_id: cfg.clientId, code, redirect_uri: redirectUri(), code_verifier: verifier,
    }),
  });
  sessionStorage.removeItem(VERIFIER);
  if (r.ok) sessionStorage.setItem(KEY, (await r.json()).id_token);
}

export function token(): string | null {
  const t = sessionStorage.getItem(KEY);
  if (!t) return null;
  try {
    const exp = JSON.parse(atob(t.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).exp as number;
    if (exp * 1000 < Date.now()) { sessionStorage.removeItem(KEY); return null; }
  } catch { sessionStorage.removeItem(KEY); return null; }
  return t;
}

export function logout(cfg: AppConfig): void {
  sessionStorage.removeItem(KEY);
  window.location.assign(`${cfg.cognitoDomain}/logout?client_id=${cfg.clientId}&logout_uri=${encodeURIComponent(redirectUri())}`);
}
