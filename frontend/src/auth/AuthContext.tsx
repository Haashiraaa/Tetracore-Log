// frontend/src/auth/AuthContext.tsx
// Who is logged in. The profile always comes from the server (/auth/me or the
// login response); it is never rebuilt from the token.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import * as authApi from "@/api/auth";
import { setAuthHandlers } from "@/api/client";
import type { OfficerProfile } from "@/api/schemas";
import { ErrorCode, isApiError } from "@/exceptions/errors";
import { tokenStore } from "@/security/tokenStore";
import * as authService from "@/services/authService";

export type AuthStatus = "booting" | "anonymous" | "authenticated" | "unreachable";

interface AuthContextValue {
  status: AuthStatus;
  profile: OfficerProfile | null;
  /** Why the guard was sent back to the login screen, if the app did it. */
  notice: string | null;
  login(input: authService.LoginInput): Promise<OfficerProfile>;
  logout(): Promise<void>;
  reloadProfile(): Promise<OfficerProfile | null>;
  retryBoot(): void;
  dismissNotice(): void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("booting");
  const [profile, setProfile] = useState<OfficerProfile | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const endSession = useCallback((message: string | null) => {
    tokenStore.clear();
    setProfile(null);
    setStatus("anonymous");
    setNotice(message);
  }, []);

  /** null = the session is gone (handlers already reset state). Throws on network trouble. */
  const reloadProfile = useCallback(async (): Promise<OfficerProfile | null> => {
    try {
      const p = await authApi.me();
      setProfile(p);
      setStatus("authenticated");
      return p;
    } catch (e) {
      // Network trouble or a server fault says nothing about the session: don't drop it.
      if (isApiError(e) && (e.code === ErrorCode.Network || e.status >= 500)) throw e;
      return null;
    }
  }, []);

  useEffect(() => {
    setAuthHandlers({
      onSessionEnded: () => endSession("You were signed out. Log in again."),
      onMustChangePin: () => {
        void reloadProfile().catch(() => undefined);
      },
    });
  }, [endSession, reloadProfile]);

  const boot = useCallback(async () => {
    if (!tokenStore.getRefresh()) {
      setStatus("anonymous");
      return;
    }
    setStatus("booting");
    try {
      const p = await reloadProfile();
      if (!p) setStatus("anonymous");
    } catch {
      setStatus("unreachable");
    }
  }, [reloadProfile]);

  useEffect(() => {
    void boot();
  }, [boot]);

  const login = useCallback(async (input: authService.LoginInput) => {
    const res = await authService.login(input);
    setProfile(res.officer);
    setStatus("authenticated");
    setNotice(null);
    return res.officer;
  }, []);

  const logout = useCallback(async () => {
    const refreshToken = tokenStore.getRefresh();
    endSession(null); // clear first so the UI reacts at once
    if (refreshToken) {
      try {
        await authApi.logout(refreshToken);
      } catch {
        /* logout is best effort: the token is already forgotten locally */
      }
    }
  }, [endSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      profile,
      notice,
      login,
      logout,
      reloadProfile,
      retryBoot: () => void boot(),
      dismissNotice: () => setNotice(null),
    }),
    [status, profile, notice, login, logout, reloadProfile, boot],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>.");
  return ctx;
}

/** For screens behind RequireAuth, where a profile is guaranteed. */
export function useOfficer(): OfficerProfile {
  const { profile } = useAuth();
  if (!profile) throw new Error("useOfficer used outside an authenticated route.");
  return profile;
}
