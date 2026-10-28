import discord
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from database import (
    get_guild_settings,
    update_guild_setting,
    log_bot_activity,
    get_activities_since,
    get_activity_stats_since,
    get_active_periodic_reminders
)
from utils.ai_service import generate_daily_system_report
from utils.embeds import (
    COLOR_INFO,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_DANGER,
    COLOR_PRIMARY
)

logger = logging.getLogger("MiniJefe.Reporting")

ACTION_STYLES = {
    "setup": ("🚀 Implementación / Setup", COLOR_SUCCESS),
    "moderacion": ("🧹 Moderación / Purga", COLOR_WARNING),
    "roles": ("🎭 Gestión de Roles", 0x9B59B6),
    "recordatorio": ("📋 Tareas & Recordatorios", COLOR_INFO),
    "bienvenida": ("👋 Bienvenida de Miembro", COLOR_PRIMARY),
    "config": ("⚙️ Configuración del Servidor", 0x1ABC9C),
    "autonomo": ("🤖 Actividad Autónoma", 0x34495E),
    "sistema": ("🟢 Notificación del Sistema", COLOR_SUCCESS)
}

async def get_or_create_reports_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    """
    Localiza o crea automáticamente el canal #reportes del servidor:
    1. Verifica si ya está configurado en guild_settings.
    2. Busca un canal existente con nombre similar ('reportes', 'reporte', 'logs-bot', 'auditoria').
    3. Si no existe y el bot tiene permisos de Manage Channels, lo crea con permisos de solo lectura para miembros.
    """
    # 1. Configuración previa en DB
    try:
        settings = await get_guild_settings(guild.id)
        saved_id = settings.get("reports_channel_id")
        if saved_id:
            ch = guild.get_channel(saved_id)
            if ch and isinstance(ch, discord.TextChannel) and ch.permissions_for(guild.me).send_messages:
                return ch
    except Exception as e:
        logger.warning(f"Error consultando reports_channel_id en {guild.name}: {e}")

    # 2. Buscar en canales de texto existentes
    for ch in guild.text_channels:
        clean = ch.name.lower().replace("-", "").replace("_", "")
        if any(term in clean for term in ["reportes", "reporte", "auditoria", "logsbot", "bitacora"]):
            if ch.permissions_for(guild.me).send_messages:
                try:
                    await update_guild_setting(guild.id, "reports_channel_id", ch.id)
                except Exception:
                    pass
                return ch

    # 3. Crear automáticamente el canal #reportes si hay permisos
    if guild.me.guild_permissions.manage_channels:
        try:
            # Buscar categoría recomendada ("Inicio", "Administración", "Staff")
            category = (
                discord.utils.get(guild.categories, name="Inicio") or
                discord.utils.get(guild.categories, name="Administración") or
                discord.utils.get(guild.categories, name="Staff")
            )

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=False,
                    read_message_history=True,
                    add_reactions=True
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    embed_links=True,
                    attach_files=True,
                    manage_messages=True
                )
            }

            new_ch = await guild.create_text_channel(
                name="reportes",
                category=category,
                topic="📋 Registro oficial de cambios, implementaciones, auditoría y reportes diarios automáticos de MiniJefe.",
                overwrites=overwrites,
                reason="MiniJefe: Creación automática del canal de reportes y auditoría"
            )

            try:
                await update_guild_setting(guild.id, "reports_channel_id", new_ch.id)
            except Exception:
                pass

            # Enviar mensaje de inicialización
            init_embed = discord.Embed(
                title="📋 Canal de Reportes Oficial de MiniJefe",
                description=(
                    f"¡Canal inicializado con éxito en **{guild.name}**!\n\n"
                    f"A partir de este momento, MiniJefe registrará aquí:\n"
                    f"• 🚀 **Implementaciones y cambios**: Creación de canales, categorías, plantillas y roles.\n"
                    f"• 🧹 **Acciones de moderación**: Limpieza de chat, mitigación de spam y filtros.\n"
                    f"• 🎭 **Auditoría de roles**: Asignaciones y modificaciones del panel.\n"
                    f"• 📋 **Tareas y recordatorios**: Altas, finalizaciones y cancelaciones.\n"
                    f"• 📊 **Reporte Diario Autónomo**: Resumen diario de todas las operaciones realizadas por el bot por su cuenta."
                ),
                color=COLOR_SUCCESS
            )
            init_embed.set_footer(text=f"Servidor: {guild.name} • MiniJefe Auditoría")
            await new_ch.send(embed=init_embed)

            logger.info(f"Canal #reportes creado automáticamente en {guild.name}")
            return new_ch
        except Exception as e:
            logger.error(f"No se pudo crear automáticamente el canal #reportes en {guild.name}: {e}")

    # Fallback
    return guild.system_channel if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages else None

