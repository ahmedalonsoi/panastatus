"""Bot público de Telegram (python-telegram-bot).

Comandos:
    /start              bienvenida y ayuda
    /servicios          suscribirse/desuscribirse con botones (por categoría)
    /estado [servicio]  estado general, o detalle de un servicio
    /missuscripciones   qué servicios sigo
    /silencio [horas]   pausar avisos (por defecto 1 h; "/silencio off" para reanudar)
    /stop               borrar todos mis datos

Funciona en grupos: el chat_id es el del grupo y los avisos llegan al grupo. Para que
cualquiera del grupo no pueda cambiar la configuración, en grupos solo los
administradores pueden suscribir, silenciar o detener.

Este proceso solo atiende comandos. Los avisos los envía el worker (notifier.py).
"""

from __future__ import annotations

import html
import logging
from datetime import UTC, datetime, timedelta

import asyncpg
from telegram import (
    BotCommand,
    CallbackQuery,
    Chat,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update,
)
from telegram.constants import ChatMemberStatus, ChatType, ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    TypeHandler,
)

from panastatus import db, telemetry
from panastatus.config import PANAMA_TZ, get_settings, load_monitor_config
from panastatus.logging_setup import configure_logging
from panastatus.notifier import format_duration

log = logging.getLogger("panastatus.bot")

STATUS_EMOJI = {"up": "🟢", "degraded": "🟡", "down": "🔴", "unknown": "⚪"}
STATUS_TEXT = {"up": "operativo", "degraded": "lento", "down": "caído", "unknown": "sin datos"}

HELP = (
    "👋 <b>PanaStatus</b> vigila la disponibilidad de sitios web de Panamá "
    "(bancos, gobierno, universidades y servicios globales) y te avisa cuando se caen.\n\n"
    "/servicios — elegir qué servicios seguir\n"
    "/estado — estado de todos los servicios\n"
    "/estado <i>nombre</i> — detalle de uno (ej. <code>/estado utp</code>)\n"
    "/missuscripciones — lo que sigues\n"
    "/silencio <i>horas</i> — pausar avisos (<code>/silencio off</code> para reanudar)\n"
    "/stop — dejar de recibir avisos y borrar tus datos\n\n"
    "Solo guardamos el id de este chat y tus suscripciones."
)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def pool_of(context: ContextTypes.DEFAULT_TYPE) -> asyncpg.Pool:
    return context.application.bot_data["pool"]


def categories_of(context: ContextTypes.DEFAULT_TYPE) -> dict[str, str]:
    return context.application.bot_data["categories"]


# Accesos seguros al Update. Telegram tipa message/chat/callback_query como opcionales
# porque un Update puede ser de muchos tipos; los handlers de abajo solo se registran
# para comandos y botones, donde siempre existen. Si algún día no existen, el error es
# explícito (y queda en los logs) en vez de un AttributeError sobre None.


def message_of(update: Update) -> Message:
    if update.effective_message is None:
        raise RuntimeError("Update sin mensaje")
    return update.effective_message


def chat_of(update: Update) -> Chat:
    if update.effective_chat is None:
        raise RuntimeError("Update sin chat")
    return update.effective_chat


def query_of(update: Update) -> CallbackQuery:
    if update.callback_query is None:
        raise RuntimeError("Update sin callback_query")
    return update.callback_query


async def can_manage(update: Update) -> bool:
    """En chats privados siempre; en grupos solo administradores."""
    chat = chat_of(update)
    if chat.type == ChatType.PRIVATE:
        return True
    if update.effective_user is None:  # mensajes de canales anónimos: no gestionan
        return False
    member = await chat.get_member(update.effective_user.id)
    return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)


def fmt_pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.2f}%"


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await message_of(update).reply_text(HELP, parse_mode=ParseMode.HTML)


# ---------------------------------------------------------------------------
# /servicios + botones
#   callback_data:  "home"  |  "cat:<categoría>"  |  "tog:<servicio>"
# ---------------------------------------------------------------------------


def categories_keyboard(categories: dict[str, str]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(label, callback_data=f"cat:{key}")]
        for key, label in categories.items()
    ]
    return InlineKeyboardMarkup(rows)


async def services_keyboard(
    pool: asyncpg.Pool, chat_id: int, category: str
) -> InlineKeyboardMarkup:
    services = [s for s in await db.list_services(pool) if s["category"] == category]
    sub = await db.get_subscriber(pool, chat_id)
    subscribed = set(sub["services"]) if sub else set()
    rows = [
        [
            InlineKeyboardButton(
                f"{'✅' if s['id'] in subscribed else '➕'} {s['name']}",
                callback_data=f"tog:{s['id']}",
            )
        ]
        for s in services
    ]
    rows.append([InlineKeyboardButton("« Categorías", callback_data="home")])
    return InlineKeyboardMarkup(rows)


