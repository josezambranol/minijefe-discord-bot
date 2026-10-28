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
            notif_key = f"server_polish_v3_95dev_{guild.id}"
            if await has_notification_been_sent(notif_key):
                continue
            try:
                logger.info(f"Aplicando optimización y actualización de contenidos en '{guild.name}'...")
                await self.execute_server_polish(guild)
                await record_notification_sent(notif_key)
                logger.info(f"Optimización v3 completada exitosamente en '{guild.name}'.")
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

    @app_commands.command(
        name="pulir-servidor",
        description="Limpia mensajes antiguos, restaura roles, publica reglas extensas y optimiza canales (95% dev)"
    )
    @app_commands.default_permissions(administrator=True)
    async def slash_polish_server(self, interaction: discord.Interaction):
        """Comando directo para ejecutar el pulido integral del servidor."""
        if not interaction.guild:
            await interaction.response.send_message("Servidor no encontrado.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        lines = await self.execute_server_polish(interaction.guild, executor=interaction.user)

        embed = discord.Embed(
            title="Servidor Actualizado y Optimizado",
            description=(
                f"Se aplicaron las mejoras de estructura y contenido en **{interaction.guild.name}**:\n\n" +
                "\n".join(lines)
            ),
            color=COLOR_DARK
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="aplicar-en-canales-reales",
        description="Actualiza reglas, roles, bienvenida y plantillas en los canales del servidor borrando lo viejo"
    )
    @app_commands.default_permissions(administrator=True)
    async def apply_to_real_channels(self, interaction: discord.Interaction):
        """Alias de pulir-servidor para mantener compatibilidad."""
        await self.slash_polish_server.callback(self, interaction)

    @app_commands.command(
        name="limpiar-duplicados",
        description="Elimina las categorías y canales duplicados o redundantes del servidor"
    )
    @app_commands.default_permissions(administrator=True)
    async def clean_duplicates(self, interaction: discord.Interaction):
        """Ejecuta el pulido y limpieza de duplicados."""
        await self.slash_polish_server.callback(self, interaction)

    @app_commands.command(name="publicar-reglas", description="Limpia mensajes antiguos y publica el reglamento oficial extenso")
    @app_commands.describe(canal="Canal donde se publicarán las reglas (por defecto #reglas o el actual)")
    @app_commands.default_permissions(administrator=True)
    async def publish_rules(self, interaction: discord.Interaction, canal: Optional[discord.TextChannel] = None):
        await interaction.response.defer(ephemeral=True)
        target = canal or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.followup.send("Debes indicar un canal de texto válido.", ephemeral=True)
            return

        await purge_bot_messages(target)
        embeds = create_server_rules_embeds()
        try:
            for emb in embeds:
                await target.send(embed=emb)
            await interaction.followup.send(f"Reglamento oficial actualizado en {target.mention}.", ephemeral=True)
            await log_to_reports(
                guild=interaction.guild,
                title="Reglamento Oficial Actualizado",
                description=f"Se limpiaron mensajes previos y se publicó el reglamento extenso en {target.mention}.",
                action_type="setup",
                user=interaction.user
            )
        except Exception as e:
            await interaction.followup.send(f"Error al publicar reglas: {e}", ephemeral=True)

    @app_commands.command(name="plantilla-proyecto", description="Limpia plantillas anteriores y publica el estándar de proyectos")
    @app_commands.describe(enviar_al_canal="Si es True, publica y fija la plantilla en el canal actual")
    async def publish_project_template(self, interaction: discord.Interaction, enviar_al_canal: bool = True):
        await interaction.response.defer(ephemeral=True)
        embed = create_project_template_embed()
        if enviar_al_canal:
            if not interaction.user.guild_permissions.manage_messages:
                await interaction.followup.send("Se requieren permisos de gestión de mensajes.", ephemeral=True)
                return
            await purge_bot_messages(interaction.channel)
            msg = await interaction.channel.send(embed=embed)
            try:
                await msg.pin()
            except Exception:
                pass
            await interaction.followup.send("Estándar de proyectos actualizado en el canal.", ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="plantilla-roadmap", description="Limpia plantillas anteriores y publica la guía de roadmaps")
    @app_commands.describe(enviar_al_canal="Si es True, publica y fija la guía en el canal actual")
    async def publish_roadmap_template(self, interaction: discord.Interaction, enviar_al_canal: bool = True):
        await interaction.response.defer(ephemeral=True)
        embed = create_roadmap_template_embed()
        if enviar_al_canal:
            if not interaction.user.guild_permissions.manage_messages:
                await interaction.followup.send("Se requieren permisos de gestión de mensajes.", ephemeral=True)
                return
            await purge_bot_messages(interaction.channel)
            msg = await interaction.channel.send(embed=embed)
            try:
                await msg.pin()
            except Exception:
                pass
            await interaction.followup.send("Guía de roadmaps actualizada en el canal.", ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="plantilla-presentacion", description="Limpia plantillas anteriores y publica el formato de presentación")
    @app_commands.describe(enviar_al_canal="Si es True, publica y fija el formato en el canal actual")
    async def publish_presentation_template(self, interaction: discord.Interaction, enviar_al_canal: bool = True):
        await interaction.response.defer(ephemeral=True)
        embed = create_presentation_template_embed()
        if enviar_al_canal:
            if not interaction.user.guild_permissions.manage_messages:
                await interaction.followup.send("Se requieren permisos de gestión de mensajes.", ephemeral=True)
                return
            await purge_bot_messages(interaction.channel)
            msg = await interaction.channel.send(embed=embed)
            try:
                await msg.pin()
            except Exception:
                pass
            await interaction.followup.send("Formato de presentación actualizado en el canal.", ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CommunityCog(bot))
