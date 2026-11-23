import type { NextConfig } from "next";

/**
 * PanaStatus se publica como sitio ESTÁTICO (`output: "export"`):
 * `next build` genera HTML/CSS/JS en `out/` y Caddy los sirve directamente.
 *
 * ¿Por qué estático y no un servidor Node?
 * - Seguridad: en producción no corre ningún proceso Node expuesto a internet.
 * - Costo y rendimiento: archivos estáticos con caché, casi sin CPU.
 * - Los datos cambian cada minuto, así que igual se piden desde el navegador a la API
 *   (FastAPI). El HTML solo es el "esqueleto".
 */
const nextConfig: NextConfig = {
  output: "export",
  // /bot -> /bot/index.html: cualquier servidor estático lo sirve sin reglas extra.
  trailingSlash: true,
  // La optimización de imágenes de Next necesita un servidor; no la usamos.
  images: { unoptimized: true },
  // No anunciar el framework en las cabeceras (menos información para un atacante).
  poweredByHeader: false,
  reactStrictMode: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
