import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";
import {
  ACCESS_REFRESH_MARGIN_MS,
  apiFetch,
  registerAuthBridge,
  withRefreshMutex,
  type TokenResponse,
  type UserPublic,
} from "./api";

export type AuthStatus = "loading" | "authenticated" | "anonymous";

type AuthContextValue = {
  authStatus: AuthStatus;
  accessToken: string | null;
  refreshToken: string | null;
  user: UserPublic | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<string | null>;
  setUser: (user: UserPublic | null) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const STORAGE_KEY = "identity_platform_refresh";

function initialAuthStatus(): AuthStatus {
  if (typeof sessionStorage === "undefined") return "anonymous";
  return sessionStorage.getItem(STORAGE_KEY) ? "loading" : "anonymous";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [authStatus, setAuthStatus] = useState<AuthStatus>(initialAuthStatus);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(() =>
    typeof sessionStorage !== "undefined" ? sessionStorage.getItem(STORAGE_KEY) : null,
  );
  const [user, setUser] = useState<UserPublic | null>(null);

  const accessTokenRef = useRef<string | null>(null);
  const refreshTokenRef = useRef<string | null>(refreshToken);
  const accessExpiresAtRef = useRef<number | null>(null);
  const proactiveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const bootstrapStartedRef = useRef(false);

  useEffect(() => {
    accessTokenRef.current = accessToken;
  }, [accessToken]);

  useEffect(() => {
    refreshTokenRef.current = refreshToken;
  }, [refreshToken]);

  const clearProactiveTimer = useCallback(() => {
    if (proactiveTimerRef.current) {
      clearTimeout(proactiveTimerRef.current);
      proactiveTimerRef.current = null;
    }
  }, []);

  const applyTokens = useCallback((tokens: TokenResponse) => {
    setAccessToken(tokens.access_token);
    setRefreshToken(tokens.refresh_token);
    sessionStorage.setItem(STORAGE_KEY, tokens.refresh_token);
    accessExpiresAtRef.current = Date.now() + tokens.expires_in * 1000;
  }, []);

  const performRefresh = useCallback(async (): Promise<string | null> => {
    const rt = refreshTokenRef.current;
    if (!rt) return null;
    try {
      const tokens = await apiFetch<TokenResponse>("/v1/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refresh_token: rt }),
      });
      applyTokens(tokens);
      return tokens.access_token;
    } catch {
      return null;
    }
  }, [applyTokens]);

  // Every refresh trigger (401 retry, proactive timer, bootstrap, visibility
  // change) must go through this single mutex — never call performRefresh()
  // directly — or two concurrent refreshes can race with the same refresh
  // token (docs/tech-debt.md item 8).
  const synchronizedRefresh = useCallback(
    (): Promise<string | null> => withRefreshMutex(performRefresh),
    [performRefresh],
  );

  const scheduleProactiveRefresh = useCallback(() => {
    clearProactiveTimer();
    const expiresAt = accessExpiresAtRef.current;
    if (!expiresAt || !refreshTokenRef.current) return;

    const runRefresh = () => {
      void synchronizedRefresh().then((token) => {
        if (token) scheduleProactiveRefresh();
      });
    };

    const msUntilRefresh = expiresAt - Date.now() - ACCESS_REFRESH_MARGIN_MS;
    if (msUntilRefresh <= 0) {
      runRefresh();
      return;
    }
    proactiveTimerRef.current = setTimeout(runRefresh, msUntilRefresh);
  }, [clearProactiveTimer, synchronizedRefresh]);

  const clearSession = useCallback(() => {
    clearProactiveTimer();
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
    accessExpiresAtRef.current = null;
    sessionStorage.removeItem(STORAGE_KEY);
    setAuthStatus("anonymous");
  }, [clearProactiveTimer]);

  const handleAuthFailure = useCallback(() => {
    clearSession();
    navigate("/login", { replace: true });
  }, [clearSession, navigate]);

  const logout = useCallback(async () => {
    const rt = refreshTokenRef.current;
    if (rt) {
      try {
        await apiFetch<void>("/v1/auth/logout", {
          method: "POST",
          body: JSON.stringify({ refresh_token: rt }),
        });
      } catch {
        /* best effort */
      }
    }
    clearSession();
  }, [clearSession]);

  const refreshSession = useCallback(async (): Promise<string | null> => {
    const token = await synchronizedRefresh();
    if (!token) {
      await logout();
      return null;
    }
    scheduleProactiveRefresh();
    return token;
  }, [logout, synchronizedRefresh, scheduleProactiveRefresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await apiFetch<TokenResponse>("/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      applyTokens(tokens);
      scheduleProactiveRefresh();
      try {
        const me = await apiFetch<UserPublic>("/v1/users/me", {
          accessToken: tokens.access_token,
        });
        setUser(me);
        setAuthStatus("authenticated");
      } catch (e) {
        // Tokens were already applied above; if the profile fetch fails, roll the
        // session back instead of leaving a live session under a "Login failed" UI
        // (docs/tech-debt.md item 27). Mirrors the bootstrap effect's same rollback.
        await logout();
        throw e;
      }
    },
    [applyTokens, scheduleProactiveRefresh, logout],
  );

  useEffect(() => {
    registerAuthBridge({
      getAccessToken: () => accessTokenRef.current,
      refreshAccessToken: async () => {
        const token = await synchronizedRefresh();
        if (token) scheduleProactiveRefresh();
        return token;
      },
      onAuthFailure: handleAuthFailure,
    });
    return () => registerAuthBridge(null);
  }, [handleAuthFailure, synchronizedRefresh, scheduleProactiveRefresh]);

  useEffect(() => {
    if (bootstrapStartedRef.current) return;
    if (!refreshTokenRef.current) {
      setAuthStatus("anonymous");
      return;
    }
    if (accessTokenRef.current) return;

    bootstrapStartedRef.current = true;
    setAuthStatus("loading");

    void (async () => {
      const token = await synchronizedRefresh();
      if (!token) {
        clearSession();
        return;
      }
      scheduleProactiveRefresh();
      try {
        const me = await apiFetch<UserPublic>("/v1/users/me", { accessToken: token });
        setUser(me);
        setAuthStatus("authenticated");
      } catch {
        await logout();
      }
    })();
  }, [clearSession, logout, synchronizedRefresh, scheduleProactiveRefresh]);

  useEffect(() => {
    const onVisibility = () => {
      if (document.visibilityState !== "visible") return;
      const expiresAt = accessExpiresAtRef.current;
      if (!expiresAt || !refreshTokenRef.current) return;
      if (expiresAt - Date.now() <= ACCESS_REFRESH_MARGIN_MS) {
        void synchronizedRefresh().then((token) => {
          if (token) scheduleProactiveRefresh();
        });
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [synchronizedRefresh, scheduleProactiveRefresh]);

  const value = useMemo(
    () => ({
      authStatus,
      accessToken,
      refreshToken,
      user,
      login,
      logout,
      refreshSession,
      setUser,
    }),
    [authStatus, accessToken, refreshToken, user, login, logout, refreshSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
