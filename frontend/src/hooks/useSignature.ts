// frontend/src/hooks/useSignature.ts
// Load the signature image of one entry. The signature endpoint needs the bearer header,
// so a plain <img src> can't load it: fetch it as a blob and point the image at an object URL.
import { useEffect, useState } from "react";
import { getSignature } from "@/api/entries";
import * as occurrencesApi from "@/api/occurrences";
import type { SignatureSide } from "@/api/schemas";
import { ErrorCode, errorMessage, hasCode } from "@/exceptions/errors";
import type { LogKind } from "@/models";

export type SigState =
  | { kind: "none" }
  | { kind: "loading" }
  | { kind: "ready"; url: string }
  | { kind: "error"; message: string };

export function useSignature(kind: LogKind, entryId: string, has: boolean, side: SignatureSide): SigState {
  return useSignatureImage(() => getSignature(kind, entryId, side), `${kind}/${entryId}/${side}`, has);
}

/** The officer's signature on one Events log note. */
export function useNoteSignature(noteId: string, has: boolean): SigState {
  return useSignatureImage(() => occurrencesApi.getSignature(noteId), `note/${noteId}`, has);
}

/** `key` says which image this is: a new key loads a new one. */
function useSignatureImage(load: () => Promise<Blob>, key: string, has: boolean): SigState {
  const [state, setState] = useState<SigState>(has ? { kind: "loading" } : { kind: "none" });

  useEffect(() => {
    if (!has) {
      setState({ kind: "none" });
      return;
    }
    let objectUrl: string | null = null;
    let cancelled = false;
    setState({ kind: "loading" });
    load()
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, has]);

  return state;
}
