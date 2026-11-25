"use client";

import Link from "next/link";
import useSWR from "swr";

import type { About, Service } from "@/lib/api";
import { fetcher } from "@/lib/api";

/**
 * Página para administradores de sitios que ven "PanaStatusBot" en sus registros.
 * El correo y el User-Agent vienen de /api/about (la misma configuración que usa el
 * checker), así esta página nunca contradice al bot real.
 */
export default function BotPage() {
  const about = useSWR<About>("/api/about", fetcher);
  const services = useSWR<Service[]>("/api/services", fetcher);

  const rows: [string, string][] = [
    ["Peticiones", "Una sola petición GET a una URL pública: la página de inicio o, en portales como Moodle o matrícula, la página pública de inicio de sesión. Nunca inicia sesión, nunca envía credenciales ni formularios."],
    ["Frecuencia", "Una petición cada 1 a 5 minutos por sitio (normalmente cada 3 minutos), unas 480 al día como máximo."],
    ["Contenido descargado", "Ninguno. Solo se leen los encabezados de la respuesta y se cierra la conexión."],
    ["Qué se mide", "Código de estado HTTP, tiempo de respuesta y fecha de vencimiento del certificado TLS (leída de la misma conexión, sin peticiones extra)."],
    ["Otras páginas", "No sigue enlaces ni rastrea el sitio. Solo sigue redirecciones HTTP (máx. 5)."],
    ["Datos publicados", "Disponibilidad, latencia e incidentes de caída. Nada del contenido del sitio."],
  ];

  return (
    <article className="mt-6 min-w-0 space-y-4 break-words">
      <h1 className="text-xl font-semibold">PanaStatusBot</h1>
      <p className="text-muted">
        Información para administradores de sitios web que ven este bot en sus registros.
      </p>

      <div className="rounded-xl border border-line bg-surface p-4">
        <p>
          <strong>
            PanaStatusBot es un monitor de disponibilidad público y sin fines de lucro.
          </strong>{" "}
          Comprueba si la página de inicio de servicios web usados en Panamá (bancos, entidades de
          gobierno, universidades y servicios globales) está en línea, y publica el resultado en{" "}
          <Link href="/">una página de estado</Link> para que la ciudadanía sepa si un problema es
          general o solo suyo.
        </p>
        <p className="mt-2">
          No es un rastreador (crawler), no busca vulnerabilidades y no recopila contenido.
        </p>
      </div>

      <h2 className="pt-2 text-lg font-semibold">Contacto</h2>
      <p className="text-lg">
        {about.data ? (
          <a href={`mailto:${about.data.contact}`}>{about.data.contact}</a>
        ) : (
          <span className="text-muted">cargando…</span>
        )}
      </p>
      <p>
        Escríbanos ante cualquier duda, para solicitar la exclusión de su sitio o para pedir que
        cambiemos la frecuencia o la URL revisada.
      </p>

      <h2 className="pt-2 text-lg font-semibold">Qué hace exactamente</h2>
      <div className="rounded-xl border border-line bg-surface p-4">
        <table className="w-full text-sm">
          <tbody>
            {rows.map(([k, v]) => (
              <tr key={k} className="border-b border-line align-top last:border-b-0">
                <td className="py-2 pr-4 font-semibold sm:whitespace-nowrap">{k}</td>
                <td className="py-2">{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 className="pt-2 text-lg font-semibold">Cómo identificarlo</h2>
      <p>Todas las peticiones llevan este User-Agent:</p>
      <pre className="rounded-lg bg-surface p-3 font-mono text-sm break-all whitespace-pre-wrap">
        {about.data?.user_agent ?? "PanaStatusBot/… (+…/bot/; …)"}
      </pre>

      <h2 className="pt-2 text-lg font-semibold">Solicitar la exclusión</h2>
      <p>
        Si prefiere que su sitio no sea monitoreado, escriba al correo de contacto indicando el
        dominio. <strong>Lo retiramos en un máximo de 48 horas</strong>, sin preguntas. También
        podemos reducir la frecuencia o revisar otra URL más liviana (por ejemplo, un endpoint de
        salud).
      </p>

      <h2 className="pt-2 text-lg font-semibold">Sitios monitoreados actualmente</h2>
      <ul className="list-disc pl-5">
        {services.data?.map((s) => (
          <li key={s.id}>
            {s.name} — <span className="text-muted">{new URL(s.url).host}</span>
          </li>
        )) ?? <li className="text-muted">Cargando…</li>}
      </ul>

      <hr className="border-line" />
      <h2 className="text-lg font-semibold">English summary</h2>
      <p>
        PanaStatusBot is a non-profit public uptime monitor for websites used in Panama. It sends a
        single <code>GET</code> request to one public URL per site every 1–5 minutes (≈480
        requests/day at most), reads only the response headers and TLS certificate expiry, and
        never logs in, crawls, or downloads page content. To opt out or adjust the frequency, email
        the address above; removals are honored within 48 hours.
      </p>
    </article>
  );
}
