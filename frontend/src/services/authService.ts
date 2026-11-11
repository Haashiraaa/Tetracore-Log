// frontend/src/services/authService.ts
// Rules around signing in and PINs. api/* stays HTTP-only; this adds the rules.

import * as authApi from "@/api/auth";
import type { LoginResponse } from "@/api/schemas";
import { pinPolicyError } from "@/lib/pin";
import { tokenStore } from "@/security/tokenStore";

export interface LoginInput {
  facilityCode: string;
  officerCode: string;
  pin: string;
}

export type FieldErrors<K extends string> = Partial<Record<K, string>>;

export function validateLogin(input: LoginInput): FieldErrors<"officerCode" | "pin"> {
  const errors: FieldErrors<"officerCode" | "pin"> = {};
  if (!input.officerCode.trim()) errors.officerCode = "Enter your officer code.";
  if (!input.pin) errors.pin = "Enter your PIN.";
  return errors;
}

function deviceLabel(): string {
  return `Web browser (${navigator.platform || "unknown"})`.slice(0, 120);
}

export async function login(input: LoginInput): Promise<LoginResponse> {
  const res = await authApi.login({
    // blank facility = a global account (CSO or admin with no facility)
    facility_code: input.facilityCode.trim() || null,
    officer_code: input.officerCode.trim(),
    pin: input.pin,
    device_label: deviceLabel(),
  });
  tokenStore.setAccess(res.access_token);
  tokenStore.setRefresh(res.refresh_token);
  return res;
}

export function validateNewPin(
  current: string,
  next: string,
  confirm: string,
): FieldErrors<"current" | "next" | "confirm"> {
  const errors: FieldErrors<"current" | "next" | "confirm"> = {};
  if (!current) errors.current = "Enter your current PIN.";
  const policy = pinPolicyError(next);
  if (policy) errors.next = policy;
  else if (next === current) errors.next = "New PIN must be different from the current one.";
  if (confirm !== next) errors.confirm = "The two PINs don't match.";
  return errors;
}

export function changePin(current: string, next: string): Promise<void> {
  return authApi.changePin(current, next);
}
