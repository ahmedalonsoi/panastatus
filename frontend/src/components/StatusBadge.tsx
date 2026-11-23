import type { Status } from "@/lib/api";
import { STATUS_LABEL } from "@/lib/format";

// Ícono + texto + color: el estado se entiende aunque no se distingan los colores.
const ICON: Record<Status, string> = { up: "✓", degraded: "!", down: "✕", unknown: "?" };

const DOT: Record<Status, string> = {
  up: "bg-status-up",
  degraded: "bg-status-degraded",
  down: "bg-status-down",
  unknown: "bg-status-unknown",
};

export function StatusDot({ status }: { status: Status }) {
  return (
    <span
      aria-hidden
      className={`inline-flex size-4 flex-none items-center justify-center rounded-full text-[10px] font-bold ${DOT[status]} ${status === "degraded" ? "text-black" : "text-white"}`}
    >
      {ICON[status]}
    </span>
  );
}

export function StatusLabel({ status, latencyMs }: { status: Status; latencyMs?: number | null }) {
  return (
    <span className="text-sm font-semibold whitespace-nowrap text-ink">
      {STATUS_LABEL[status]}
      {latencyMs != null && status !== "down" && (
        <span className="font-normal text-muted"> · {latencyMs} ms</span>
      )}
    </span>
  );
}
