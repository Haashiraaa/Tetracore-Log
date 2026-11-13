// frontend/src/hooks/useSignature.ts
// Load the signature image of one entry. The signature endpoint needs the bearer header,
// so a plain <img src> can't load it: fetch it as a blob and point the image at an object URL.
import { useEffect, useState } from "react";
import { getSignature } from "@/api/entries";
import type { SignatureSide } from "@/api/schemas";
import { ErrorCode, errorMessage, hasCode } from "@/exceptions/errors";
import type { LogKind } from "@/models";

export type SigState =
  | { kind: "none" }
  | { kind: "loading" }
  | { kind: "ready"; url: string }
  | { kind: "error"; message: string };

export function useSignature(kind: LogKind, entryId: string, has: boolean, side: SignatureSide): SigState {
  const [state, setState] = useState<SigState>(has ? { kind: "loading" } : { kind: "none" });

  useEffect(() => {
    if (!has) {
      setState({ kind: "none" });
      return;
    }
    let objectUrl: string | null = null;
    let cancelled = false;
    setState({ kind: "loading" });
    getSignature(kind, entryId, side)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setState({ kind: "ready", url: objectUrl });
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setState(
          hasCode(e, ErrorCode.NotFound) ? { kind: "none" } : { kind: "error", message: errorMessage(e) },
        );
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [kind, entryId, has, side]);

  return state;
}
