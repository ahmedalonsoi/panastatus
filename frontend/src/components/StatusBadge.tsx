import type { Status } from "@/lib/api";
import { STATUS_LABEL } from "@/lib/format";

import { AlertIcon, CheckIcon, QuestionIcon, XIcon } from "./Icons";

// Ícono + texto + color: el estado se entiende aunque no se distingan los colores.
export const STATUS_ICON = { up: CheckIcon, degraded: AlertIcon, down: XIcon, unknown: QuestionIcon };

const DOT: Record<Status, string> = {
  up: "bg-status-up text-white",
  degraded: "bg-status-degraded text-black",
  down: "bg-status-down text-white",
  unknown: "bg-status-unknown text-white",
};

const PILL: Record<Status, string> = {
  up: "bg-status-up-soft text-status-up-ink",
  degraded: "bg-status-degraded-soft text-status-degraded-ink",
  down: "bg-status-down-soft text-status-down-ink",
  unknown: "bg-status-unknown-soft text-status-unknown-ink",
};

/** Círculo sólido con ícono: identifica el estado de un vistazo en listas. */
export function StatusDot({ status, className = "size-4" }: { status: Status; className?: string }) {
  const Icon = STATUS_ICON[status];
  return (
    <span
      aria-hidden
      className={`inline-flex flex-none items-center justify-center rounded-full ${DOT[status]} ${className}`}
    >
      <Icon className="size-[70%]" />
    </span>
  );
}

/** Insignia con fondo suave: "Operativo · 451 ms". */
export function StatusPill({ status, latencyMs }: { status: Status; latencyMs?: number | null }) {
  const Icon = STATUS_ICON[status];
  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap">
      {latencyMs != null && status !== "down" && (
        <span className="hidden font-mono text-xs text-muted tabular-nums sm:inline">
          {latencyMs} ms
        </span>
      )}
      <span
        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${PILL[status]}`}
      >
        <Icon className="size-3.5" />
        {STATUS_LABEL[status]}
      </span>
    </span>
  );
}
