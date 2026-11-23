import type { Incident } from "@/lib/api";
import { dateTime, duration } from "@/lib/format";

import { StatusDot } from "./StatusBadge";

export function IncidentList({ incidents }: { incidents: Incident[] }) {
  if (!incidents.length) {
    return <p className="py-3 text-sm text-muted">Sin incidentes registrados.</p>;
  }
  return (
    <ul>
      {incidents.map((i) => (
        <li key={i.id} className="border-b border-line py-3 last:border-b-0">
          <div className="flex items-center gap-2">
            <StatusDot status={i.resolved_at ? "up" : "down"} />
            <strong>{i.service_name}</strong>
            <span className="text-sm text-muted">· {i.resolved_at ? "Resuelto" : "En curso"}</span>
          </div>
          <p className="text-sm text-muted">
            {dateTime(i.started_at)} · duración {duration(i.duration_seconds)}
            {i.cause && <> · {i.cause}</>}
          </p>
          {i.postmortem && (
            <details className="mt-1 text-sm">
              <summary className="cursor-pointer text-accent">Análisis del incidente</summary>
              {/* Texto plano revisado por el admin; whitespace-pre-line respeta los párrafos. */}
              <div className="mt-2 rounded-md bg-bg p-3 whitespace-pre-line">{i.postmortem}</div>
            </details>
          )}
        </li>
      ))}
    </ul>
  );
}
