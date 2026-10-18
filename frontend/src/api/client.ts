// frontend/src/api/client.ts
// Authenticated requests. Counterpart of backend/src/api/deps.py.
//
//   token_expired / invalid_token  -> refresh once, retry once (single-flight)
//   session_revoked                -> the session is dead: sign out locally
//   must_change_pin                -> tell the app so it can route to /change-pin
//   anything else (incl. invalid_credentials from change-pin) is just an error
//   for the caller. A wrong current PIN must NOT log the guard out.

import { ErrorCode, hasCode, isApiError, ApiError } from "@/exceptions/errors";
import { tokenStore } from "@/security/tokenStore";
import { requestBlob, requestJson, type RequestOptions } from "./http";
import type { RefreshResponse } from "./schemas";

export interface AuthHandlers {
  onSessionEnded(): void;
  onMustChangePin(): void;
}

let handlers: AuthHandlers = { onSessionEnded() {}, onMustChangePin() {} };

export function setAuthHandlers(next: AuthHandlers): void {
  handlers = next;
}

let inflightRefresh: Promise<boolean> | null = null;

/** true = new access token stored, false = refresh token rejected. Throws on network/5xx. */
async function doRefresh(): Promise<boolean> {
  const refreshToken = tokenStore.getRefresh();
  if (!refreshToken) return false;
  try {
    const res = await requestJson<RefreshResponse>("/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
    });
    tokenStore.setAccess(res.access_token);
    return true;
  } catch (e) {
    if (isApiError(e) && (e.code === ErrorCode.Network || e.status >= 500)) throw e;
    return false;
  }
}

function refreshAccess(): Promise<boolean> {
  if (!inflightRefresh) {
    inflightRefresh = doRefresh().finally(() => {
      inflightRefresh = null;
    });
  }
  return inflightRefresh;
}

function endSession(): never {
  tokenStore.clear();
  handlers.onSessionEnded();
  throw new ApiError(401, ErrorCode.SessionRevoked, "Your session ended. Log in again.");
}

async function withAuth<T>(send: (bearer: string) => Promise<T>): Promise<T> {
  if (!tokenStore.getAccess() && !(await refreshAccess())) return endSession();

  for (let attempt = 0; ; attempt++) {
    try {
      return await send(`Bearer ${tokenStore.getAccess()}`);
    } catch (e) {
      if (attempt === 0 && hasCode(e, ErrorCode.TokenExpired, ErrorCode.InvalidToken)) {
        if (await refreshAccess()) continue;
        return endSession();
      }
      if (hasCode(e, ErrorCode.SessionRevoked)) {
        tokenStore.clear();
        handlers.onSessionEnded();
      } else if (hasCode(e, ErrorCode.MustChangePin)) {
        handlers.onMustChangePin();
      }
      throw e;
    }
  }
}

export function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  return withAuth((bearer) =>
    requestJson<T>(path, { ...opts, headers: { ...opts.headers, Authorization: bearer } }),
  );
}

/** For endpoints that need the bearer header but return an image (signatures). */
export function requestAuthedBlob(path: string, opts: RequestOptions = {}): Promise<Blob> {
  return withAuth((bearer) =>
    requestBlob(path, { ...opts, headers: { ...opts.headers, Authorization: bearer } }),
  );
}
