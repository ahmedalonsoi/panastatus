"use client";

import Link from "next/link";
import useSWR from "swr";

import { CategorySection, CategorySkeleton, categoryAnchor } from "@/components/CategorySection";
import { IncidentList } from "@/components/IncidentList";
import { KpiTiles, OverallCard } from "@/components/Overview";
import { StatusDot } from "@/components/StatusBadge";
import type { DailyPoint, Incident, Service, Summary } from "@/lib/api";
import { fetcher } from "@/lib/api";
import { worstStatus } from "@/lib/format";

// La página se refresca sola cada 60 s (SWR también refresca al volver a la pestaña).
const REFRESH = { refreshInterval: 60_000 };

interface Group {
  category: string;
  label: string;
  services: Service[];
}

/** Agrupa por categoría conservando el orden de la API (el de config/services.yaml). */
function groupByCategory(services: Service[]): Group[] {
  const groups = new Map<string, Group>();
  for (const s of services) {
    const g = groups.get(s.category) ?? { category: s.category, label: s.category_label, services: [] };
    g.services.push(s);
    groups.set(s.category, g);
  }
  return [...groups.values()];
}

export default function StatusPage() {
  const summary = useSWR<Summary>("/api/summary", fetcher, REFRESH);
  const services = useSWR<Service[]>("/api/services", fetcher, REFRESH);
  const daily = useSWR<Record<string, DailyPoint[]>>("/api/uptime/daily?days=90", fetcher, REFRESH);
  const incidents = useSWR<Incident[]>("/api/incidents?limit=5", fetcher, REFRESH);

  const failed = Boolean(summary.error || services.error);
  const groups = services.data ? groupByCategory(services.data) : null;

  return (
    <>
      <OverallCard summary={summary.data} failed={failed} />
      <KpiTiles services={services.data} />

      {groups && groups.length > 1 && (
        <nav aria-label="Categorías" className="mt-6 mb-4 flex flex-wrap gap-2">
          {groups.map((g) => (
            <a
              key={g.category}
              href={`#${categoryAnchor(g.category)}`}
              className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1 text-sm text-ink no-underline transition-colors hover:bg-surface-2"
            >
              <StatusDot status={worstStatus(g.services.map((s) => s.status))} className="size-3" />
              {g.label}
              <span className="text-muted">{g.services.length}</span>
            </a>
          ))}
        </nav>
      )}

      <div className="mt-6">
        {groups
          ? groups.map((g) => (
              <CategorySection
                key={g.category}
                category={g.category}
                label={g.label}
                services={g.services}
                daily={daily.data}
              />
            ))
          : [0, 1].map((i) => <CategorySkeleton key={i} />)}
      </div>

      <section aria-labelledby="incidentes-recientes" className="mt-10">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 id="incidentes-recientes" className="text-lg font-semibold">
            Incidentes recientes
          </h2>
          <Link href="/incidentes/" className="text-sm">
            Ver historial →
          </Link>
        </div>
        <div className="rounded-2xl border border-line bg-surface px-4">
          {incidents.data ? (
            <IncidentList incidents={incidents.data} />
          ) : (
            <div className="my-4 h-10 animate-pulse rounded bg-empty" aria-label="Cargando" />
          )}
        </div>
      </section>

      <p className="mt-8 text-xs text-muted">
        Cómo leer esta página: una caída se confirma con 2 revisiones fallidas seguidas, para
        evitar falsas alarmas. Cada barra es un día: verde ≥ 99.9 %, ámbar ≥ 98 %, rojo por
        debajo. Los datos se miden desde afuera, igual que los vería un usuario.
      </p>
    </>
  );
}
