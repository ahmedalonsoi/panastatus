/** Datos del sitio usados en varias páginas (un solo lugar para cambiarlos). */

export const SITE = {
  name: "PanaStatus",
  repoUrl: "https://github.com/ahmedalonsoi/panastatus",
  apiDocs: "/api/docs",
} as const;

export const NAV = [
  { href: "/", label: "Estado" },
  { href: "/incidentes/", label: "Incidentes" },
  { href: "/bot/", label: "Sobre el bot" },
] as const;
