"use client";

import { useState } from "react";
import useSWR from "swr";

import type { DailyPoint, LatencyPoint, Service, ServiceDetail } from "@/lib/api";
import { fetcher } from "@/lib/api";
import { pct } from "@/lib/format";

import { LatencyChart } from "./LatencyChart";
import { StatusDot, StatusLabel } from "./StatusBadge";
import { UptimeBars } from "./UptimeBars";

/** Una fila por servicio. Al abrirla carga (solo entonces) el detalle y la latencia. */
export function ServiceRow({ service, daily }: { service: Service; daily: DailyPoint[] }) {
  const [open, setOpen] = useState(false);
  const panelId = `detalle-${service.id}`;

  return (
    <div className="border-b border-line px-4 py-3.5 last:border-b-0">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full cursor-pointer items-center justify-between gap-3 text-left"
      >
        <span className="flex items-center gap-2 font-semibold">
          <StatusDot status={service.status} />
          {service.name}
        </span>
        <StatusLabel status={service.status} latencyMs={service.last_latency_ms} />
      </button>
      <UptimeBars points={daily} />
      <p className="mt-0.5 text-right text-xs text-muted">Últimas 24 h: {pct(service.uptime_24h)}</p>
      {open && (
        <div id={panelId}>
          <ServiceDetailPanel id={service.id} />
        </div>
      )}
    </div>
  );
}

function ServiceDetailPanel({ id }: { id: string }) {
  // refreshInterval: se actualiza solo cada minuto mientras el panel está abierto.
  const detail = useSWR<ServiceDetail>(`/api/services/${id}`, fetcher, { refreshInterval: 60_000 });
  const latency = useSWR<LatencyPoint[]>(`/api/services/${id}/latency?hours=24`, fetcher, {
    refreshInterval: 60_000,
  });

  if (detail.error || latency.error) {
    return <p className="mt-3 text-sm text-muted">No se pudo cargar el detalle.</p>;
  }
  if (!detail.data || !latency.data) {
    return <p className="mt-3 text-sm text-muted">Cargando…</p>;
  }
  const s = detail.data;
  return (
    <div className="mt-3 text-sm text-muted">
      <p>
        Disponibilidad 7 d <strong className="text-ink">{pct(s.uptime["7d"])}</strong> · 30 d{" "}
        <strong className="text-ink">{pct(s.uptime["30d"])}</strong> · 90 d{" "}
        <strong className="text-ink">{pct(s.uptime["90d"])}</strong>
        {s.ssl_days_left != null && <> · SSL vence en {s.ssl_days_left} días</>}
      </p>
      {s.last_error && <p>Último error: {s.last_error}</p>}
      <LatencyChart points={latency.data} />
    </div>
  );
}
