// frontend/src/lib/pin.ts
// Mirrors validate_pin_policy in backend/src/security/passwords.py. The server
// is the authority (weak_pin); this only saves a round trip.

import { PIN_MAX_LENGTH, PIN_MIN_LENGTH } from "@/config/env";

export function pinPolicyError(pin: string): string | null {
  if (!/^[0-9]+$/.test(pin)) return "PIN must contain digits only.";
  if (pin.length < PIN_MIN_LENGTH || pin.length > PIN_MAX_LENGTH) {
    return `PIN must be ${PIN_MIN_LENGTH}-${PIN_MAX_LENGTH} digits long.`;
  }
  if (new Set(pin).size === 1) return "PIN cannot be a single repeated digit.";
  const digits = [...pin].map(Number);
  const steps = new Set(digits.slice(1).map((d, i) => d - digits[i]));
  if (steps.size === 1 && (steps.has(1) || steps.has(-1))) {
    return "PIN cannot be a straight run like 123456.";
  }
  return null;
}
