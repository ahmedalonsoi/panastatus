import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
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
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f7f9" },
    { media: "(prefers-color-scheme: dark)", color: "#101114" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
      <body className="min-h-screen font-sans text-[15px] leading-relaxed">
        <div className="mx-auto max-w-3xl px-4 pt-8 pb-16">
          <header className="flex flex-wrap items-baseline justify-between gap-2">
            <Link href="/" className="text-2xl font-bold text-ink no-underline">
              Pana<span className="text-accent">Status</span>
            </Link>
            <nav className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
              <Link href="/">Estado</Link>
              <Link href="/incidentes/">Incidentes</Link>
              <Link href="/bot/">Sobre el bot</Link>
              <a href="/api/docs">API</a>
            </nav>
          </header>
          <main>{children}</main>
          <footer className="mt-12 text-center text-xs text-muted">
            PanaStatus revisa solo páginas públicas cada 1–5 minutos, con un User-Agent
            identificable. <Link href="/bot/">Más información</Link>.
          </footer>
        </div>
      </body>
    </html>
  );
}
