const API_BASE = import.meta.env.VITE_API_URL ?? "";

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type UserPublic = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  locale: string;
  timezone: string;
  email_verified: boolean;
  created_at: string;
};

export type FieldError = { field: string; message: string };

export class HttpError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly fieldErrors: FieldError[] = [],
  ) {
    super(message);
    this.name = "HttpError";
  }
}

// FastAPI's own 422s (unlike our HTTPException(detail=str) ones) return
// `detail` as an array of {loc, msg, type} — one per invalid field. Surface
// those as per-field errors instead of a generic message (docs/tech-debt.md item 28).
async function parseError(res: Response): Promise<{ message: string; fieldErrors: FieldError[] }> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") {
      return { message: body.detail, fieldErrors: [] };
    }
    if (Array.isArray(body.detail)) {
      const fieldErrors: FieldError[] = body.detail
        .map((item: { loc?: unknown[]; msg?: string }) => {
          const field = Array.isArray(item.loc) ? item.loc.at(-1) : undefined;
          return typeof field === "string" && typeof item.msg === "string"
            ? { field, message: item.msg }
            : null;
        })
        .filter((e: FieldError | null): e is FieldError => e !== null);
      if (fieldErrors.length > 0) {
        return { message: fieldErrors.map((e) => e.message).join("; "), fieldErrors };
      }
    }
  } catch {
    /* ignore */
  }
  return { message: res.statusText, fieldErrors: [] };
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { accessToken?: string | null } = {},
): Promise<T> {
  const { accessToken, headers, ...rest } = options;
  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...headers,
    },
  });
  if (!res.ok) {
    const { message, fieldErrors } = await parseError(res);
    throw new HttpError(message, res.status, fieldErrors);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type AuthBridge = {
  getAccessToken: () => string | null;
  refreshAccessToken: () => Promise<string | null>;
  onAuthFailure: () => void;
};

let authBridge: AuthBridge | null = null;

export function registerAuthBridge(bridge: AuthBridge | null): void {
  authBridge = bridge;
}

let refreshMutex: Promise<string | null> | null = null;

/**
 * Every refresh trigger (401 retry, proactive timer, bootstrap, visibility
 * change — F-007) must call refresh through this shared mutex, or two
 * concurrent refreshes can present the same refresh token at once. Harmless
 * today (Wave 1 doesn't rotate refresh tokens), but Wave 3 rotation with
 * reuse detection would treat that as theft and kill the session
 * (docs/tech-debt.md item 8). `auth.tsx`'s `synchronizedRefresh` wraps
 * `performRefresh` with this mutex and is the single entry point every
 * trigger (including `authBridge.refreshAccessToken`, used below) calls
 * through — never wrap `refreshAccessToken()` in this mutex again here,
 * or the two wrap layers race each other on this same module-level lock.
 */
export async function withRefreshMutex(
  refreshFn: () => Promise<string | null>,
): Promise<string | null> {
  if (!refreshMutex) {
    refreshMutex = refreshFn().finally(() => {
      refreshMutex = null;
    });
  }
  return refreshMutex;
}

/** Authenticated API calls with single 401 → refresh → retry (F-007). */
export async function apiFetchAuth<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (!authBridge) {
    throw new Error("Auth bridge not registered");
  }

  const attempt = (token: string | null) =>
    apiFetch<T>(path, {
      ...options,
      accessToken: token,
    });

  let token = authBridge.getAccessToken();
  try {
    return await attempt(token);
  } catch (e) {
    if (!(e instanceof HttpError) || e.status !== 401) throw e;
  }

  // authBridge.refreshAccessToken is already synchronized on the mutex
  // above (see auth.tsx's synchronizedRefresh) — do not wrap it here too.
  token = await authBridge.refreshAccessToken();
  if (!token) {
    authBridge.onAuthFailure();
    throw new HttpError("Session expired", 401);
  }

  try {
    return await attempt(token);
  } catch (e) {
    if (e instanceof HttpError && e.status === 401) {
      authBridge.onAuthFailure();
    }
    throw e;
  }
}

export const ACCESS_REFRESH_MARGIN_MS = 2 * 60 * 1000;
