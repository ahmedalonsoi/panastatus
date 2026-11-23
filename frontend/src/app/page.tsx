"use client";

import Link from "next/link";
import useSWR from "swr";

import { IncidentList } from "@/components/IncidentList";
import { ServiceRow } from "@/components/ServiceRow";
import type { DailyPoint, Incident, Overall, Service, Summary } from "@/lib/api";
import { fetcher } from "@/lib/api";
import { OVERALL_LABEL, dateTime } from "@/lib/format";

// La página se refresca sola cada 60 s (SWR también refresca al volver a la pestaña).
const REFRESH = { refreshInterval: 60_000 };

const BANNER_CLASS: Record<Overall | "loading", string> = {
  operational: "bg-status-up text-white",
  degraded: "bg-status-degraded text-black",
  outage: "bg-status-down text-white",
  loading: "bg-status-unknown text-white",
};

export default function StatusPage() {
  const summary = useSWR<Summary>("/api/summary", fetcher, REFRESH);
  const services = useSWR<Service[]>("/api/services", fetcher, REFRESH);
  const daily = useSWR<Record<string, DailyPoint[]>>("/api/uptime/daily?days=90", fetcher, REFRESH);
  const incidents = useSWR<Incident[]>("/api/incidents?limit=5", fetcher, REFRESH);

  const error = summary.error || services.error || daily.error;
  const overall = summary.data?.overall;

  // Agrupar por categoría conservando el orden de la API.
  const groups = new Map<string, Service[]>();
  for (const s of services.data ?? []) {
    groups.set(s.category_label, [...(groups.get(s.category_label) ?? []), s]);
  }

  return (
    <>
      <p className="mt-1 text-sm text-muted" aria-live="polite">
        {error
          ? "No se pudo actualizar. Reintentando…"
          : summary.data?.last_checked_at
            ? `Última revisión: ${dateTime(summary.data.last_checked_at)}`
            : "Cargando…"}
      </p>

      <div
        role="status"
        className={`mt-5 mb-7 rounded-xl px-5 py-4 text-lg font-semibold ${BANNER_CLASS[overall ?? "loading"]}`}
      >
        {overall ? OVERALL_LABEL[overall] : "Consultando servicios…"}
      </div>

      {[...groups].map(([label, list]) => (
        <section key={label} className="mb-5 rounded-xl border border-line bg-surface">
          <h2 className="border-b border-line px-4 py-3 text-base font-semibold">{label}</h2>
          {list.map((s) => (
            <ServiceRow key={s.id} service={s} daily={daily.data?.[s.id] ?? []} />
          ))}
        </section>
      ))}

      <h2 className="mt-9 mb-2 text-lg font-semibold">Incidentes recientes</h2>
      <div className="rounded-xl border border-line bg-surface px-4">
        {incidents.data ? (
          <IncidentList incidents={incidents.data} />
        ) : (
          <p className="py-3 text-sm text-muted">Cargando…</p>
        )}
      </div>
      <p className="mt-2 text-sm">
        <Link href="/incidentes/">Ver historial completo →</Link>
      </p>
    </>
  );
}
