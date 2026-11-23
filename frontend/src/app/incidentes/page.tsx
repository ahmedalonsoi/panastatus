"use client";

import useSWR from "swr";

import { IncidentList } from "@/components/IncidentList";
import type { Incident } from "@/lib/api";
import { fetcher } from "@/lib/api";

export default function IncidentsPage() {
  const { data, error } = useSWR<Incident[]>("/api/incidents?limit=100", fetcher, {
    refreshInterval: 60_000,
  });

  return (
    <>
      <h1 className="mt-6 text-xl font-semibold">Historial de incidentes</h1>
      <p className="text-sm text-muted">
        Un incidente se abre tras 2 revisiones fallidas seguidas y se cierra cuando el servicio
        responde de nuevo. Los incidentes largos incluyen un análisis revisado por una persona.
      </p>
      <div className="mt-4 rounded-xl border border-line bg-surface px-4">
        {error ? (
          <p className="py-3 text-sm text-muted">No se pudo cargar el historial.</p>
        ) : data ? (
          <IncidentList incidents={data} />
        ) : (
          <p className="py-3 text-sm text-muted">Cargando…</p>
        )}
      </div>
    </>
  );
}
