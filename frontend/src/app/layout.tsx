import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";

import { GitHubIcon } from "@/components/Icons";
import { SiteHeader } from "@/components/SiteHeader";
import { SITE } from "@/lib/site";

import "./globals.css";

// next/font descarga la fuente en el build y la sirve desde nuestro dominio:
// el navegador del visitante nunca contacta a Google (privacidad y velocidad).
const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: "PanaStatus — Estado de servicios web de Panamá",
    template: "%s · PanaStatus",
  },
  description:
    "Disponibilidad en tiempo real de bancos, gobierno, universidades y servicios globales en Panamá.",
  applicationName: "PanaStatus",
  openGraph: {
    title: "PanaStatus — Estado de servicios web de Panamá",
    description: "¿Se cayó o es mi internet? Disponibilidad de bancos, gobierno y universidades.",
    locale: "es_PA",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f7f9" },
    { media: "(prefers-color-scheme: dark)", color: "#0f1013" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
      <body className="flex min-h-screen flex-col font-sans text-[15px] leading-relaxed">
        <a
          href="#contenido"
          className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-30 focus:rounded-md focus:bg-surface focus:px-3 focus:py-2"
        >
          Saltar al contenido
        </a>
        <SiteHeader />
        <main id="contenido" className="mx-auto w-full max-w-4xl flex-1 px-4 pt-8 pb-16">
          {children}
        </main>
        <SiteFooter />
      </body>
    </html>
  );
}

function SiteFooter() {
  return (
    <footer className="border-t border-line bg-surface">
      <div className="mx-auto grid max-w-4xl gap-6 px-4 py-8 text-sm text-muted sm:grid-cols-[2fr_1fr_1fr]">
        <div>
          <p className="font-semibold text-ink">PanaStatus</p>
          <p className="mt-1 max-w-sm">
            Monitor independiente de disponibilidad de servicios web usados en Panamá. Revisa
            solo páginas públicas cada 1–5 minutos, con un User-Agent identificable.
          </p>
        </div>
        <div>
          <p className="font-semibold text-ink">Sitio</p>
          <ul className="mt-1 space-y-1">
            <li>
              <Link href="/incidentes/">Historial de incidentes</Link>
            </li>
            <li>
              <Link href="/bot/">Metodología y exclusión</Link>
            </li>
            <li>
              <a href={SITE.apiDocs}>API pública</a>
            </li>
          </ul>
        </div>
        <div>
          <p className="font-semibold text-ink">Proyecto</p>
          <ul className="mt-1 space-y-1">
            <li>
              <a href={SITE.repoUrl} className="inline-flex items-center gap-1.5">
                <GitHubIcon className="size-3.5" /> Código fuente
              </a>
            </li>
            <li>Hecho en Panamá 🇵🇦</li>
          </ul>
        </div>
      </div>
    </footer>
  );
}
