import type { Overall, Service, Summary } from "@/lib/api";
import { OVERALL_LABEL, pct, timeAgo } from "@/lib/format";

import { AlertIcon, CheckIcon, QuestionIcon, XIcon } from "./Icons";

const OVERALL_STYLE: Record<Overall | "loading", { card: string; icon: string; Icon: typeof CheckIcon }> = {
  operational: { card: "border-status-up/40 bg-status-up-soft", icon: "bg-status-up text-white", Icon: CheckIcon },
  degraded: { card: "border-status-degraded/50 bg-status-degraded-soft", icon: "bg-status-degraded text-black", Icon: AlertIcon },
  outage: { card: "border-status-down/40 bg-status-down-soft", icon: "bg-status-down text-white", Icon: XIcon },
  loading: { card: "border-line bg-surface", icon: "bg-status-unknown text-white", Icon: QuestionIcon },
};

/**
 * Tarjeta principal: responde en un segundo "¿hay algo caído?". Es una región "status"
 * (aria-live implícito): un lector de pantalla anuncia el cambio cuando se actualiza.
 */
export function OverallCard({ summary, failed }: { summary?: Summary; failed: boolean }) {
  const overall = summary?.overall ?? "loading";
  const { card, icon, Icon } = OVERALL_STYLE[overall];
  const total = summary ? Object.values(summary.counts).reduce((a, b) => a + b, 0) : 0;
  const affected = summary ? summary.counts.down + summary.counts.degraded : 0;

  return (
    <section role="status" className={`rounded-2xl border p-5 sm:p-6 ${card}`}>
      <div className="flex items-start gap-4">
        <span className={`grid size-11 flex-none place-items-center rounded-full ${icon}`}>
          <Icon className="size-6" />
        </span>
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-ink sm:text-2xl">
            {summary ? OVERALL_LABEL[summary.overall] : "Consultando servicios…"}
          </h1>
          <p className="mt-0.5 text-sm text-muted">
            {failed
              ? "No se pudo actualizar. Reintentando…"
              : summary
                ? [
                    `${total} servicios monitoreados`,
                    affected ? `${affected} con problemas` : null,
                    summary.last_checked_at ? `actualizado ${timeAgo(summary.last_checked_at)}` : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")
                : "Cargando…"}
          </p>
        </div>
      </div>
    </section>
  );
}

/** Indicadores clave (KPI) bajo la tarjeta principal. */
export function KpiTiles({ services }: { services?: Service[] }) {
  const list = services ?? [];
  const uptimes = list.map((s) => s.uptime_24h).filter((v): v is number => v != null);
  const avgUptime = uptimes.length ? uptimes.reduce((a, b) => a + b, 0) / uptimes.length : null;
  const latencies = list
    .filter((s) => s.status !== "down")
    .map((s) => s.last_latency_ms)
    .filter((v): v is number => v != null)
    .sort((a, b) => a - b);
  const median = latencies.length ? latencies[Math.floor(latencies.length / 2)] : null;
  const certs = list.filter((s) => s.ssl_days_left != null && s.ssl_days_left < 30).length;
  const down = list.filter((s) => s.status === "down").length;

  const tiles = [
    { label: "Disponibilidad 24 h", value: pct(avgUptime), hint: "promedio de todos los servicios" },
    { label: "Latencia mediana", value: median != null ? `${median} ms` : "—", hint: "última revisión" },
    { label: "Caídos ahora", value: services ? String(down) : "—", hint: "incidentes abiertos" },
    { label: "Certificados < 30 días", value: services ? String(certs) : "—", hint: "TLS por renovar" },
  ];

  return (
    <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
      {tiles.map((t) => (
        <div key={t.label} className="rounded-xl border border-line bg-surface p-3.5">
          <dt className="text-xs font-medium text-muted">{t.label}</dt>
          <dd className="mt-1 text-xl font-semibold text-ink tabular-nums">
            {services ? t.value : <span className="inline-block h-6 w-16 animate-pulse rounded bg-empty" />}
          </dd>
          <dd className="text-xs text-muted">{t.hint}</dd>
        </div>
      ))}
    </dl>
  );
}
