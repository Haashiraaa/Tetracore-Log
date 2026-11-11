// frontend/src/api/auth.ts  (backend: api/routes/auth.py)

import { request } from "./client";
import { requestJson } from "./http";
import type { LoginRequest, LoginResponse, OfficerProfile } from "./schemas";

export function login(body: LoginRequest): Promise<LoginResponse> {
  return requestJson<LoginResponse>("/auth/login", { method: "POST", body });
}

/** Takes the REFRESH token so a guard can still log out after the access token expired. */
export function logout(refreshToken: string): Promise<void> {
  return requestJson<void>("/auth/logout", {
    method: "POST",
    body: { refresh_token: refreshToken },
  });
}

export function me(): Promise<OfficerProfile> {
  return request<OfficerProfile>("/auth/me");
}

export function changePin(currentPin: string, newPin: string): Promise<void> {
  return request<void>("/auth/change-pin", {
    method: "POST",
    body: { current_pin: currentPin, new_pin: newPin },
  });
}
