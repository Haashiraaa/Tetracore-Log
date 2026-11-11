// frontend/src/exceptions/errors.ts
// Mirrors backend/src/exceptions/errors.py. Application logic switches on
// `code` (the backend's detail.code), never on the HTTP status.

export const ErrorCode = {
  // from the backend
  InvalidCredentials: "invalid_credentials",
  AccountLocked: "account_locked",
  TokenExpired: "token_expired",
  InvalidToken: "invalid_token",
  SessionRevoked: "session_revoked",
  Forbidden: "forbidden",
  MustChangePin: "must_change_pin",
  WeakPin: "weak_pin",
  NotFound: "not_found",
  Conflict: "conflict",
  TruckAlreadyInside: "truck_already_inside",
  InvalidSignature: "invalid_signature",
  // raised by this app
  Network: "network_error",
  Validation: "validation_error",
  Http: "http_error",
  Server: "server_error",
} as const;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryAfterSeconds?: number;

  constructor(status: number, code: string, message: string, retryAfterSeconds?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError;
}

export function hasCode(e: unknown, ...codes: string[]): e is ApiError {
  return isApiError(e) && codes.includes(e.code);
}

/** Text safe to show to a guard. */
export function errorMessage(e: unknown): string {
  if (!isApiError(e)) return "Something went wrong. Try again.";
  switch (e.code) {
    case ErrorCode.AccountLocked: {
      const minutes = Math.max(1, Math.ceil((e.retryAfterSeconds ?? 60) / 60));
      return `Too many failed attempts. Try again in ${minutes} minute${minutes === 1 ? "" : "s"}.`;
    }
    case ErrorCode.Network:
      return "Can't reach the server. Check the connection and try again.";
    case ErrorCode.Server:
      return "The server hit an error. Try again, and tell the admin if it keeps happening.";
    case ErrorCode.Forbidden:
      return e.message || "You don't have permission to do that.";
    default:
      return e.message;
  }
}