async def servicios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await message_of(update).reply_text(
        "Elige una categoría. Toca un servicio para seguirlo (✅) o dejar de seguirlo (➕).",
        reply_markup=categories_keyboard(categories_of(context)),
    )


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = query_of(update)
    pool = pool_of(context)
    chat_id = chat_of(update).id
    data = query.data or ""

    if data == "home":
        await query.answer()
        await query.edit_message_reply_markup(categories_keyboard(categories_of(context)))
        return

    if data.startswith("cat:"):
        await query.answer()
        keyboard = await services_keyboard(pool, chat_id, data.removeprefix("cat:"))
        await query.edit_message_reply_markup(keyboard)
        return

    if data.startswith("tog:"):
        if not await can_manage(update):
            await query.answer(
                "En grupos solo los administradores pueden cambiar las suscripciones.",
                show_alert=True,
            )
            return
        service_id = data.removeprefix("tog:")
        service = await db.get_service(pool, service_id)
        if service is None:
            await query.answer("Ese servicio ya no existe.", show_alert=True)
            return
        subscribed = await db.toggle_subscription(pool, chat_id, service_id)
        await query.answer(f"{'Suscrito a' if subscribed else 'Ya no sigues'} {service['name']}")
        keyboard = await services_keyboard(pool, chat_id, service["category"])
        await query.edit_message_reply_markup(keyboard)
        return

    await query.answer()


# ---------------------------------------------------------------------------
# /estado [servicio]
# ---------------------------------------------------------------------------


