import type { Incident } from "@/lib/api";
import { dateTime, duration } from "@/lib/format";

import { CheckIcon } from "./Icons";
import { StatusDot } from "./StatusBadge";

/** Lista de incidentes: los abiertos primero, con duración, causa y post-mortem aprobado. */
export function IncidentList({ incidents }: { incidents: Incident[] }) {
  if (!incidents.length) {
    return (
      <p className="flex items-center gap-2 py-4 text-sm text-muted">
        <CheckIcon className="size-4 text-status-up-ink" />
        Sin incidentes registrados.
      </p>
    );
  }
  return (
    <ul>
      {incidents.map((i) => {
        const open = !i.resolved_at;
        return (
          <li key={i.id} className="border-b border-line py-4 last:border-b-0">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <StatusDot status={open ? "down" : "up"} />
              <strong className="text-ink">{i.service_name}</strong>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-semibold ${open ? "bg-status-down-soft text-status-down-ink" : "bg-surface-2 text-muted"}`}
              >
                {open ? "En curso" : "Resuelto"}
              </span>
            </div>
            <p className="mt-1 text-sm text-muted">
              <time dateTime={i.started_at}>{dateTime(i.started_at)}</time> ·{" "}
              {open ? "lleva" : "duró"} {duration(i.duration_seconds)}
              {i.cause && <> · {i.cause}</>}
            </p>
            {i.postmortem && (
              <details className="mt-2 text-sm">
                <summary className="cursor-pointer font-medium text-accent">
                  Análisis del incidente (revisado por una persona)
                </summary>
                {/* Texto plano aprobado por el admin; whitespace-pre-line respeta los párrafos. */}
                <div className="mt-2 rounded-lg bg-surface-2 p-3 whitespace-pre-line">
                  {i.postmortem}
                </div>
              </details>
            )}
          </li>
        );
      })}
    </ul>
  );
}
