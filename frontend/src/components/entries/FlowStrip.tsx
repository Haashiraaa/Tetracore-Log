// frontend/src/components/entries/FlowStrip.tsx
// A truck's path at a glance: queued outside, on site, gone. The numbers roll as trucks move.
import { RollingNumber } from "@/components/ui/RollingNumber";

export function FlowStrip({ queued, onSite, leftToday }: { queued: number; onSite: number; leftToday: number | null }) {
  return (
    <dl className="strip flow" aria-label="Where the trucks are">
      <div className="strip__cell">
        <dt>Queued</dt>
        <dd>
          <RollingNumber value={queued} />
        </dd>
      </div>
      <div className="strip__cell strip__cell--key">
        <dt>On site</dt>
        <dd>
          <RollingNumber value={onSite} />
        </dd>
      </div>
      <div className="strip__cell">
        <dt>Left today</dt>
        <dd>
          <RollingNumber value={leftToday} />
        </dd>
      </div>
    </dl>
  );
}