async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pool = pool_of(context)
    services = await db.list_services(pool)

    if not context.args:
        # Resumen de todos, agrupado por categoría
        lines: list[str] = []
        categories = categories_of(context)
        for key, label in categories.items():
            group = [s for s in services if s["category"] == key]
            if not group:
                continue
            lines.append(f"\n<b>{html.escape(label)}</b>")
            for s in group:
                lines.append(f"{STATUS_EMOJI[s['status']]} {html.escape(s['name'])}")
        down = sum(s["status"] == "down" for s in services)
        header = "✅ Todo operativo" if down == 0 else f"⚠️ {down} servicio(s) caído(s)"
        await message_of(update).reply_text(
            header + "\n" + "\n".join(lines) + "\n\nDetalle: /estado <i>nombre</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    # Buscar por id o por parte del nombre (sin importar mayúsculas)
    term = " ".join(context.args).lower()
    matches = [s for s in services if term == s["id"] or term in s["name"].lower()]
    if not matches:
        await message_of(update).reply_text(
            "No encontré ese servicio. Usa /estado para ver la lista."
        )
        return
    s = matches[0]
    uptime = await db.uptime_windows(pool, s["id"])

    lines = [
        f"{STATUS_EMOJI[s['status']]} <b>{html.escape(s['name'])}</b>: {STATUS_TEXT[s['status']]}"
    ]
    if s["down_since"]:
        down_for = datetime.now(UTC) - s["down_since"]
        lines.append(f"Caído hace {format_duration(down_for)}")
    if s["last_error"]:
        lines.append(f"Último error: {html.escape(s['last_error'])}")
    if s["last_latency_ms"] is not None:
        lines.append(f"Latencia: {s['last_latency_ms']} ms")
    lines.append(
        f"Disponibilidad: 24 h {fmt_pct(s['uptime_24h'])} · 7 d {fmt_pct(uptime['7d'])}"
        f" · 30 d {fmt_pct(uptime['30d'])}"
    )
    if s["ssl_days_left"] is not None:
        warn = " ⚠️" if s["ssl_days_left"] < 15 else ""
        lines.append(f"Certificado SSL: vence en {s['ssl_days_left']} días{warn}")
    if s["last_checked_at"]:
        lines.append(f"Revisado: {s['last_checked_at'].astimezone(PANAMA_TZ):%H:%M} (Panamá)")
    await message_of(update).reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# ---------------------------------------------------------------------------
# /missuscripciones, /silencio, /stop
# ---------------------------------------------------------------------------


async def missuscripciones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pool = pool_of(context)
    sub = await db.get_subscriber(pool, chat_of(update).id)
    if not sub or not sub["services"]:
        await message_of(update).reply_text(
            "No sigues ningún servicio. Usa /servicios para elegir."
        )
        return
    names = {s["id"]: s["name"] for s in await db.list_services(pool)}
    lines = [f"• {html.escape(names.get(sid, sid))}" for sid in sub["services"]]
    text = "<b>Sigues:</b>\n" + "\n".join(lines)
    if sub["muted_until"] and sub["muted_until"] > datetime.now(UTC):
        text += f"\n\n🔕 En silencio hasta las {sub['muted_until'].astimezone(PANAMA_TZ):%H:%M}"
    await message_of(update).reply_text(text, parse_mode=ParseMode.HTML)


async def silencio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await can_manage(update):
        await message_of(update).reply_text("Solo los administradores del grupo.")
        return
    chat_id = chat_of(update).id
    arg = context.args[0].lower().rstrip("h") if context.args else "1"

    if arg in ("off", "no", "0"):
        until, reply = None, "🔔 Avisos reactivados."
    else:
        try:
            hours = int(arg)
        except ValueError:
            await message_of(update).reply_text("Uso: /silencio 2  (horas, máx. 72)")
            return
        hours = max(1, min(hours, 72))
        until = datetime.now(UTC) + timedelta(hours=hours)
        reply = f"🔕 Sin avisos hasta las {until.astimezone(PANAMA_TZ):%H:%M}."

    if not await db.set_muted_until(pool_of(context), chat_id, until):
        reply = "No tienes suscripciones. Usa /servicios primero."
    await message_of(update).reply_text(reply)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await can_manage(update):
        await message_of(update).reply_text("Solo los administradores del grupo.")
        return
    await db.delete_subscriber(pool_of(context), chat_of(update).id)
    await message_of(update).reply_text(
        "Listo: borramos este chat de PanaStatus. No recibirás más avisos. "
        "Puedes volver cuando quieras con /servicios."
    )


# ---------------------------------------------------------------------------
# Arranque
# ---------------------------------------------------------------------------


async def post_init(app: Application) -> None:
    settings = get_settings()
    app.bot_data["pool"] = await db.create_pool(settings.database_url)
    app.bot_data["categories"] = load_monitor_config(settings.services_file).categories
    # Menú de comandos que Telegram muestra al escribir "/"
    await app.bot.set_my_commands(
        [
            BotCommand("servicios", "Elegir qué servicios seguir"),
            BotCommand("estado", "Estado de los servicios"),
            BotCommand("missuscripciones", "Ver lo que sigo"),
            BotCommand("silencio", "Pausar avisos por unas horas"),
            BotCommand("stop", "Dejar de recibir avisos y borrar mis datos"),
            BotCommand("start", "Ayuda"),
        ]
    )
    log.info("bot iniciado")


async def post_shutdown(app: Application) -> None:
    pool = app.bot_data.get("pool")
    if pool:
        await pool.close()


# ---------------------------------------------------------------------------
# Revisión de post-mortems (solo admin)
#   callback_data:  "pm:ok:<id>"  |  "pm:no:<id>"
# ---------------------------------------------------------------------------


async def on_postmortem_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = query_of(update)
    admin = get_settings().admin_chat_id
    # Solo el chat del admin puede aprobar. El mensaje solo se le envía a él, pero se
    # verifica igual: nunca confiar en que un botón llegue solo a quien debe.
    if admin is None or chat_of(update).id != admin:
        await query.answer("Solo el administrador puede revisar post-mortems.", show_alert=True)
        return
    _, action, raw_id = (query.data or "").split(":", 2)
    result = await db.review_postmortem(pool_of(context), int(raw_id), action == "ok")
    if result is None:
        await query.answer("Ese borrador ya fue revisado.", show_alert=True)
        return
    approved = result["status"] == "approved"
    await query.answer("Publicado" if approved else "Descartado")
    footer = (
        "\n\n✅ <b>Publicado</b> en la página de incidentes." if approved else "\n\n❌ Descartado."
    )
    # Un mensaje muy viejo puede ser "inaccesible" (sin texto): se usa cadena vacía.
    original = query.message.text if isinstance(query.message, Message) else None
    await query.edit_message_text(html.escape(original or "") + footer, parse_mode=ParseMode.HTML)


async def count_command(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cuenta cada comando para la métrica panastatus_bot_commands_total. Corre en el
    grupo -1 (antes que los handlers normales) y no corta el flujo."""
    if isinstance(update, Update) and update.effective_message:
        text = update.effective_message.text or ""
        if text.startswith("/"):
            # "/estado@PanaStatusBot utp" -> "estado"
            command = text.split()[0][1:].split("@")[0].lower()[:32]
            telemetry.bot_commands.add(1, {"command": command})


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("error en el bot", exc_info=context.error)


def main() -> None:
    configure_logging()
    telemetry.setup("bot")
    settings = get_settings()
    if not settings.telegram_bot_token:
        log.warning("TELEGRAM_BOT_TOKEN no definido; el bot no arranca.")
        return  # código de salida 0: Docker (restart: on-failure) no lo reinicia

    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    app.add_handler(TypeHandler(Update, count_command), group=-1)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("servicios", servicios))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("missuscripciones", missuscripciones))
    app.add_handler(CommandHandler("silencio", silencio))
    app.add_handler(CommandHandler("stop", stop))
    # El de post-mortems va antes: on_button atiende todo lo demás.
    app.add_handler(CallbackQueryHandler(on_postmortem_review, pattern=r"^pm:(ok|no):\d+$"))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_error_handler(on_error)

    # Long polling: el bot pregunta a Telegram por mensajes nuevos. No necesita una URL
    # pública ni HTTPS (a diferencia de un webhook), ideal para empezar.
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
