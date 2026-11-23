/**
 * Cliente de la API pública de PanaStatus.
 *
 * Los tipos reflejan los modelos Pydantic de `src/panastatus/api.py`. Si cambias uno,
 * cambia el otro (la documentación viva está en /api/docs).
 *
 * En producción la API está en el mismo dominio (Caddy enruta /api/* a FastAPI), así que
 * API_BASE queda vacío. En desarrollo (`npm run dev` en :3000) apunta a :8000; ver
 * `.env.development`.
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export type Status = "up" | "degraded" | "down" | "unknown";
export type Overall = "operational" | "degraded" | "outage";

export interface Summary {
  overall: Overall;
  counts: Record<Status, number>;
  last_checked_at: string | null;
}

export interface Service {
  id: string;
  name: string;
  category: string;
  category_label: string;
  url: string;
  status: Status;
  last_checked_at: string | null;
  last_latency_ms: number | null;
  last_error: string | null;
  ssl_days_left: number | null;
  uptime_24h: number | null;
  down_since: string | null;
}

export interface ServiceDetail extends Service {
  uptime: Record<"7d" | "30d" | "90d", number | null>;
}

export interface DailyPoint {
  day: string; // AAAA-MM-DD (día de Panamá)
  total: number;
  ok_count: number;
  uptime: number; // 0..1
  avg_latency_ms: number | null;
}

export interface LatencyPoint {
  bucket: string;
  avg_ms: number | null;
  max_ms: number | null;
  failures: number;
}

export interface Incident {
  id: number;
  service_id: string;
  service_name: string;
  started_at: string;
  resolved_at: string | null;
  duration_seconds: number;
  cause: string | null;
  postmortem?: string | null; // texto aprobado por el admin (Fase 4), si existe
}

export interface About {
  contact: string;
  user_agent: string;
}

export class ApiError extends Error {
  constructor(public readonly status: number) {
    super(`HTTP ${status}`);
  }
}

/** Fetcher para SWR: la clave es la ruta de la API (p. ej. "/api/services"). */
export async function fetcher<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new ApiError(res.status);
  return res.json() as Promise<T>;
}
