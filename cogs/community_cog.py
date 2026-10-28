import discord
from discord.ext import commands
from discord import app_commands
import logging
import unicodedata
import re
from typing import Optional, List

from database import update_guild_setting
from utils.embeds import (
    create_server_rules_embeds,
    create_project_template_embed,
    create_roadmap_template_embed,
    create_presentation_template_embed,
    create_roles_panel_embed,
    COLOR_SUCCESS,
    COLOR_PRIMARY,
    COLOR_INFO
)
from utils.reporting import log_to_reports, get_or_create_reports_channel
from cogs.roles_cog import (
    SPECIALTY_NAMES,
    LANGUAGE_NAMES,
    NOTIFICATION_NAMES,
    RolesPanelView
)

logger = logging.getLogger("MiniJefe.Community")

def normalize_text(text: str) -> str:
    """Remueve emojis, tildes y caracteres especiales para comparar nombres de canales/categorías."""
    n = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8').lower()
    return re.sub(r'[^a-z0-9]', '', n)

def find_category_smart(guild: discord.Guild, keywords: List[str]) -> Optional[discord.CategoryChannel]:
    """Busca una categoría priorizando aquellas con emojis o decoraciones existentes (ej: 📌 INICIO)."""
    candidates = []
    for cat in guild.categories:
        c_clean = normalize_text(cat.name)
        if any(k in c_clean for k in keywords):
            candidates.append(cat)
    if not candidates:
        return None
    candidates.sort(key=lambda c: (any(sym in c.name for sym in ["📌", "★", "🔥", "🚀", "📢", "📚"]), len(c.channels)), reverse=True)
    return candidates[0]

def find_channel_smart(guild: discord.Guild, keywords: List[str], preferred_category: Optional[discord.CategoryChannel] = None) -> Optional[discord.TextChannel]:
    """Busca un canal de texto priorizando la categoría preferida y nombres con emojis existentes."""
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
    candidates.sort(key=lambda ch: (ch.category_id == (preferred_category.id if preferred_category else None), any(sym in ch.name for sym in ["📜", "🎭", "👋", "💬", "📢", "📋", "📚"])), reverse=True)
    return candidates[0]

