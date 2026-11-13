// frontend/src/components/ui/RollingNumber.tsx
import { useState } from "react";
import { cx } from "@/lib/cx";

/** A number that rolls up or down when it changes, so a change is seen and not just read. */
export function RollingNumber({ value }: { value: number | null }) {
  const [shown, setShown] = useState(value);
  const [direction, setDirection] = useState<"up" | "down" | null>(null);
  if (value !== shown) {
    setDirection(value !== null && shown !== null ? (value > shown ? "up" : "down") : null);
    setShown(value);
  }
  return (
    <span key={value ?? "none"} className={cx("roll", direction && `roll--${direction}`)}>
      {value ?? "–"}
    </span>
  );
}
