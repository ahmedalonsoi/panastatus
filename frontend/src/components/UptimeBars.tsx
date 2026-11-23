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
 * Barra de disponibilidad diaria (90 días). Cada día es una marca con su propio
 * tooltip al pasar el mouse o al enfocarla con el teclado.
 */
export function UptimeBars({ points, days = 90 }: { points: DailyPoint[]; days?: number }) {
  const [hover, setHover] = useState<string | null>(null);
  const byDay = useMemo(() => new Map(points.map((p) => [p.day, p])), [points]);
  const range = useMemo(() => lastDays(days), [days]);

  const tip = (day: string) => {
    const p = byDay.get(day);
    return p ? `${day}: ${pct(p.uptime)} disponible` : `${day}: sin datos`;
  };

  return (
    <div>
      <div className="mt-2.5 flex h-8 gap-[2px]" onMouseLeave={() => setHover(null)}>
        {range.map((day) => (
          <span
            key={day}
            tabIndex={-1}
            title={tip(day)}
            aria-label={tip(day)}
            onMouseEnter={() => setHover(day)}
            className={`flex-1 rounded-[2px] transition-opacity hover:opacity-70 ${LEVEL_CLASS[dayLevel(byDay.get(day)?.uptime)]}`}
          />
        ))}
      </div>
      <div className="mt-1 flex justify-between text-xs text-muted">
        <span>hace {days} días</span>
        <span aria-live="polite">{hover ? tip(hover) : ""}</span>
        <span>hoy</span>
      </div>
    </div>
  );
}
