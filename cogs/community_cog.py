import discord
from discord.ext import commands
from discord import app_commands
import logging
import unicodedata
import re
from typing import Optional, List

from database import (
    update_guild_setting,
    has_notification_been_sent,
    record_notification_sent
)
from utils.embeds import (
    create_server_rules_embeds,
    create_project_template_embed,
    create_roadmap_template_embed,
    create_presentation_template_embed,
    create_roles_panel_embed,
    COLOR_SUCCESS,
    COLOR_PRIMARY,
    COLOR_INFO,
    COLOR_DARK
)
from utils.reporting import log_to_reports, get_or_create_reports_channel
from cogs.roles_cog import (
    RolesPanelView,
    ensure_all_managed_roles,
    deploy_clean_roles_panel
)

logger = logging.getLogger("MiniJefe.Community")


def normalize_text(text: str) -> str:
    """Remueve emojis, tildes y caracteres especiales para comparar nombres de canales y categorías."""
    n = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8').lower()
    return re.sub(r'[^a-z0-9]', '', n)


def find_category_smart(guild: discord.Guild, keywords: List[str]) -> Optional[discord.CategoryChannel]:
    """Localiza la categoría principal que coincida con las palabras clave."""
    candidates = []
    for cat in guild.categories:
        c_clean = normalize_text(cat.name)
        if any(k in c_clean for k in keywords):
            candidates.append(cat)
    if not candidates:
        return None
    # Priorizar la categoría original con más canales establecidos
    candidates.sort(key=lambda c: (len(c.channels), any(sym in c.name for sym in ["📌", "💻", "📚", "💬", "🎮"])), reverse=True)
    return candidates[0]


def find_channel_smart(
    guild: discord.Guild,
    keywords: List[str],
    preferred_category: Optional[discord.CategoryChannel] = None
) -> Optional[discord.TextChannel]:
    """Busca un canal de texto priorizando la categoría indicada."""
    if preferred_category:
        for ch in preferred_category.text_channels:
            c_clean = normalize_text(ch.name)
            if any(k in c_clean for k in keywords):
                return ch
    candidates = []
    for ch in guild.text_channels:
        c_clean = normalize_text(ch.name)
        if any(k in c_clean for k in keywords):
            candidates.append(ch)
    if not candidates:
        return None
    candidates.sort(
        key=lambda ch: (ch.category_id == (preferred_category.id if preferred_category else None)),
        reverse=True
    )
    return candidates[0]


async def purge_bot_messages(channel: discord.TextChannel, limit: int = 40) -> int:
    """Elimina los mensajes anteriores enviados por el bot en un canal para reemplazarlos por versiones limpias."""
    deleted = 0
    guild = channel.guild
    try:
        async for msg in channel.history(limit=limit):
            if msg.author.id == guild.me.id:
                try:
                    await msg.delete()
                    deleted += 1
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"No se pudo limpiar historial del bot en #{channel.name}: {e}")
    return deleted


