"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV, SITE } from "@/lib/site";

import { GitHubIcon, PulseIcon } from "./Icons";

/** Encabezado fijo con la página activa marcada (aria-current para lectores de pantalla). */
export function SiteHeader() {
  const pathname = usePathname();
  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href.replace(/\/$/, ""));

  return (
    <header className="sticky top-0 z-20 border-b border-line bg-bg/85 backdrop-blur supports-[backdrop-filter]:bg-bg/70">
      <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3">
        <Link href="/" className="flex items-center gap-2 text-lg font-bold text-ink no-underline">
          <span className="grid size-7 place-items-center rounded-lg bg-accent text-white">
            <PulseIcon className="size-4" />
          </span>
          <span>
            Pana<span className="text-accent">Status</span>
          </span>
        </Link>
        <nav aria-label="Principal" className="flex items-center gap-1 text-sm">
          {NAV.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              aria-current={isActive(href) ? "page" : undefined}
              className="rounded-md px-2.5 py-1.5 text-muted no-underline transition-colors hover:bg-surface-2 hover:text-ink aria-[current=page]:bg-surface-2 aria-[current=page]:font-semibold aria-[current=page]:text-ink"
            >
              {label}
            </Link>
          ))}
          <a
            href={SITE.apiDocs}
            className="rounded-md px-2.5 py-1.5 text-muted no-underline transition-colors hover:bg-surface-2 hover:text-ink"
          >
            API
          </a>
          <a
            href={SITE.repoUrl}
            aria-label="Código fuente en GitHub"
            className="ml-1 rounded-md p-1.5 text-muted transition-colors hover:bg-surface-2 hover:text-ink"
          >
            <GitHubIcon className="size-[18px]" />
          </a>
        </nav>
      </div>
    </header>
  );
}
