/** Formatos en español de Panamá. Panamá es UTC-5 todo el año (sin horario de verano). */

import type { Overall, Status } from "./api";

export const TZ = "America/Panama";

export const STATUS_LABEL: Record<Status, string> = {
  up: "Operativo",
  degraded: "Lento",
  down: "Caído",
  unknown: "Sin datos",
};

export const OVERALL_LABEL: Record<Overall, string> = {
  operational: "Todos los servicios operan con normalidad",
  degraded: "Algunos servicios están lentos",
  outage: "Hay servicios caídos",
};

export function pct(value: number | null | undefined, digits = 2): string {
  return value == null ? "—" : `${(value * 100).toFixed(digits)} %`;
}

export function dateTime(iso: string): string {
  return new Date(iso).toLocaleString("es-PA", {
    timeZone: TZ,
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function hourMinute(iso: string): string {
  return new Date(iso).toLocaleTimeString("es-PA", {
    timeZone: TZ,
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function duration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h) return `${h} h ${m} min`;
  if (m) return `${m} min`;
  return `${seconds} s`;
}

const RELATIVE = new Intl.RelativeTimeFormat("es", { numeric: "auto" });

/** "hace 2 minutos", "hace 1 hora"... (para "Actualizado ..."). */
export function timeAgo(iso: string, now = Date.now()): string {
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000);
  const abs = Math.abs(seconds);
  if (abs < 45) return "hace unos segundos";
  if (abs < 3600) return RELATIVE.format(Math.round(seconds / 60), "minute");
  if (abs < 86_400) return RELATIVE.format(Math.round(seconds / 3600), "hour");
  return RELATIVE.format(Math.round(seconds / 86_400), "day");
}

/**
 * Disponibilidad de un periodo a partir de los puntos diarios, ponderada por la cantidad
 * de revisiones de cada día (un día con 10 revisiones no pesa igual que uno con 480).
 */
export function weightedUptime(points: { total: number; ok_count: number }[]): number | null {
  const total = points.reduce((sum, p) => sum + p.total, 0);
  if (!total) return null;
  return points.reduce((sum, p) => sum + p.ok_count, 0) / total;
}

/** El peor estado de un grupo: decide el resumen de una categoría. */
const SEVERITY: Record<Status, number> = { up: 0, unknown: 1, degraded: 2, down: 3 };
export function worstStatus(statuses: Status[]): Status {
  return statuses.reduce<Status>((worst, s) => (SEVERITY[s] > SEVERITY[worst] ? s : worst), "up");
}

/** Las fechas AAAA-MM-DD de los últimos `n` días en hora de Panamá, de la más vieja a hoy. */
export function lastDays(n: number, now = Date.now()): string[] {
  const days: string[] = [];
  for (let i = n - 1; i >= 0; i--) {
    // "en-CA" formatea como AAAA-MM-DD, igual que la API.
    days.push(new Date(now - i * 86_400_000).toLocaleDateString("en-CA", { timeZone: TZ }));
  }
  return days;
}

/** Clasificación de un día en la barra de 90 días (mismos umbrales que statuspage.io). */
export function dayLevel(uptime: number | undefined): "none" | "up" | "minor" | "major" {
  if (uptime == null) return "none";
  if (uptime >= 0.999) return "up";
  if (uptime >= 0.98) return "minor";
  return "major";
}
