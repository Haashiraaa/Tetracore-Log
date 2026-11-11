// frontend/src/lib/people.ts
// How a person is written down. Mirrors clean_full_name and clean_phone in
// backend/src/models.py: the same name or number must come out the same on both sides.

/** Spaces tidied. */
export function cleanFullName(raw: string): string {
  return raw.trim().split(/\s+/).filter(Boolean).join(" ");
}

/** A full name is at least two words: first name and last name. */
export function isFullName(raw: string): boolean {
  return cleanFullName(raw).split(" ").filter(Boolean).length >= 2;
}

/** One form for a phone number: digits only, +234 / 234 written as a leading 0. Null if it is no phone. */
export function cleanPhone(raw: string): string | null {
  let digits = raw.replace(/\D/g, "");
  if (digits.startsWith("234") && digits.length === 13) digits = `0${digits.slice(3)}`;
  return digits.length >= 7 && digits.length <= 15 ? digits : null;
}

export const PHONE_ERROR = "Enter a valid phone number, for example 0803 123 4567.";

export function fullNameError(raw: string, whose = "their"): string | null {
  return isFullName(raw) ? null : `Enter ${whose} full name: first name and last name.`;
}
