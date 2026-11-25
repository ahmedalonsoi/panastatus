"use client";

import useSWR from "swr";

import { IncidentList } from "@/components/IncidentList";
import type { Incident } from "@/lib/api";
import { fetcher } from "@/lib/api";
import { duration } from "@/lib/format";

export default function IncidentsPage() {
  const { data, error } = useSWR<Incident[]>("/api/incidents?limit=100", fetcher, {
    refreshInterval: 60_000,
  });

  const resolved = data?.filter((i) => i.resolved_at) ?? [];
  const mttr = resolved.length
    ? resolved.reduce((sum, i) => sum + i.duration_seconds, 0) / resolved.length
    : null;

  return (
    <>
      <h1 className="text-2xl font-semibold">Historial de incidentes</h1>
      <p className="mt-1 max-w-2xl text-sm text-muted">
        Un incidente se abre tras 2 revisiones fallidas seguidas y se cierra cuando el servicio
        responde de nuevo. Los incidentes de 15 minutos o más pueden incluir un análisis
        (post-mortem) redactado con IA y aprobado por una persona antes de publicarse.
      </p>

      {data && data.length > 0 && (
        <dl className="mt-5 grid grid-cols-3 gap-3">
          {[
            ["Incidentes", String(data.length)],
            ["En curso", String(data.length - resolved.length)],
            ["Tiempo medio de recuperación", mttr != null ? duration(Math.round(mttr)) : "—"],
          ].map(([k, v]) => (
            <div key={k} className="rounded-xl border border-line bg-surface p-3.5">
              <dt className="text-xs font-medium text-muted">{k}</dt>
              <dd className="mt-1 text-lg font-semibold text-ink tabular-nums">{v}</dd>
            </div>
          ))}
        </dl>
      )}

      <div className="mt-5 rounded-2xl border border-line bg-surface px-4">
        {error ? (
          <p className="py-4 text-sm text-muted">No se pudo cargar el historial.</p>
        ) : data ? (
          <IncidentList incidents={data} />
        ) : (
          <div className="my-4 h-10 animate-pulse rounded bg-empty" aria-label="Cargando" />
        )}
      </div>
    </>
  );
}
