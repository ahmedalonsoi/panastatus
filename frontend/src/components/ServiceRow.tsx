"use client";

import { useState } from "react";
import useSWR from "swr";

import type { DailyPoint, LatencyPoint, Service, ServiceDetail } from "@/lib/api";
import { fetcher } from "@/lib/api";
import { dateTime, pct, weightedUptime } from "@/lib/format";

import { ChevronIcon, ExternalIcon } from "./Icons";
import { LatencyChart } from "./LatencyChart";
import { StatusPill } from "./StatusBadge";
import { UptimeBars } from "./UptimeBars";

/** Una fila por servicio. Al abrirla carga (solo entonces) el detalle y la latencia. */
export function ServiceRow({ service, daily }: { service: Service; daily?: DailyPoint[] }) {
  const [open, setOpen] = useState(false);
  const panelId = `detalle-${service.id}`;
  const host = new URL(service.url).host.replace(/^www\./, "");
  const uptime90 = daily ? weightedUptime(daily) : null;

  return (
    <div className="border-b border-line px-4 py-4 last:border-b-0">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
        className="group flex w-full cursor-pointer items-center justify-between gap-3 text-left"
      >
        <span className="flex min-w-0 items-center gap-2">
          <ChevronIcon
            className={`size-4 flex-none text-muted transition-transform group-hover:text-ink ${open ? "rotate-0" : "-rotate-90"}`}
          />
          <span className="min-w-0">
            <span className="block truncate font-semibold text-ink">{service.name}</span>
            <span className="block truncate font-mono text-xs text-muted">{host}</span>
          </span>
        </span>
        <StatusPill status={service.status} latencyMs={service.last_latency_ms} />
      </button>

      {daily ? (
        <UptimeBars
          points={daily}
          left={`${pct(uptime90)} en 90 días`}
          right={`24 h: ${pct(service.uptime_24h)}`}
        />
      ) : (
        <div className="mt-3 h-7 animate-pulse rounded bg-empty" aria-hidden />
      )}

      {open && (
        <div id={panelId}>
          <ServiceDetailPanel service={service} />
        </div>
      )}
    </div>
  );
}

function ServiceDetailPanel({ service }: { service: Service }) {
  // refreshInterval: se actualiza solo cada minuto mientras el panel está abierto.
  const detail = useSWR<ServiceDetail>(`/api/services/${service.id}`, fetcher, {
    refreshInterval: 60_000,
  });
  const latency = useSWR<LatencyPoint[]>(`/api/services/${service.id}/latency?hours=24`, fetcher, {
    refreshInterval: 60_000,
  });

  if (detail.error || latency.error) {
    return <p className="mt-3 text-sm text-muted">No se pudo cargar el detalle.</p>;
  }
  if (!detail.data || !latency.data) {
    return <div className="mt-3 h-36 animate-pulse rounded-lg bg-empty" aria-label="Cargando" />;
  }
  const s = detail.data;
  const facts: [string, string][] = [
    ["7 días", pct(s.uptime["7d"])],
    ["30 días", pct(s.uptime["30d"])],
    ["90 días", pct(s.uptime["90d"])],
    ["Certificado TLS", s.ssl_days_left != null ? `vence en ${s.ssl_days_left} días` : "—"],
  ];

  return (
    <div className="mt-4 rounded-xl bg-surface-2 p-4">
      <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        {facts.map(([k, v]) => (
          <div key={k}>
            <dt className="text-xs text-muted">{k}</dt>
            <dd className="font-semibold text-ink tabular-nums">{v}</dd>
          </div>
        ))}
      </dl>
      {s.down_since && (
        <p className="mt-3 text-sm text-status-down-ink">
          Caído desde el <time dateTime={s.down_since}>{dateTime(s.down_since)}</time>
        </p>
      )}
      {s.last_error && <p className="mt-2 text-sm text-muted">Último error: {s.last_error}</p>}
      <LatencyChart points={latency.data} />
      <a
        href={service.url}
        rel="noopener noreferrer"
        target="_blank"
        className="mt-2 inline-flex items-center gap-1 text-sm"
      >
        Abrir el sitio <ExternalIcon className="size-3.5" />
      </a>
    </div>
  );
}
