// frontend/src/lib/people.ts
// How a person is written down. Mirrors clean_full_name and clean_phone in
// backend/src/models.py: the same name or number must come out the same on both sides.
import { parsePhoneNumberFromString } from "libphonenumber-js/max";
import { DEFAULT_PHONE_REGION } from "@/config/env";

/** Spaces tidied. */
export function cleanFullName(raw: string): string {
  return raw.trim().split(/\s+/).filter(Boolean).join(" ");
}

/** A full name is at least two words: first name and last name. */
export function isFullName(raw: string): boolean {
  return cleanFullName(raw).split(" ").filter(Boolean).length >= 2;
}

export const PHONE_ERROR =
  "Enter a valid phone number. A Nigerian number looks like 0803 123 4567. For another country start with + and the country code, for example +44 7911 123456.";

/** One form for a phone number: E.164, "+" then the country code then the number
 *  (+2348031112222). A number without a country code is read as Nigerian; one that starts with
 *  + is read as that country's. Null unless it is a REAL number for that country (the right
 *  length and a prefix the country uses). Mirrors clean_phone in backend/src/models.py. */
export function cleanPhone(raw: string): string | null {
  const text = raw.trim();
  if (!text || /[a-z]/i.test(text)) return null; // letters: extensions, vanity numbers
  const parsed = parsePhoneNumberFromString(text, DEFAULT_PHONE_REGION);
  return parsed && parsed.isValid() && !parsed.ext ? parsed.number : null;
}

/** A stored number as people read it: "+234 803 111 2222". Anything that is not a number is returned as it is. */
export function formatPhone(stored: string | null | undefined): string {
  if (!stored) return "";
  const parsed = parsePhoneNumberFromString(stored);
  return parsed ? parsed.formatInternational() : stored;
}

/** Every way someone might type a stored number into a search box: +2348031112222,
 *  0803 111 2222, 08031112222. */
export function phoneSearchText(stored: string | null | undefined): string {
  if (!stored) return "";
  const parsed = parsePhoneNumberFromString(stored);
  if (!parsed) return stored;
  const national = parsed.formatNational();
  return `${parsed.number} ${national} ${national.replace(/\D/g, "")}`;
}

/** How many digits must be typed before we search, same as the API. */
export const PHONE_SEARCH_MIN = 3;

/** The digits typed so far, or null if too few to search. The server drops a leading 0 or 00
 *  (see phone_search_digits in backend/src/models.py), so a typed "0803" finds +234 803... */
export function phoneSearchDigits(raw: string): string | null {
  const digits = raw.replace(/\D/g, "");
  return digits.length >= PHONE_SEARCH_MIN ? digits : null;
}

export function fullNameError(raw: string, whose = "their"): string | null {
  return isFullName(raw) ? null : `Enter ${whose} full name: first name and last name.`;
}
