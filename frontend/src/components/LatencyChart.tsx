"use client";

import { useRef, useState } from "react";

import type { LatencyPoint } from "@/lib/api";
import { hourMinute } from "@/lib/format";

const W = 600;
const H = 120;
const PAD_TOP = 8;

/**
 * Latencia promedio en tramos de 15 min (una sola serie: el título la nombra, sin leyenda).
 * - Línea de 2 px; los tramos con fallas se marcan con una franja roja suave.
 * - Cursor: una línea vertical sigue al mouse y se ajusta al tramo más cercano; el
 *   tooltip muestra el valor de ese tramo.
 * - Accesibilidad: <details> con la tabla de datos.
 */
export function LatencyChart({ points }: { points: LatencyPoint[] }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [idx, setIdx] = useState<number | null>(null);

  const values = points.map((p) => p.avg_ms).filter((v): v is number => v != null);
  if (values.length < 2) {
    return <p className="text-sm text-muted">Aún no hay suficientes datos de latencia.</p>;
  }

  const max = Math.max(...values) * 1.15;
  const x = (i: number) => (i / (points.length - 1)) * W;
  const y = (v: number) => H - (v / max) * (H - PAD_TOP);

  // Un tramo sin datos corta la línea (M = "mover" sin dibujar) en vez de unir el hueco.
  let d = "";
  let pen = false;
  points.forEach((p, i) => {
    if (p.avg_ms == null) {
      pen = false;
      return;
    }
    d += `${pen ? "L" : "M"}${x(i).toFixed(1)},${y(p.avg_ms).toFixed(1)} `;
    pen = true;
  });

  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const rect = svgRef.current!.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    setIdx(Math.max(0, Math.min(points.length - 1, Math.round(ratio * (points.length - 1)))));
  };

  const active = idx != null ? points[idx] : null;

  return (
    <figure className="mt-2">
      <figcaption className="text-xs text-muted">
        Latencia promedio, últimas 24 h · máx. {Math.max(...values)} ms
      </figcaption>
      <div className="relative">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${H}`}
          preserveAspectRatio="none"
          className="mt-1 block h-28 w-full touch-none"
          role="img"
          aria-label="Gráfico de latencia de las últimas 24 horas"
          onPointerMove={onMove}
          onPointerLeave={() => setIdx(null)}
        >
          <line x1={0} x2={W} y1={H} y2={H} stroke="var(--line)" vectorEffect="non-scaling-stroke" />
          {points.map((p, i) =>
            p.failures ? (
              <rect
                key={p.bucket}
                x={x(i) - 3}
                y={0}
                width={6}
                height={H}
                fill="var(--status-down)"
                opacity={0.25}
              />
            ) : null,
          )}
          <path
            d={d}
            fill="none"
            stroke="var(--accent)"
            strokeWidth={2}
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
          />
          {idx != null && (
            <line
              x1={x(idx)}
              x2={x(idx)}
              y1={0}
              y2={H}
              stroke="var(--muted)"
              strokeWidth={1}
              vectorEffect="non-scaling-stroke"
            />
          )}
        </svg>
        {active && (
          <div
            className="pointer-events-none absolute top-0 z-10 rounded-md border border-line bg-surface px-2 py-1 text-xs shadow-sm"
            style={{
              left: `${(idx! / (points.length - 1)) * 100}%`,
              transform: idx! > points.length / 2 ? "translateX(calc(-100% - 8px))" : "translateX(8px)",
            }}
          >
            <strong className="block text-sm text-ink">
              {active.avg_ms != null ? `${active.avg_ms} ms` : "sin datos"}
            </strong>
            <span className="text-muted">
              {hourMinute(active.bucket)}
              {active.failures ? ` · ${active.failures} falla(s)` : ""}
            </span>
          </div>
        )}
      </div>
      <details className="mt-1 text-xs text-muted">
        <summary className="cursor-pointer">Ver datos en tabla</summary>
        <table className="mt-1 w-full text-left">
          <thead>
            <tr>
              <th>Hora</th>
              <th>Promedio</th>
              <th>Máximo</th>
              <th>Fallas</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr key={p.bucket}>
                <td>{hourMinute(p.bucket)}</td>
                <td>{p.avg_ms ?? "—"} ms</td>
                <td>{p.max_ms ?? "—"} ms</td>
                <td>{p.failures}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
