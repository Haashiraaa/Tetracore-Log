// frontend/src/components/ui/Banner.tsx
import type { ReactNode } from "react";
import { cx } from "@/lib/cx";

export type Tone = "info" | "warn" | "error" | "success";

export function Banner({
  tone = "info",
  title,
  children,
  className,
}: {
  tone?: Tone;
  title?: string;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cx("banner", `banner--${tone}`, className)} role={tone === "error" ? "alert" : "status"}>
      {title && <strong className="banner__title">{title}</strong>}
      {children && <div className="banner__text">{children}</div>}
    </div>
  );
}
