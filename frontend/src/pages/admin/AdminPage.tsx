// frontend/src/pages/admin/AdminPage.tsx  (backend: api/routes/admin.py)
import { useState } from "react";
import * as adminApi from "@/api/admin";
import { Banner } from "@/components/ui/Banner";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { errorMessage } from "@/exceptions/errors";
import { useAsync } from "@/hooks/useAsync";
import { FacilitiesPanel } from "./FacilitiesPanel";
import { OfficersPanel } from "./OfficersPanel";

type Tab = "officers" | "facilities";

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("officers");
  const facilities = useAsync((signal) => adminApi.listFacilities(signal), []);

  return (
    <div className="page stack stack--lg">
      <PageHeader title="Admin" subtitle="Facilities and the people who log at them." />

      <div className="segmented" role="tablist" aria-label="Admin sections">
        {(["officers", "facilities"] as const).map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            className="segmented__tab"
            onClick={() => setTab(t)}
          >
            {t === "officers" ? "Officers" : "Facilities"}
          </button>
        ))}
      </div>

      {facilities.error !== null && <Banner tone="error">{errorMessage(facilities.error)}</Banner>}
      {facilities.loading && facilities.data === null && <Spinner />}

      {facilities.data !== null && (
        <div role="tabpanel">
          {tab === "officers" ? (
            <OfficersPanel facilities={facilities.data} />
          ) : (
            <FacilitiesPanel facilities={facilities.data} onChanged={facilities.reload} />
          )}
        </div>
      )}
    </div>
  );
}