class CommunityCog(commands.Cog, name="Comunidad y Recursos"):
    """Gestión de arquitectura del servidor, reglamento, plantillas técnicas y optimización de canales."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._startup_polish_done = False

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Al iniciar la nueva versión, aplica automáticamente la limpieza de mensajes antiguos,
        restauración del panel de roles, actualización de reglas extensas y reducción de canales redundantes.
        """
        if self._startup_polish_done:
            return
        self._startup_polish_done = True

        for guild in self.bot.guilds:
            notif_key = f"server_polish_v6_ceo_voice_{guild.id}"
            if await has_notification_been_sent(notif_key):
                continue
            try:
                logger.info(f"Aplicando optimización, canales CEO y actualización en '{guild.name}'...")
                await self.execute_server_polish(guild)
                await record_notification_sent(notif_key)
                logger.info(f"Optimización v6 completada exitosamente en '{guild.name}'.")
            except Exception as e:
                logger.error(f"Error aplicando optimización automática en '{guild.name}': {e}", exc_info=True)

    async def execute_server_polish(self, guild: discord.Guild, executor: Optional[discord.User | discord.Member] = None) -> List[str]:
        """
        Ejecuta la restructuración y pulido integral del servidor:
        1. Elimina categorías/canales duplicados y reduce canales de juegos para mantener enfoque 95% programación / 5% juegos.
        2. Borra mensajes antiguos del bot en reglas, roles, presentaciones, proyectos y roadmaps.
        3. Publica el nuevo reglamento extenso sin ruido visual y restaura el panel de roles corregido.
        4. Oculta #reportes al público general para reducir saturación visual (solo visible para Administración y el bot).
        """
        report_lines = []

        # -------------------------------------------------------------
        # 1. ELIMINAR CATEGORÍAS Y CANALES DUPLICADOS O SOBRANTES
        # -------------------------------------------------------------
        cat_inicio = find_category_smart(guild, ["inicio"])
        cat_desarrollo = find_category_smart(guild, ["desarrollo", "programacion", "dev", "codigo"])
        cat_estudio = find_category_smart(guild, ["estudio", "aprendizaje"])
        cat_gaming = find_category_smart(guild, ["gaming", "juego", "recreacion"])

        # Eliminar categorías duplicadas ("Inicio", "Estudio" sin canales originales)
        for cat in list(guild.categories):
            is_dup_inicio = (cat_inicio and cat.id != cat_inicio.id and normalize_text(cat.name) == "inicio")
            is_dup_estudio = (cat_estudio and cat.id != cat_estudio.id and normalize_text(cat.name) == "estudio")
            if is_dup_inicio or is_dup_estudio or cat.name.strip() in ["Inicio", "Estudio"]:
                # Solo borrar si no es la categoría principal seleccionada
                if (cat_inicio and cat.id == cat_inicio.id) or (cat_estudio and cat.id == cat_estudio.id):
                    continue
                for ch in list(cat.channels):
                    try:
                        await ch.delete(reason="Limpieza de canales duplicados")
                        report_lines.append(f"- Eliminado canal duplicado `#{ch.name}`")
                    except Exception:
                        pass
                try:
                    await cat.delete(reason="Limpieza de categoría duplicada")
                    report_lines.append(f"- Eliminada categoría duplicada `{cat.name}`")
                except Exception:
                    pass

        # Eliminar canal #proyectos-colaboracion suelto si ya existe #proyectos en DESARROLLO
        ch_proyectos_real = find_channel_smart(guild, ["proyecto"], preferred_category=cat_desarrollo)
        for ch in list(guild.channels):
            if normalize_text(ch.name) == "proyectoscolaboracion" and ch_proyectos_real and ch.id != ch_proyectos_real.id:
                try:
                    await ch.delete(reason="Unificación con el canal principal de proyectos en Desarrollo")
                    report_lines.append(f"- Eliminado canal redundante `#{ch.name}` (se usa {ch_proyectos_real.mention})")
                except Exception:
                    pass

        # -------------------------------------------------------------
        # 2. REDUCIR SATURACIÓN EN GAMING (ENFOQUE 95% PROGRAMACIÓN / 5% JUEGOS)
        # -------------------------------------------------------------
        if cat_gaming:
            for ch in list(cat_gaming.channels):
                c_norm = normalize_text(ch.name)
                # Eliminar canales secundarios de gaming que saturan la barra lateral (buscar-equipo, Duo, Squad)
                if any(extra in c_norm for extra in ["buscarequipo", "duo", "squad"]):
                    try:
                        await ch.delete(reason="Optimización de volumen: enfoque 95% programación / 5% juegos")
                        report_lines.append(f"- Reducido canal secundario de juegos `{ch.name}`")
                    except Exception:
                        pass

        # -------------------------------------------------------------
        # 3. ACTUALIZAR CATEGORÍA INICIO (REGLAS, ROLES, BIENVENIDA, PRESENTACIONES)
        # -------------------------------------------------------------
        if not cat_inicio:
            cat_inicio = await guild.create_category(name="INICIO", reason="Estructura base del servidor")

        # 3.1 Canal de Reglas (Borrar mensajes viejos y publicar reglamento extenso sin ruido)
        ch_reglas = find_channel_smart(guild, ["regla", "rules"], preferred_category=cat_inicio)
        if not ch_reglas:
            ch_reglas = await guild.create_text_channel(name="reglas", category=cat_inicio)
        await purge_bot_messages(ch_reglas)
        for emb in create_server_rules_embeds():
            await ch_reglas.send(embed=emb)
        report_lines.append(f"- Reglamento extenso actualizado en {ch_reglas.mention} (mensajes antiguos eliminados)")

        # 3.2 Canal de Roles (Restaurar mensaje de roles borrado, limpiar viejos y verificar roles técnicos)
        ch_roles = find_channel_smart(guild, ["role", "rol"], preferred_category=cat_inicio)
        if not ch_roles:
            ch_roles = await guild.create_text_channel(name="roles", category=cat_inicio)
        await deploy_clean_roles_panel(ch_roles)
        report_lines.append(f"- Panel de roles técnicos restaurado y actualizado en {ch_roles.mention}")

        # 3.3 Canal de Bienvenida
        ch_bienvenida = find_channel_smart(guild, ["bienvenid", "welcome"], preferred_category=cat_inicio)
        if ch_bienvenida:
            await update_guild_setting(guild.id, "welcome_channel_id", ch_bienvenida.id)
            report_lines.append(f"- Canal de bienvenida vinculado en {ch_bienvenida.mention}")

        # 3.4 Canal de Presentaciones (Sin caracteres raros ni exceso de emojis)
        ch_pres = find_channel_smart(guild, ["presentaci", "presentat"], preferred_category=cat_inicio)
        if not ch_pres:
            ch_pres = await guild.create_text_channel(
                name="presentaciones",
                category=cat_inicio,
                topic="Presentación de integrantes de la comunidad de desarrollo"
            )
        else:
            # Si tenía caracteres raros o emojis en el nombre recién creado, limpiarlo a 'presentaciones'
            if "presentaciones" in normalize_text(ch_pres.name) and ch_pres.name != "presentaciones":
                try:
                    await ch_pres.edit(name="presentaciones", category=cat_inicio)
                except Exception:
                    pass
        await purge_bot_messages(ch_pres)
        pres_msg = await ch_pres.send(embed=create_presentation_template_embed())
        try:
            await pres_msg.pin()
        except Exception:
            pass
        report_lines.append(f"- Plantilla de presentaciones actualizada en {ch_pres.mention}")

        # -------------------------------------------------------------
        # 4. ACTUALIZAR PROYECTOS EN DESARROLLO
        # -------------------------------------------------------------
        ch_proyectos = find_channel_smart(guild, ["proyecto"], preferred_category=cat_desarrollo)
        if ch_proyectos:
            await purge_bot_messages(ch_proyectos)
            proj_msg = await ch_proyectos.send(embed=create_project_template_embed())
            try:
                await proj_msg.pin()
            except Exception:
                pass
            report_lines.append(f"- Estándar de proyectos actualizado y fijado en {ch_proyectos.mention}")

        # -------------------------------------------------------------
        # 5. ACTUALIZAR ROADMAPS EN ESTUDIO
        # -------------------------------------------------------------
        if cat_estudio:
            ch_roadmaps = find_channel_smart(guild, ["roadmap", "ruta"], preferred_category=cat_estudio)
            if not ch_roadmaps:
                ch_roadmaps = await guild.create_text_channel(
                    name="roadmaps",
                    category=cat_estudio,
                    topic="Rutas de aprendizaje y planes de estudio técnico"
                )
            else:
                if ch_roadmaps.name != "roadmaps":
                    try:
                        await ch_roadmaps.edit(name="roadmaps", category=cat_estudio)
                    except Exception:
                        pass
            await purge_bot_messages(ch_roadmaps)
            road_msg = await ch_roadmaps.send(embed=create_roadmap_template_embed())
            try:
                await road_msg.pin()
            except Exception:
                pass
            report_lines.append(f"- Guía de roadmaps actualizada en {ch_roadmaps.mention}")

        # -------------------------------------------------------------
        # 6. CANAL DE REPORTES PRIVADO PARA STAFF (SIN RUIDO PARA MIEMBROS)
        # -------------------------------------------------------------
        ch_reportes = await get_or_create_reports_channel(guild)
        if ch_reportes:
            try:
                await ch_reportes.set_permissions(
                    guild.default_role,
                    view_channel=False,
                    send_messages=False
                )
            except Exception:
                pass
            report_lines.append(f"- Canal de auditoría {ch_reportes.mention} configurado como privado para Administración")

        # -------------------------------------------------------------
        # 7. CANALES DE VOZ PRIVADOS PARA CEO (JORDY Y RANGO CEO)
        # -------------------------------------------------------------
        # 7.1 Buscar o crear rol 'CEO'
        ceo_role = discord.utils.find(lambda r: r.name.lower() == "ceo", guild.roles)
        if not ceo_role and guild.me.guild_permissions.manage_roles:
            try:
                ceo_role = await guild.create_role(
                    name="CEO",
                    color=discord.Color(0xD4AF37),
                    hoist=True,
                    mentionable=False,
                    reason="Rol para dirección ejecutiva y canales privados"
                )
                report_lines.append(f"- Creado rol ejecutivo `{ceo_role.name}`")
            except Exception as e:
                logger.warning(f"No se pudo crear rol CEO: {e}")

        # 7.2 Localizar a Jordy si está en el servidor
        jordy_member = None
        for m in guild.members:
            if "jordy" in m.name.lower() or "jordy" in m.display_name.lower():
                jordy_member = m
                break
        if not jordy_member and guild.owner:
            jordy_member = guild.owner

        if jordy_member and ceo_role and ceo_role not in jordy_member.roles:
            try:
                if guild.me.guild_permissions.manage_roles and ceo_role < guild.me.top_role:
                    await jordy_member.add_roles(ceo_role, reason="Asignación de rol CEO")
                    report_lines.append(f"- Rol `{ceo_role.name}` asignado a {jordy_member.mention}")
            except Exception:
                pass

        # 7.3 Permisos privados: ocultos para @everyone, visibles y conectables para CEO y Jordy
        ceo_overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True)
        }
        if ceo_role:
            ceo_overwrites[ceo_role] = discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                stream=True
            )
        if jordy_member:
            ceo_overwrites[jordy_member] = discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                stream=True
            )

        # 7.4 Categoría privada DIRECCIÓN
        cat_staff = find_category_smart(guild, ["direccion", "staff", "admin", "ejecutivo", "gerencia"])
        if not cat_staff and guild.me.guild_permissions.manage_channels:
            try:
                cat_staff = await guild.create_category(
                    name="DIRECCIÓN",
                    overwrites=ceo_overwrites,
                    reason="Categoría privada para rango CEO y dirección"
                )
                report_lines.append(f"- Creada categoría privada `{cat_staff.name}`")
            except Exception:
                cat_staff = None

        # 7.5 Canal de voz 1: Máximo 5 personas
        v5_name = "Reunión CEO"
        v5_channel = discord.utils.find(
            lambda c: isinstance(c, discord.VoiceChannel) and ("reunion ceo" in c.name.lower() or "ceo (5" in c.name.lower() or c.name == v5_name),
            guild.voice_channels
        )
        if not v5_channel and guild.me.guild_permissions.manage_channels:
            try:
                v5_channel = await guild.create_voice_channel(
                    name=v5_name,
                    category=cat_staff,
                    user_limit=5,
                    overwrites=ceo_overwrites,
                    reason="Canal de voz privado para CEOs (máximo 5 personas)"
                )
                report_lines.append(f"- Creado canal de voz privado `{v5_channel.name}` (límite: 5 personas, solo rango CEO)")
            except Exception as e:
                logger.warning(f"Error creando canal de voz 5p: {e}")
        elif v5_channel:
            try:
                await v5_channel.edit(user_limit=5, overwrites=ceo_overwrites, category=cat_staff or v5_channel.category)
            except Exception:
                pass

        # 7.6 Canal de voz 2: Máximo 2 personas
        v2_name = "Despacho CEO"
        v2_channel = discord.utils.find(
            lambda c: isinstance(c, discord.VoiceChannel) and ("despacho ceo" in c.name.lower() or "ceo (2" in c.name.lower() or c.name == v2_name),
            guild.voice_channels
        )
        if not v2_channel and guild.me.guild_permissions.manage_channels:
            try:
                v2_channel = await guild.create_voice_channel(
                    name=v2_name,
                    category=cat_staff,
                    user_limit=2,
                    overwrites=ceo_overwrites,
                    reason="Canal de voz privado para CEOs (máximo 2 personas)"
                )
                report_lines.append(f"- Creado canal de voz privado `{v2_channel.name}` (límite: 2 personas, solo rango CEO)")
            except Exception as e:
                logger.warning(f"Error creando canal de voz 2p: {e}")
        elif v2_channel:
            try:
                await v2_channel.edit(user_limit=2, overwrites=ceo_overwrites, category=cat_staff or v2_channel.category)
            except Exception:
                pass

        # Registrar en #reportes
        try:
            await log_to_reports(
                guild=guild,
                title="Reestructuración y Pulido del Servidor (Enfoque 95% Programación)",
                description="\n".join(report_lines),
                action_type="setup",
                user=executor
            )
        except Exception as e:
            logger.warning(f"Error registrando pulido en #reportes: {e}")

        return report_lines


async def setup(bot: commands.Bot):
    await bot.add_cog(CommunityCog(bot))