async def log_to_reports(
    guild: discord.Guild,
    title: str,
    description: str,
    action_type: str = "sistema",
    user: Optional[discord.User | discord.Member] = None,
    fields: Optional[List[tuple]] = None,
    color: Optional[int] = None
) -> Optional[discord.Message]:
    """
    Registra una acción tanto en la base de datos como en el canal oficial #reportes.
    Garantiza trazabilidad completa de todo cambio que realice o implemente MiniJefe.
    """
    if not guild:
        return None

    # 1. Guardar en SQLite para persistencia y estadísticas diarias
    try:
        user_id = user.id if user else None
        await log_bot_activity(
            guild_id=guild.id,
            action_type=action_type,
            title=title,
            description=description,
            user_id=user_id
        )
    except Exception as e:
        logger.warning(f"Error al guardar log_bot_activity en DB: {e}")

    # 2. Localizar canal #reportes
    report_ch = await get_or_create_reports_channel(guild)
    if not report_ch or not report_ch.permissions_for(guild.me).send_messages:
        return None

    # 3. Estilo visual según tipo de acción
    category_title, default_color = ACTION_STYLES.get(action_type, ("📋 Registro de Actividad", COLOR_INFO))
    final_color = color or default_color

    embed = discord.Embed(
        title=f"{category_title}: {title}",
        description=description,
        color=final_color,
        timestamp=datetime.now(timezone.utc)
    )

    if user:
        embed.add_field(name="👤 Responsable / Usuario", value=f"{user.mention} (`{user.display_name}`)", inline=True)

    if fields:
        for f_name, f_val, f_inline in fields:
            embed.add_field(name=f_name, value=str(f_val)[:1024], inline=f_inline)

    embed.set_footer(text=f"Servidor: {guild.name} • MiniJefe Auditoría")

    try:
        msg = await report_ch.send(embed=embed)
        return msg
    except Exception as e:
        logger.error(f"Error enviando mensaje a #reportes en {guild.name}: {e}")
        return None

async def build_daily_autonomous_report_embed(guild: discord.Guild, bot: discord.Client) -> discord.Embed:
    """
    Compila el informe diario de todo lo que MiniJefe realizó de manera autónoma
    o coordinada durante las últimas 24 horas en el servidor.
    """
    now_utc = datetime.now(timezone.utc)
    since_24h = (now_utc - timedelta(hours=24)).isoformat()

    # 1. Estadísticas de actividad
    stats = await get_activity_stats_since(guild.id, since_24h)
    recent_activities = await get_activities_since(guild.id, since_24h)
    active_reminders = await get_active_periodic_reminders(guild.id)

    reminders_sent = stats.get("autonomous_reminder", 0)
    moderation_actions = stats.get("moderacion", 0)
    welcomes_count = stats.get("bienvenida", 0)
    tasks_created = stats.get("recordatorio", 0)
    roles_changes = stats.get("roles", 0)
    setup_actions = stats.get("setup", 0)

    stats_dict = {
        "reminders_sent": reminders_sent,
        "active_reminders": len(active_reminders),
        "moderation_actions": moderation_actions,
        "welcomes_count": welcomes_count,
        "tasks_created": tasks_created,
        "roles_changes": roles_changes
    }

    # 2. Resumen de actividades destacadas para la IA
    activity_bullets = []
    for act in recent_activities[:10]:
        activity_bullets.append(f"{act['title']}: {act['description']}")

    # 3. Generación con IA
    ai_brief = await generate_daily_system_report(guild.name, stats_dict, activity_bullets)

    # 4. Salud del sistema y métricas
    latency_ms = round(bot.latency * 1000) if bot.latency else 0

    embed = discord.Embed(
        title=f"📊 Informe Diario de Operaciones Autónomas — MiniJefe",
        description=(
            f"**Balance Operativo del Servidor:**\n> {ai_brief}\n\n"
            f"A continuación se detalla la actividad autónoma y administrativa procesada en **{guild.name}** en las últimas 24 horas:"
        ),
        color=COLOR_SUCCESS,
        timestamp=now_utc
    )

    embed.add_field(
        name="⏰ Tareas y Recordatorios Autónomos",
        value=(
            f"• **Avisos automáticos enviados:** `{reminders_sent}`\n"
            f"• **Tareas actualmente en seguimiento:** `{len(active_reminders)}`\n"
            f"• **Nuevos recordatorios agendados:** `{tasks_created}`"
        ),
        inline=False
    )

    embed.add_field(
        name="🧹 Moderación y Salud de Canales",
        value=(
            f"• **Intervenciones de purga / spam:** `{moderation_actions}`\n"
            f"• **Protección Anti-Spam:** Activa y protegiendo canales"
        ),
        inline=True
    )

    embed.add_field(
        name="👥 Comunidad & Roles",
        value=(
            f"• **Bienvenidas procesadas (tarjetas dev):** `{welcomes_count}`\n"
            f"• **Actualizaciones de roles dev:** `{roles_changes}`"
        ),
        inline=True
    )

    embed.add_field(
        name="⚡ Estado del Sistema & Conectividad",
        value=(
            f"• **Latencia Gateway Discord:** `{latency_ms} ms`\n"
            f"• **Base de Datos SQLite:** Conectada y nominal ✅\n"
            f"• **Servidor Web Healthcheck:** Activo 24/7 🟢"
        ),
        inline=False
    )

    if recent_activities:
        recent_lines = []
        for a in recent_activities[:6]:
            icon = ACTION_STYLES.get(a["action_type"], ("•", 0))[0].split()[0]
            clean_desc = (a["description"][:75] + "...") if len(a["description"]) > 75 else a["description"]
            recent_lines.append(f"{icon} **{a['title']}**: {clean_desc}")
        embed.add_field(
            name="📜 Registro Cronológico Reciente",
            value="\n".join(recent_lines),
            inline=False
        )

    embed.set_footer(text=f"Servidor: {guild.name} • MiniJefe Operaciones Autónomas")
    return embed