class CommunityCog(commands.Cog, name="Comunidad y Recursos"):
    """Comandos para desplegar reglas, plantillas de proyectos, roadmaps, presentaciones y auto-setup."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="setup-comunidad-completo",
        description="Construye y configura automáticamente todos los canales, categorías, plantillas y roles dev"
    )
    @app_commands.default_permissions(administrator=True)
    async def auto_setup_community(self, interaction: discord.Interaction):
        """
        Automatización integral:
        1. Crea la categoría 'Inicio' con #reglas, #roles, #presentaciones y #bienvenidas.
        2. Crea la categoría 'Estudio' con #roadmaps-personales.
        3. Crea el canal/foro de #proyectos-colaboracion con tags y plantilla fijada.
        4. Crea los 19 roles dev y despliega los paneles interactivos sin latencia.
        """
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("❌ Servidor no encontrado.", ephemeral=True)
            return

        bot_member = guild.me
        if not bot_member.guild_permissions.manage_channels or not bot_member.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ El bot requiere los permisos de **Gestionar Canales** (`Manage Channels`) y **Gestionar Roles** (`Manage Roles`) para ejecutar la configuración automática.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        report_lines = []

        # -------------------------------------------------------------
        # 1. CATEGORÍA "INICIO" (Reconoce '📌 INICIO' o categoría decorada)
        # -------------------------------------------------------------
        cat_inicio = find_category_smart(guild, ["inicio"])
        if not cat_inicio:
            cat_inicio = await guild.create_category(name="📌 INICIO", reason="MiniJefe: Setup de comunidad")
            report_lines.append(f"📁 Creada categoría **{cat_inicio.name}**")
        else:
            report_lines.append(f"📁 Categoría principal detectada: **{cat_inicio.name}**")

        # Canal #reglas (Reconoce '📜 · reglas' existente)
        ch_reglas = find_channel_smart(guild, ["regla", "rules"], preferred_category=cat_inicio)
        if not ch_reglas:
            ch_reglas = await guild.create_text_channel(name="📜・reglas", category=cat_inicio, reason="MiniJefe Setup")
            for emb in create_server_rules_embeds():
                await ch_reglas.send(embed=emb)
            report_lines.append(f"  • Creado canal {ch_reglas.mention} con reglamento oficial publicado")
        else:
            # Publicar el reglamento dev en el canal existente
            for emb in create_server_rules_embeds():
                await ch_reglas.send(embed=emb)
            report_lines.append(f"  • Desplegado reglamento oficial en tu canal existente {ch_reglas.mention}")

        # Canal #roles (Reconoce '🎭 · roles' existente)
        ch_roles = find_channel_smart(guild, ["role", "rol"], preferred_category=cat_inicio)
        if not ch_roles:
            ch_roles = await guild.create_text_channel(name="🎭・roles", category=cat_inicio, reason="MiniJefe Setup")
            panel_embed = create_roles_panel_embed()
            await ch_roles.send(embed=panel_embed, view=RolesPanelView())
            report_lines.append(f"  • Creado canal {ch_roles.mention} con selector interactivo de roles")
        else:
            panel_embed = create_roles_panel_embed()
            await ch_roles.send(embed=panel_embed, view=RolesPanelView())
            report_lines.append(f"  • Desplegado selector de roles interactivo en tu canal existente {ch_roles.mention}")

        # Canal #bienvenida (Reconoce '👋 · bienvenida' existente)
        ch_bienvenidas = find_channel_smart(guild, ["bienvenid", "welcome"], preferred_category=cat_inicio)
        if not ch_bienvenidas:
            ch_bienvenidas = await guild.create_text_channel(name="👋・bienvenida", category=cat_inicio, reason="MiniJefe Setup")
            report_lines.append(f"  • Creado canal {ch_bienvenidas.mention} para tarjetas de bienvenida")
        else:
            report_lines.append(f"  • Canal existente {ch_bienvenidas.mention} vinculado para bienvenidas dev")
        await update_guild_setting(guild.id, "welcome_channel_id", ch_bienvenidas.id)

        # Canal #presentaciones (Se coloca dentro de 📌 INICIO)
        ch_presentaciones = find_channel_smart(guild, ["presentaci", "presentat"], preferred_category=cat_inicio)
        if not ch_presentaciones:
            # Si se creó antes en una categoría duplicada, moverlo a 📌 INICIO
            ch_pres_outside = find_channel_smart(guild, ["presentaci", "presentat"])
            if ch_pres_outside and ch_pres_outside.category_id != cat_inicio.id:
                try:
                    await ch_pres_outside.edit(category=cat_inicio, name="💬・presentaciones", reason="MiniJefe: Mover a 📌 INICIO")
                    ch_presentaciones = ch_pres_outside
                    report_lines.append(f"  • Canal {ch_presentaciones.mention} reubicado dentro de **{cat_inicio.name}**")
                except Exception:
                    pass

            if not ch_presentaciones:
                ch_presentaciones = await guild.create_text_channel(name="💬・presentaciones", category=cat_inicio, reason="MiniJefe Setup")
                pres_msg = await ch_presentaciones.send(embed=create_presentation_template_embed())
                try:
                    await pres_msg.pin()
                except Exception:
                    pass
                report_lines.append(f"  • Creado canal {ch_presentaciones.mention} dentro de **{cat_inicio.name}** con plantilla fijada")
        else:
            report_lines.append(f"  • Canal de presentaciones {ch_presentaciones.mention} asegurado en **{cat_inicio.name}**")

        # Canal #reportes (Auditoría oficial)
        ch_reportes = find_channel_smart(guild, ["reporte", "auditoria"], preferred_category=cat_inicio)
        if not ch_reportes:
            ch_reportes = await get_or_create_reports_channel(guild)
            if ch_reportes and ch_reportes.category_id != cat_inicio.id:
                try:
                    await ch_reportes.edit(category=cat_inicio)
                except Exception:
                    pass
        if ch_reportes:
            report_lines.append(f"  • Canal {ch_reportes.mention} configurado para auditoría en **{cat_inicio.name}**")

        # -------------------------------------------------------------
        # LIMPIEZA DE CATEGORÍA Y CANALES DUPLICADOS
        # -------------------------------------------------------------
        for cat in list(guild.categories):
            if cat.id != cat_inicio.id and normalize_text(cat.name) == "inicio":
                for ch in list(cat.channels):
                    c_clean = normalize_text(ch.name)
                    if c_clean in ["reglas", "roles", "bienvenidas", "bienvenida"]:
                        try:
                            await ch.delete(reason="MiniJefe: Limpieza de canal duplicado")
                            report_lines.append(f"  🗑️ Eliminado canal redundante #{ch.name}")
                        except Exception:
                            pass
                if len(cat.channels) == 0:
                    try:
                        await cat.delete(reason="MiniJefe: Limpieza de categoría duplicada")
                        report_lines.append(f"🗑️ Eliminada categoría redundante **{cat.name}**")
                    except Exception:
                        pass

        # -------------------------------------------------------------
        # 2. CATEGORÍA "ESTUDIO"
        # -------------------------------------------------------------
        cat_estudio = find_category_smart(guild, ["estudio", "aprendizaje", "study"])
        if not cat_estudio:
            cat_estudio = await guild.create_category(name="📚 ESTUDIO", reason="MiniJefe: Setup de comunidad")
            report_lines.append(f"📁 Creada categoría **{cat_estudio.name}**")
        else:
            report_lines.append(f"📁 Categoría detectada: **{cat_estudio.name}**")

        ch_roadmaps = find_channel_smart(guild, ["roadmap", "ruta"], preferred_category=cat_estudio)
        if not ch_roadmaps:
            ch_roadmaps = await guild.create_text_channel(name="roadmaps-personales", category=cat_estudio, reason="MiniJefe Setup")
            road_msg = await ch_roadmaps.send(embed=create_roadmap_template_embed())
            try:
                await road_msg.pin()
            except Exception:
                pass
            report_lines.append(f"  • Creado canal {ch_roadmaps.mention} con plantilla de roadmap fijada")
        else:
            report_lines.append(f"  • Canal {ch_roadmaps.mention} detectado en **{cat_estudio.name}**")

        # -------------------------------------------------------------
        # 3. FORO DE PROYECTOS (#proyectos-colaboracion)
        # -------------------------------------------------------------
        ch_proyectos = find_channel_smart(guild, ["proyecto", "colaboracion", "colab"])
        if not ch_proyectos:
            tags = [
                discord.ForumTag(name="🚀 Startup"),
                discord.ForumTag(name="💼 Freelance"),
                discord.ForumTag(name="📚 Aprendizaje"),
                discord.ForumTag(name="💻 Frontend"),
                discord.ForumTag(name="⚙️ Backend"),
                discord.ForumTag(name="📱 Mobile"),
                discord.ForumTag(name="🎨 UI/UX"),
                discord.ForumTag(name="🟢 Reclutando")
            ]
            try:
                forum_ch = await guild.create_channel(
                    name="proyectos-colaboracion",
                    type=discord.ChannelType.forum,
                    available_tags=tags,
                    topic="Espacio para publicar y colaborar en proyectos de la comunidad",
                    reason="MiniJefe: Setup de comunidad"
                )
                await forum_ch.create_thread(
                    name="📌 Plantilla Oficial para Publicar Proyectos",
                    embed=create_project_template_embed()
                )
                report_lines.append(f"🚀 Creado **Foro** {forum_ch.mention} con etiquetas y plantilla fijada")
            except Exception as e:
                # Si el servidor no tiene Community habilitado, crear canal de texto estándar
                text_proj = await guild.create_text_channel(name="proyectos-colaboracion", reason="MiniJefe Setup")
                msg_proj = await text_proj.send(embed=create_project_template_embed())
                try:
                    await msg_proj.pin()
                except Exception:
                    pass
                report_lines.append(f"🚀 Creado canal de texto {text_proj.mention} con plantilla de proyectos fijada")
        else:
            report_lines.append(f"🚀 Canal {ch_proyectos.mention} ya existente")

        # -------------------------------------------------------------
        # 4. CREACIÓN Y VERIFICACIÓN DE ROLES DEV
        # -------------------------------------------------------------
        existing_role_names = {r.name.lower() for r in guild.roles}
        roles_to_create = [
            (SPECIALTY_NAMES, discord.Color(0x3498DB)),
            (LANGUAGE_NAMES, discord.Color(0xE67E22)),
            (NOTIFICATION_NAMES, discord.Color(0x9B59B6))
        ]
        created_count = 0
        for names, col in roles_to_create:
            for name in names:
                if name.lower() not in existing_role_names:
                    try:
                        await guild.create_role(name=name, color=col, mentionable=False, reason="MiniJefe Auto Setup")
                        created_count += 1
                    except Exception:
                        pass
        report_lines.append(f"🎭 Verificados y creados **{created_count}** roles de especialidad y lenguajes")

        # -------------------------------------------------------------
        # RESPUESTA FINAL Y REGISTRO EN #REPORTES
        # -------------------------------------------------------------
        embed_final = discord.Embed(
            title="🎉 ¡Setup Comunitario Completado con Éxito!",
            description=(
                f"MiniJefe ha estructurado la arquitectura completa del servidor **{guild.name}**:\n\n" +
                "\n".join(report_lines) +
                "\n\n💡 *Recuerda verificar en los Ajustes del Servidor que el rol de MiniJefe esté por encima de los roles dev.*"
            ),
            color=COLOR_SUCCESS
        )
        embed_final.set_footer(text=f"Servidor: {guild.name} • MiniJefe Automatización")
        await interaction.followup.send(embed=embed_final, ephemeral=True)

        # Dejar constancia formal en #reportes
        try:
            await log_to_reports(
                guild=guild,
                title="Setup Comunitario Completo Ejecutado",
                description=(
                    f"Se ha completado la inicialización y estructuración de la comunidad dev en **{guild.name}**:\n\n" +
                    "\n".join(report_lines)
                ),
                action_type="setup",
                user=interaction.user
            )
        except Exception as e:
            logger.warning(f"Error al registrar setup en #reportes: {e}")

    @app_commands.command(name="publicar-reglas", description="Publica el reglamento oficial completo de la comunidad dev")
    @app_commands.describe(canal="Canal donde se publicarán las reglas (por defecto #reglas o el actual)")
    @app_commands.default_permissions(administrator=True)
    async def publish_rules(self, interaction: discord.Interaction, canal: Optional[discord.TextChannel] = None):
        target = canal or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("❌ Debes indicar un canal de texto válido.", ephemeral=True)
            return

        embeds = create_server_rules_embeds()
        try:
            for emb in embeds:
                await target.send(embed=emb)
            await interaction.response.send_message(f"✅ ¡Reglas oficiales publicadas exitosamente en {target.mention}!", ephemeral=True)
            await log_to_reports(
                guild=interaction.guild,
                title="Reglamento Oficial Publicado",
                description=f"Se ha publicado el reglamento oficial completo en {target.mention}.",
                action_type="setup",
                user=interaction.user
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error al publicar reglas: {e}", ephemeral=True)

    @app_commands.command(name="plantilla-proyecto", description="Publica o consulta la plantilla oficial para el foro de proyectos")
    @app_commands.describe(enviar_al_canal="Si es True, publica la plantilla en el canal actual para fijarla")
    async def publish_project_template(self, interaction: discord.Interaction, enviar_al_canal: bool = False):
        embed = create_project_template_embed()
        if enviar_al_canal:
            if not interaction.user.guild_permissions.manage_messages:
                await interaction.response.send_message("❌ Necesitas permisos de gestión para publicar plantillas fijadas en el canal.", ephemeral=True)
                return
            await interaction.channel.send(embed=embed)
            await interaction.response.send_message("✅ Plantilla de proyectos enviada al canal.", ephemeral=True)
            await log_to_reports(
                guild=interaction.guild,
                title="Plantilla de Proyectos Desplegada",
                description=f"Se publicó la plantilla de proyectos en {interaction.channel.mention}.",
                action_type="setup",
                user=interaction.user
            )
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="plantilla-roadmap", description="Publica o consulta la plantilla oficial de roadmap para la categoría Estudio")
    @app_commands.describe(enviar_al_canal="Si es True, publica la plantilla en el canal actual para fijarla")
    async def publish_roadmap_template(self, interaction: discord.Interaction, enviar_al_canal: bool = False):
        embed = create_roadmap_template_embed()
        if enviar_al_canal:
            if not interaction.user.guild_permissions.manage_messages:
                await interaction.response.send_message("❌ Necesitas permisos de gestión para publicar plantillas fijadas en el canal.", ephemeral=True)
                return
            await interaction.channel.send(embed=embed)
            await interaction.response.send_message("✅ Plantilla de roadmap enviada al canal.", ephemeral=True)
            await log_to_reports(
                guild=interaction.guild,
                title="Plantilla de Roadmaps Desplegada",
                description=f"Se publicó la plantilla de roadmaps de estudio en {interaction.channel.mention}.",
                action_type="setup",
                user=interaction.user
            )
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="plantilla-presentacion", description="Publica o consulta el formato de presentación para nuevos miembros")
    @app_commands.describe(enviar_al_canal="Si es True, publica el formato en el canal actual para fijarlo")
    async def publish_presentation_template(self, interaction: discord.Interaction, enviar_al_canal: bool = False):
        embed = create_presentation_template_embed()
        if enviar_al_canal:
            if not interaction.user.guild_permissions.manage_messages:
                await interaction.response.send_message("❌ Necesitas permisos de gestión para publicar formatos fijados en el canal.", ephemeral=True)
                return
            await interaction.channel.send(embed=embed)
            await interaction.response.send_message("✅ Formato de presentación enviado al canal.", ephemeral=True)
            await log_to_reports(
                guild=interaction.guild,
                title="Plantilla de Presentaciones Desplegada",
                description=f"Se publicó la plantilla de presentación comunitaria en {interaction.channel.mention}.",
                action_type="setup",
                user=interaction.user
            )
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="limpiar-duplicados",
        description="Elimina las categorías y canales duplicados ('Inicio' y 'Estudio') creados por error abajo"
    )
    @app_commands.default_permissions(administrator=True)
    async def clean_duplicates(self, interaction: discord.Interaction):
        """Elimina exclusivamente las categorías sin emojis que se crearon por duplicidad."""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("❌ Servidor no encontrado.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        deleted_channels = []
        deleted_cats = []

        # Buscar categorías sin emojis 'Inicio' y 'Estudio' que se hayan creado abajo
        for cat in list(guild.categories):
            # Si el nombre es exactamente 'Inicio' o 'Estudio' (sin el emoji 📌 ni 📚)
            if cat.name.strip() in ["Inicio", "Estudio"]:
                for ch in list(cat.channels):
                    try:
                        await ch.delete(reason="MiniJefe: Limpieza de canales duplicados")
                        deleted_channels.append(ch.name)
                    except Exception as e:
                        logger.warning(f"No se pudo borrar canal duplicado {ch.name}: {e}")
                try:
                    await cat.delete(reason="MiniJefe: Limpieza de categoría duplicada")
                    deleted_cats.append(cat.name)
                except Exception as e:
                    logger.warning(f"No se pudo borrar categoría duplicada {cat.name}: {e}")

        # También buscar canales sueltos duplicados por si acaso
        for ch in list(guild.text_channels):
            if ch.category is None and ch.name in ["reglas", "roles", "bienvenidas", "presentaciones", "roadmaps-personales"]:
                try:
                    await ch.delete(reason="MiniJefe: Limpieza de canal huérfano duplicado")
                    deleted_channels.append(ch.name)
                except Exception:
                    pass

        embed = discord.Embed(
            title="🧹 Limpieza de Canales Duplicados Completada",
            description=(
                f"Se han eliminado con éxito los canales redundantes:\n\n"
                f"📁 **Categorías eliminadas:** {', '.join(deleted_cats) if deleted_cats else 'Ninguna encontrada'}\n"
                f"🗑️ **Canales eliminados:** {', '.join(deleted_channels) if deleted_channels else 'Ninguno encontrado'}\n\n"
                f"✨ Tu servidor ahora conserva únicamente sus categorías originales con emojis."
            ),
            color=COLOR_SUCCESS
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="aplicar-en-canales-reales",
        description="Aplica las reglas, roles, bienvenida y plantillas en tus canales reales con emojis"
    )
    @app_commands.default_permissions(administrator=True)
    async def apply_to_real_channels(self, interaction: discord.Interaction):
        """Configura todo en los canales ya existentes con emojis y crea sólo lo estrictamente necesario."""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("❌ Servidor no encontrado.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        report_lines = []

        # 1. Localizar categoría 📌 INICIO
        cat_inicio = find_category_smart(guild, ["inicio"])
        if cat_inicio:
            report_lines.append(f"📁 Categoría principal: **{cat_inicio.name}**")

            # 📜 · reglas
            ch_reglas = find_channel_smart(guild, ["regla", "rules"], preferred_category=cat_inicio)
            if ch_reglas:
                for emb in create_server_rules_embeds():
                    await ch_reglas.send(embed=emb)
                report_lines.append(f"  • 📜 Reglamento de programación publicado en {ch_reglas.mention}")

            # 🎭 · roles
            ch_roles = find_channel_smart(guild, ["role", "rol"], preferred_category=cat_inicio)
            if ch_roles:
                panel_embed = create_roles_panel_embed()
                await ch_roles.send(embed=panel_embed, view=RolesPanelView())
                report_lines.append(f"  • 🎭 Selector de roles instantáneo desplegado en {ch_roles.mention}")

            # 👋 · bienvenida
            ch_bienvenida = find_channel_smart(guild, ["bienvenid", "welcome"], preferred_category=cat_inicio)
            if ch_bienvenida:
                await update_guild_setting(guild.id, "welcome_channel_id", ch_bienvenida.id)
                report_lines.append(f"  • 👋 Tarjetas gráficas de bienvenida vinculadas a {ch_bienvenida.mention}")

            # ✨ · presentaciones (Crear dentro de 📌 INICIO si no existe)
            ch_pres = find_channel_smart(guild, ["presentaci", "presentat"], preferred_category=cat_inicio)
            if not ch_pres:
                ch_pres = await guild.create_text_channel(
                    name="✨・presentaciones",
                    category=cat_inicio,
                    topic="Canal para presentarte ante la comunidad siguiendo el formato de referencia.",
                    reason="MiniJefe: Agregar canal de presentaciones a 📌 INICIO"
                )
                msg_p = await ch_pres.send(embed=create_presentation_template_embed())
                try:
                    await msg_p.pin()
                except Exception:
                    pass
                report_lines.append(f"  • ✨ Canal de presentaciones creado en {cat_inicio.name}: {ch_pres.mention} (con formato fijado)")
            else:
                report_lines.append(f"  • ✨ Canal de presentaciones existente en {cat_inicio.name}: {ch_pres.mention}")

        # 2. Localizar canal 🔗 · proyectos en 💻 DESARROLLO
        ch_proyectos = find_channel_smart(guild, ["proyecto", "colaboracion", "colab"])
        if ch_proyectos:
            msg_proj = await ch_proyectos.send(embed=create_project_template_embed())
            try:
                await msg_proj.pin()
            except Exception:
                pass
            report_lines.append(f"🚀 Plantilla oficial para buscar y publicar proyectos fijada en {ch_proyectos.mention}")

        # 3. Localizar categoría 📚 ESTUDIO y añadir canal de roadmaps
        cat_estudio = find_category_smart(guild, ["estudio", "aprendizaje", "study"])
        if cat_estudio:
            ch_roadmaps = find_channel_smart(guild, ["roadmap", "ruta"], preferred_category=cat_estudio)
            if not ch_roadmaps:
                ch_roadmaps = await guild.create_text_channel(
                    name="🗺️・roadmaps",
                    category=cat_estudio,
                    topic="Comparte tu ruta de aprendizaje personal con la comunidad.",
                    reason="MiniJefe: Agregar canal de roadmaps a 📚 ESTUDIO"
                )
                msg_r = await ch_roadmaps.send(embed=create_roadmap_template_embed())
                try:
                    await msg_r.pin()
                except Exception:
                    pass
                report_lines.append(f"📚 Canal de roadmaps personales creado en {cat_estudio.name}: {ch_roadmaps.mention} (con plantilla fijada)")
            else:
                report_lines.append(f"📚 Canal de roadmaps existente en {cat_estudio.name}: {ch_roadmaps.mention}")

        # 4. Asegurar canal #reportes para auditoría
        ch_reportes = await get_or_create_reports_channel(guild)
        if ch_reportes:
            report_lines.append(f"📋 Canal de auditoría {ch_reportes.mention} verificado")

        # 5. Limpiar categorías duplicadas si siguen abajo
        deleted_count = 0
        for cat in list(guild.categories):
            if cat.name.strip() in ["Inicio", "Estudio"]:
                for ch in list(cat.channels):
                    try:
                        await ch.delete(reason="MiniJefe Auto Clean")
                        deleted_count += 1
                    except Exception:
                        pass
                try:
                    await cat.delete(reason="MiniJefe Auto Clean")
                except Exception:
                    pass
        if deleted_count > 0:
            report_lines.append(f"🗑️ Eliminados **{deleted_count}** canales duplicados que estaban abajo de más")

        embed_final = discord.Embed(
            title="🎉 ¡Integración en Canales Reales Completada!",
            description=(
                f"MiniJefe ha vinculado y configurado la comunidad en los canales oficiales de **{guild.name}**:\n\n" +
                "\n".join(report_lines)
            ),
            color=COLOR_SUCCESS
        )
        embed_final.set_footer(text=f"Servidor: {guild.name} • MiniJefe Integración Perfecta")
        await interaction.followup.send(embed=embed_final, ephemeral=True)

        try:
            await log_to_reports(
                guild=guild,
                title="Integración en Canales Existentes Completada",
                description="Se configuraron las reglas, roles, bienvenida y plantillas en los canales originales con emojis.",
                action_type="setup",
                user=interaction.user
            )
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(CommunityCog(bot))
