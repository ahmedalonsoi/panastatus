"""Exporta las vistas del esquema `reporting` a CSV (para Power BI, Excel, etc.).

Alternativa a conectar Power BI directo a la base de datos: no requiere túnel SSH ni
abrir puertos. Útil para un análisis puntual o para compartir datos.

    python -m panastatus.export_reports            # → reports/*.csv
    python -m panastatus.export_reports --out C:/ruta/

Los CSV llevan BOM UTF-8 para que Excel muestre bien las tildes.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
from pathlib import Path

import asyncpg

from panastatus.config import get_settings

# Lista fija (no se arma con texto del usuario): evita cualquier inyección SQL.
VIEWS = (
    "dim_service",
    "fact_service_daily",
    "fact_incidents",
    "fact_latency_hourly",
    "sla_monthly",
)


async def fetch_views() -> dict[str, list[asyncpg.Record]]:
    """Lee todas las vistas (parte async: red). La escritura a disco va aparte."""
    conn = await asyncpg.connect(get_settings().database_url)
    try:
        return {view: await conn.fetch(f"SELECT * FROM reporting.{view}") for view in VIEWS}
    finally:
        await conn.close()


def write_csv(path: Path, rows: list[asyncpg.Record]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if rows:
            writer.writerow(rows[0].keys())
            writer.writerows(tuple(r.values()) for r in rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Exportar reportes a CSV")
    parser.add_argument("--out", type=Path, default=Path("reports"))
    out_dir: Path = parser.parse_args().out
    out_dir.mkdir(parents=True, exist_ok=True)
    for view, rows in asyncio.run(fetch_views()).items():
        path = out_dir / f"{view}.csv"
        write_csv(path, rows)
        print(f"{path}  ({len(rows)} filas)")


if __name__ == "__main__":
    main()
