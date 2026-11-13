// frontend/src/pages/events/EventsPage.tsx
// The Events log: an officer's own notes, "this is what I noticed". Everyone can read it
// (the server scopes it to a facility). Accounts that belong to a facility and are on duty
// get the form. The time, the officer's name and the gate are filled in by the server; the
// signature is the one from going on duty, so nobody signs each note. An officer who never
// signed on duty draws one on the note.
// `noteId` is made once per note and reused on retry, so a lost reply cannot save it twice.
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import * as occurrencesApi from "@/api/occurrences";
import type { OccurrenceEntry } from "@/api/schemas";
import { useOfficer } from "@/auth/AuthContext";
import { canWriteEntries, seesAllFacilities } from "@/auth/permissions";
import { useDuty } from "@/components/duty/DutyContext";
import { SignaturePad, readPad, type SignaturePadHandle } from "@/components/signature/SignaturePad";
import { Badge } from "@/components/ui/Badge";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { NOTE_MAX_LENGTH, NOTE_MIN_LENGTH, PAGE_SIZE, SIGNATURE_MAX_BYTES } from "@/config/env";
import { errorMessage } from "@/exceptions/errors";
import { useNoteSignature } from "@/hooks/useSignature";
import { formatDateTime } from "@/lib/dates";
import { deviceId, uuid } from "@/lib/ids";

function NoteSignature({ note }: { note: OccurrenceEntry }) {
  const sig = useNoteSignature(note.id, note.has_signature);
  return (
    <div className="sig-slot">
      {sig.kind === "loading" && <Spinner label="Loading signature" />}
      {sig.kind === "ready" && <img className="sig-view" src={sig.url} alt={`Signature of ${note.officer_name}`} />}
      {sig.kind === "none" && <p className="sig-slot__none">No signature</p>}
      {sig.kind === "error" && <Banner tone="error">{sig.message}</Banner>}
    </div>
  );
}

function NoteCard({ note, showFacility }: { note: OccurrenceEntry; showFacility: boolean }) {
  return (
    <li className="card stack stack--sm event-note">
      <div className="row row--between">
        <span className="mono cell-main">{formatDateTime(note.logged_at, true)}</span>
        {showFacility && <span className="mono">{note.facility_code}</span>}
      </div>
      <p className="event-note__text">{note.note}</p>
      <div className="row row--between">
        <span className="cell-sub">
          {note.officer_name}
          {note.gate ? `, gate ${note.gate}` : ""}
        </span>
        {note.signature_reused && <Badge tone="grey">Signature on file</Badge>}
      </div>
      <NoteSignature note={note} />
    </li>
  );
}

