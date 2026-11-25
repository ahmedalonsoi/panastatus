import type { DailyPoint, Service } from "@/lib/api";
import { worstStatus } from "@/lib/format";

import { ServiceRow } from "./ServiceRow";
import { StatusDot } from "./StatusBadge";

/** Convierte "🎓 Educación" en "educacion" para usarlo como ancla (#educacion). */
export function categoryAnchor(category: string): string {
  return `cat-${category}`;
}

function summaryText(services: Service[]): string {
  const down = services.filter((s) => s.status === "down").length;
  const slow = services.filter((s) => s.status === "degraded").length;
  if (down) return `${down} caído${down > 1 ? "s" : ""}`;
  if (slow) return `${slow} lento${slow > 1 ? "s" : ""}`;
  return "Todos operativos";
}

/** Un bloque por categoría con su resumen ("Todos operativos", "1 caído"). */
export function CategorySection({
  category,
  label,
  services,
  daily,
}: {
  category: string;
  label: string;
  services: Service[];
  daily?: Record<string, DailyPoint[]>;
}) {
  const status = worstStatus(services.map((s) => s.status));
  const headingId = `${categoryAnchor(category)}-titulo`;
  return (
    <section
      id={categoryAnchor(category)}
      aria-labelledby={headingId}
      className="mb-5 overflow-hidden rounded-2xl border border-line bg-surface"
    >
      <div className="flex items-center justify-between gap-3 border-b border-line bg-surface-2/60 px-4 py-3">
        <h2 id={headingId} className="text-base font-semibold">
          {label}
          <span className="ml-2 text-sm font-normal text-muted">{services.length}</span>
        </h2>
        <span className="flex items-center gap-1.5 text-sm text-muted">
          <StatusDot status={status} className="size-3.5" />
          {summaryText(services)}
        </span>
      </div>
      {services.map((s) => (
        <ServiceRow key={s.id} service={s} daily={daily?.[s.id]} />
      ))}
    </section>
  );
}

/** Esqueleto mientras carga: misma forma que el contenido real, sin saltos de diseño. */
export function CategorySkeleton() {
  return (
    <div className="mb-5 rounded-2xl border border-line bg-surface" aria-hidden>
      <div className="border-b border-line px-4 py-3.5">
        <div className="h-4 w-32 animate-pulse rounded bg-empty" />
      </div>
      {[0, 1, 2].map((i) => (
        <div key={i} className="border-b border-line px-4 py-4 last:border-b-0">
          <div className="flex justify-between">
            <div className="h-4 w-40 animate-pulse rounded bg-empty" />
            <div className="h-4 w-20 animate-pulse rounded bg-empty" />
          </div>
          <div className="mt-3 h-7 animate-pulse rounded bg-empty" />
        </div>
      ))}
    </div>
  );
}
