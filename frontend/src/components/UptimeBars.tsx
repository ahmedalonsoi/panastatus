"use client";

import { useMemo, useState } from "react";

import type { DailyPoint } from "@/lib/api";
import { dayLevel, lastDays, pct } from "@/lib/format";

const LEVEL_CLASS = {
  none: "bg-empty",
  up: "bg-status-up",
  minor: "bg-status-degraded",
  major: "bg-status-down",
} as const;

/**
 * Barra de disponibilidad diaria (90 días, de la más vieja a hoy). Cada día es una marca
 * con su propio tooltip; al pasar el mouse, el detalle del día aparece en la línea de abajo
 * (entre `left` y `right`), así nunca tapa otras filas.
 */
export function UptimeBars({
  points,
  days = 90,
  left,
  right,
}: {
  points: DailyPoint[];
  days?: number;
  left?: React.ReactNode;
  right?: React.ReactNode;
}) {
  const [hover, setHover] = useState<string | null>(null);
  const byDay = useMemo(() => new Map(points.map((p) => [p.day, p])), [points]);
  const range = useMemo(() => lastDays(days), [days]);

  const tip = (day: string) => {
    const p = byDay.get(day);
    return p ? `${day}: ${pct(p.uptime)} disponible` : `${day}: sin datos`;
  };

  return (
    <div>
      <div
        className="mt-3 flex h-7 gap-[2px]"
        onMouseLeave={() => setHover(null)}
        role="img"
        aria-label={`Disponibilidad diaria de los últimos ${days} días`}
      >
        {range.map((day) => (
          <span
            key={day}
            title={tip(day)}
            onMouseEnter={() => setHover(day)}
            className={`flex-1 rounded-[2px] transition-opacity hover:opacity-70 ${LEVEL_CLASS[dayLevel(byDay.get(day)?.uptime)]}`}
          />
        ))}
      </div>
      <div className="mt-1 flex justify-between gap-2 text-xs text-muted tabular-nums">
        <span className="whitespace-nowrap">{left ?? `hace ${days} días`}</span>
        <span aria-live="polite" className="truncate text-ink">
          {hover ? tip(hover) : ""}
        </span>
        <span className="whitespace-nowrap">{right ?? "hoy"}</span>
      </div>
    </div>
  );
}
