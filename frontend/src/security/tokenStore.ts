// frontend/src/security/tokenStore.ts
// The short-lived access token lives only in memory. The long-lived refresh
// token is kept in localStorage so a guard stays logged in across reloads.
// (V1 trade-off: localStorage is readable by any script on the page. There is
// no third-party script here; revisit with httpOnly cookies if that changes.)

const REFRESH_KEY = "log-book.refresh_token";
const OLD_REFRESH_KEY = "tetracore-log.refresh_token"; // the app's name before the rename

// Carry a saved login over from the old key once, so the rename signs nobody out.
try {
  const old = window.localStorage.getItem(OLD_REFRESH_KEY);
  if (old !== null) {
    if (window.localStorage.getItem(REFRESH_KEY) === null) window.localStorage.setItem(REFRESH_KEY, old);
    window.localStorage.removeItem(OLD_REFRESH_KEY);
  }
} catch {
  /* storage blocked: nothing to carry over */
}

let accessToken: string | null = null;
let refreshFallback: string | null = null; // used if storage is blocked

function readRefresh(): string | null {
  try {
    return window.localStorage.getItem(REFRESH_KEY) ?? refreshFallback;
  } catch {
    return refreshFallback;
  }
}

function writeRefresh(token: string | null): void {
  refreshFallback = token;
  try {
    if (token === null) window.localStorage.removeItem(REFRESH_KEY);
    else window.localStorage.setItem(REFRESH_KEY, token);
  } catch {
    /* storage blocked: in-memory fallback only */
  }
}

export const tokenStore = {
  getAccess: (): string | null => accessToken,
  setAccess: (token: string | null): void => {
    accessToken = token;
  },
  getRefresh: readRefresh,
  setRefresh: writeRefresh,
  clear: (): void => {
    accessToken = null;
    writeRefresh(null);
  },
};