export default function EventsPage() {
  const profile = useOfficer();
  const duty = useDuty();
  const showFacility = seesAllFacilities(profile);
  const canWrite = canWriteEntries(profile);
  const onDuty = duty?.onDuty ?? false;

  const [notes, setNotes] = useState<OccurrenceEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [text, setText] = useState("");
  const [noteId, setNoteId] = useState(uuid);
  const [hasSignature, setHasSignature] = useState<boolean | null>(null); // null = not known yet
  const [resign, setResign] = useState(false);
  const [textError, setTextError] = useState<string | null>(null);
  const [sigError, setSigError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pad = useRef<SignaturePadHandle>(null);

  async function load(offset: number) {
    setLoading(true);
    setLoadError(null);
    try {
      // one extra row tells us whether there is a next page
      const rows = await occurrencesApi.list({ limit: PAGE_SIZE + 1, offset });
      setNotes((old) => (offset === 0 ? rows.slice(0, PAGE_SIZE) : [...old, ...rows.slice(0, PAGE_SIZE)]));
      setHasMore(rows.length > PAGE_SIZE);
    } catch (e) {
      setLoadError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(0);
  }, []);

  useEffect(() => {
    if (!canWrite) return;
    occurrencesApi
      .signatureOnFile()
      .then((r) => setHasSignature(r.has_signature))
      .catch(() => setHasSignature(false)); // fall back to asking for a signature
  }, [canWrite]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const note = text.trim();
    if (note.length < NOTE_MIN_LENGTH) {
      setTextError(`Write what happened (at least ${NOTE_MIN_LENGTH} characters).`);
      return;
    }
    setTextError(null);
    const onFile = hasSignature === true && !resign;
    const read = onFile ? { png: null } : readPad(pad.current, SIGNATURE_MAX_BYTES);
    if ("error" in read || (!onFile && !read.png)) {
      setSigError("error" in read ? read.error : "Sign this event before you log it.");
      return;
    }
    setTextError(null);
    setSigError(null);
    setError(null);
    setSaved(null);
    setBusy(true);
    try {
      const made = await occurrencesApi.create({
        id: noteId,
        note,
        ...(read.png ? { signature: read.png } : {}),
        device_id: deviceId(),
      });
      setNotes((old) => [made, ...old.filter((n) => n.id !== made.id)]);
      setText("");
      setNoteId(uuid());
      setResign(false);
      setSaved("Event logged.");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page page--form stack stack--lg">
      <PageHeader title="Events" />

      {canWrite && duty && duty.status !== null && !onDuty && (
        <Banner tone="warn">
          You are off duty. <Link to="/duty">Go on duty</Link> to write an event.
        </Banner>
      )}

      {canWrite && onDuty && (
        <form className="card stack" onSubmit={submit} noValidate>
          {saved && <Banner tone="success">{saved}</Banner>}
          {error && <Banner tone="error">{error}</Banner>}
          <div className={textError ? "field field--error" : "field"}>
            <label className="field__label" htmlFor="event-note">
              What happened, or what did you notice?
            </label>
            <textarea
              id="event-note"
              className="input event-note__input"
              rows={4}
              maxLength={NOTE_MAX_LENGTH}
              value={text}
              onChange={(e) => setText(e.target.value)}
              disabled={busy}
              aria-invalid={textError ? true : undefined}
            />
            <p className="field__hint">
              The time, your name and your gate are added for you.
            </p>
            {textError && (
              <p className="field__error" role="alert">
                {textError}
              </p>
            )}
          </div>

          {hasSignature === null ? (
            <Spinner label="Checking your signature" />
          ) : hasSignature && !resign ? (
            <div className="sig-onfile">
              <span className="field__label">Your signature</span>
              <p>
                <strong>Signature on file.</strong> The one you signed when you went on duty is attached to this event.
              </p>
              <div>
                <Button variant="secondary" size="sm" onClick={() => setResign(true)} disabled={busy}>
                  Sign this event instead
                </Button>
              </div>
            </div>
          ) : (
            <div className="field">
              <span className="field__label">Sign this event</span>
              <SignaturePad ref={pad} disabled={busy} invalid={Boolean(sigError)} hint="Sign here" />
              {sigError && (
                <p className="field__error" role="alert">
                  {sigError}
                </p>
              )}
              {hasSignature && (
                <div>
                  <Button variant="ghost" size="sm" onClick={() => setResign(false)} disabled={busy}>
                    Use the signature on file
                  </Button>
                </div>
              )}
            </div>
          )}

          <div className="row">
            <Button type="submit" className="btn--lead" loading={busy}>
              Log event
            </Button>
          </div>
        </form>
      )}

      {loadError && <Banner tone="error">{loadError}</Banner>}
      {loading && notes.length === 0 && <Spinner label="Loading events" />}
      {!loading && !loadError && notes.length === 0 && (
        <EmptyState title="No events yet">Events written at the gate appear here, newest first.</EmptyState>
      )}

      {notes.length > 0 && (
        <ul className="stack event-list">
          {notes.map((n) => (
            <NoteCard key={n.id} note={n} showFacility={showFacility} />
          ))}
        </ul>
      )}

      {hasMore && (
        <div>
          <Button variant="secondary" onClick={() => void load(notes.length)} loading={loading}>
            Show older events
          </Button>
        </div>
      )}
    </div>
  );
}
