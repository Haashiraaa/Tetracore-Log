// frontend/src/components/ui/Badge.tsx
import type { ReactNode } from "react";
import { cx } from "@/lib/cx";

export function Badge({
  tone = "grey",
  children,
}: {
  tone?: "grey" | "blue" | "amber" | "green" | "red" | "ink";
  children: ReactNode;
}) {
  return <span className={cx("badge", `badge--${tone}`)}>{children}</span>;
}
