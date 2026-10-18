// frontend/src/components/signature/SignaturePad.tsx
// Draw-to-sign canvas. Strokes are stored normalised (0..1), so the pad survives
// resizes and rotation, and the exported PNG is rendered at a fixed small size to
// stay far below the backend's 200 KB limit.
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { cx } from "@/lib/cx";

type Point = readonly [number, number];

export interface SignaturePadHandle {
  clear(): void;
  isEmpty(): boolean;
  /** PNG data URL no larger than maxBytes, or null if empty. */
  toPng(maxBytes: number): string | null;
}

interface SignaturePadProps {
  onInkChange?: (hasInk: boolean) => void;
  disabled?: boolean;
  invalid?: boolean;
}

const INK = "#0b1d2c";
const LINE_WIDTH = 2.6; // CSS px at on-screen size

const clamp01 = (n: number) => Math.min(1, Math.max(0, n));

function paint(
  ctx: CanvasRenderingContext2D,
  strokes: Point[][],
  w: number,
  h: number,
  lineWidth: number,
): void {
  ctx.save();
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = INK;
  ctx.fillStyle = INK;
  ctx.lineWidth = lineWidth;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (const s of strokes) {
    if (s.length === 1) {
      ctx.beginPath();
      ctx.arc(s[0][0] * w, s[0][1] * h, lineWidth / 2, 0, Math.PI * 2);
      ctx.fill();
      continue;
    }
    ctx.beginPath();
    ctx.moveTo(s[0][0] * w, s[0][1] * h);
    for (let i = 1; i < s.length; i++) ctx.lineTo(s[i][0] * w, s[i][1] * h);
    ctx.stroke();
  }
  ctx.restore();
}

export const SignaturePad = forwardRef<SignaturePadHandle, SignaturePadProps>(function SignaturePad(
  { onInkChange, disabled, invalid },
  ref,
) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const strokes = useRef<Point[][]>([]);
  const active = useRef<Point[] | null>(null);
  const [hasInk, setHasInk] = useState(false);

  const redraw = useCallback(() => {
    const c = canvasRef.current;
    const ctx = c?.getContext("2d");
    if (!c || !ctx) return;
    ctx.setTransform(window.devicePixelRatio || 1, 0, 0, window.devicePixelRatio || 1, 0, 0);
    paint(ctx, strokes.current, c.clientWidth, c.clientHeight, LINE_WIDTH);
  }, []);

  const fit = useCallback(() => {
    const c = canvasRef.current;
    if (!c || !c.clientWidth || !c.clientHeight) return;
    const dpr = window.devicePixelRatio || 1;
    const tw = Math.round(c.clientWidth * dpr);
    const th = Math.round(c.clientHeight * dpr);
    if (c.width !== tw || c.height !== th) {
      c.width = tw;
      c.height = th;
    }
    redraw();
  }, [redraw]);

  useEffect(() => {
    fit();
    const ro = new ResizeObserver(() => fit());
    if (wrapRef.current) ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, [fit]);

  const clear = useCallback(() => {
    strokes.current = [];
    active.current = null;
    setHasInk(false);
    onInkChange?.(false);
    redraw();
  }, [onInkChange, redraw]);

  useImperativeHandle(
    ref,
    () => ({
      clear,
      isEmpty: () => strokes.current.length === 0,
      toPng(maxBytes) {
        const c = canvasRef.current;
        if (!c || strokes.current.length === 0 || !c.clientWidth) return null;
        const ratio = c.clientHeight / c.clientWidth;
        // Try a few widths; sparse pen strokes on white compress to a few KB.
        for (const width of [640, 480, 320, 240]) {
          const out = document.createElement("canvas");
          out.width = width;
          out.height = Math.max(1, Math.round(width * ratio));
          const ctx = out.getContext("2d");
          if (!ctx) return null;
          paint(ctx, strokes.current, out.width, out.height, Math.max(2, (LINE_WIDTH * width) / c.clientWidth));
          const url = out.toDataURL("image/png");
          const bytes = Math.floor(((url.length - url.indexOf(",") - 1) * 3) / 4);
          if (bytes <= maxBytes) return url;
        }
        return null;
      },
    }),
    [clear],
  );

  function pointOf(e: ReactPointerEvent<HTMLCanvasElement>): Point {
    const r = e.currentTarget.getBoundingClientRect();
    return [clamp01((e.clientX - r.left) / r.width), clamp01((e.clientY - r.top) / r.height)];
  }

  function onPointerDown(e: ReactPointerEvent<HTMLCanvasElement>) {
    if (disabled) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    const stroke: Point[] = [pointOf(e)];
    active.current = stroke;
    strokes.current.push(stroke);
    if (!hasInk) {
      setHasInk(true);
      onInkChange?.(true);
    }
    redraw();
  }

  function onPointerMove(e: ReactPointerEvent<HTMLCanvasElement>) {
    const stroke = active.current;
    if (!stroke) return;
    const c = e.currentTarget;
    const ctx = c.getContext("2d");
    const prev = stroke[stroke.length - 1];
    const next = pointOf(e);
    stroke.push(next);
    if (!ctx) return;
    const w = c.clientWidth;
    const h = c.clientHeight;
    ctx.save();
    ctx.setTransform(window.devicePixelRatio || 1, 0, 0, window.devicePixelRatio || 1, 0, 0);
    ctx.strokeStyle = INK;
    ctx.lineWidth = LINE_WIDTH;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(prev[0] * w, prev[1] * h);
    ctx.lineTo(next[0] * w, next[1] * h);
    ctx.stroke();
    ctx.restore();
  }

  function endStroke() {
    active.current = null;
  }

  return (
    <div
      ref={wrapRef}
      className={cx("sig", invalid && "sig--invalid", disabled && "sig--disabled")}
    >
      <canvas
        ref={canvasRef}
        className="sig__canvas"
        role="img"
        aria-label="Signature area. Sign with a finger or the mouse."
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endStroke}
        onPointerCancel={endStroke}
      />
      {!hasInk && (
        <span className="sig__hint" aria-hidden="true">
          Driver signs here
        </span>
      )}
      <button
        type="button"
        className="btn btn--ghost btn--sm sig__clear"
        onClick={clear}
        disabled={disabled || !hasInk}
      >
        Clear
      </button>
    </div>
  );
});
