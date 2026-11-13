// frontend/src/lib/theme.ts
// Day or night. "auto" follows the clock in Lagos, because gates run through the night
// and a white screen in the dark is hard on the eyes.
import { NIGHT_ENDS_HOUR, NIGHT_STARTS_HOUR } from "@/config/env";
import { lagosHour } from "./dates";

export type ThemeChoice = "auto" | "day" | "night";
export type Theme = "day" | "night";

export const THEME_CHOICES: { value: ThemeChoice; label: string }[] = [
  { value: "auto", label: "Auto" },
  { value: "day", label: "Day" },
  { value: "night", label: "Night" },
];

const THEME_KEY = "log-book.theme";

export function readThemeChoice(): ThemeChoice {
  try {
    const saved = window.localStorage.getItem(THEME_KEY);
    return saved === "day" || saved === "night" ? saved : "auto";
  } catch {
    return "auto";
  }
}

export function saveThemeChoice(choice: ThemeChoice): void {
  try {
    if (choice === "auto") window.localStorage.removeItem(THEME_KEY);
    else window.localStorage.setItem(THEME_KEY, choice);
  } catch {
    /* storage blocked: the choice lasts until the page is reloaded */
  }
}

export function themeFor(choice: ThemeChoice, at: Date = new Date()): Theme {
  if (choice !== "auto") return choice;
  const hour = lagosHour(at);
  return hour >= NIGHT_STARTS_HOUR || hour < NIGHT_ENDS_HOUR ? "night" : "day";
}

/** Puts the theme on <html>, where tokens.css picks it up. */
export function applyTheme(choice: ThemeChoice = readThemeChoice()): void {
  document.documentElement.dataset.theme = themeFor(choice);
}
