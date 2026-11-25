/**
 * Pruebas de las funciones de formato y cálculo de la página.
 * Son funciones puras: se prueban sin navegador ni API (vitest, entorno Node).
 */
import { describe, expect, it } from "vitest";

import { dayLevel, duration, lastDays, pct, timeAgo, weightedUptime, worstStatus } from "./format";

describe("pct", () => {
  it("formatea con dos decimales y muestra guion sin datos", () => {
    expect(pct(0.99954)).toBe("99.95 %");
    expect(pct(null)).toBe("—");
    expect(pct(undefined)).toBe("—");
  });
});

describe("duration", () => {
  it("usa la unidad más grande útil", () => {
    expect(duration(42)).toBe("42 s");
    expect(duration(7 * 60)).toBe("7 min");
    expect(duration(2 * 3600 + 5 * 60)).toBe("2 h 5 min");
  });
});

describe("dayLevel", () => {
  // Mismos umbrales que statuspage.io: verde ≥ 99.9 %, ámbar ≥ 98 %, rojo debajo.
  it.each([
    [undefined, "none"],
    [1, "up"],
    [0.999, "up"],
    [0.9989, "minor"],
    [0.98, "minor"],
    [0.97, "major"],
  ] as const)("%s → %s", (uptime, level) => {
    expect(dayLevel(uptime)).toBe(level);
  });
});

describe("weightedUptime", () => {
  it("pondera por cantidad de revisiones, no promedia porcentajes", () => {
    // Día 1: 480 revisiones al 100 %. Día 2: 10 revisiones al 0 %.
    // Promedio simple: 50 %. Ponderado (lo correcto): 480 / 490 ≈ 97.96 %.
    const points = [
      { total: 480, ok_count: 480 },
      { total: 10, ok_count: 0 },
    ];
    expect(weightedUptime(points)).toBeCloseTo(480 / 490, 6);
  });

  it("devuelve null sin revisiones", () => {
    expect(weightedUptime([])).toBeNull();
  });
});

describe("worstStatus", () => {
  it("una caída manda sobre la lentitud y lo desconocido", () => {
    expect(worstStatus(["up", "degraded", "down", "unknown"])).toBe("down");
    expect(worstStatus(["up", "unknown"])).toBe("unknown");
    expect(worstStatus([])).toBe("up");
  });
});

describe("lastDays", () => {
  it("devuelve n días en hora de Panamá, del más viejo a hoy", () => {
    // 2026-11-25 03:00 UTC = 2026-11-24 22:00 en Panamá (UTC-5): "hoy" es el 24.
    const now = Date.UTC(2026, 10, 25, 3, 0);
    expect(lastDays(3, now)).toEqual(["2026-11-22", "2026-11-23", "2026-11-24"]);
  });
});

describe("timeAgo", () => {
  const now = Date.UTC(2026, 10, 24, 12, 0);
  it.each([
    [10, "hace unos segundos"],
    [5 * 60, "hace 5 minutos"],
    [2 * 3600, "hace 2 horas"],
  ])("%i s atrás → %s", (secondsAgo, text) => {
    expect(timeAgo(new Date(now - secondsAgo * 1000).toISOString(), now)).toBe(text);
  });
});
