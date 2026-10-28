import discord
from discord.ext import commands
from discord import app_commands
import logging
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
        # 1. CATEGORÍA "INICIO"
        # -------------------------------------------------------------
        cat_inicio = discord.utils.get(guild.categories, name="Inicio")
        if not cat_inicio:
            cat_inicio = await guild.create_category(name="Inicio", reason="MiniJefe: Setup de comunidad")
            report_lines.append("📁 Creada categoría **Inicio**")
        else:
            report_lines.append("📁 Categoría **Inicio** ya existente")

        # Canal #reglas
        ch_reglas = discord.utils.get(guild.text_channels, name="reglas")
        if not ch_reglas:
            ch_reglas = await guild.create_text_channel(name="reglas", category=cat_inicio, reason="MiniJefe Setup")
            for emb in create_server_rules_embeds():
                await ch_reglas.send(embed=emb)
            report_lines.append(f"  • Creado canal {ch_reglas.mention} con reglamento oficial publicado")
        else:
            report_lines.append(f"  • Canal {ch_reglas.mention} detectado")

        # Canal #roles
        ch_roles = discord.utils.get(guild.text_channels, name="roles")
        if not ch_roles:
            ch_roles = await guild.create_text_channel(name="roles", category=cat_inicio, reason="MiniJefe Setup")
            panel_embed = create_roles_panel_embed()
            await ch_roles.send(embed=panel_embed, view=RolesPanelView())
            report_lines.append(f"  • Creado canal {ch_roles.mention} con selector interactivo de roles")
        else:
            report_lines.append(f"  • Canal {ch_roles.mention} detectado")

        # Canal #presentaciones
        ch_presentaciones = discord.utils.get(guild.text_channels, name="presentaciones")
        if not ch_presentaciones:
            ch_presentaciones = await guild.create_text_channel(name="presentaciones", category=cat_inicio, reason="MiniJefe Setup")
            pres_msg = await ch_presentaciones.send(embed=create_presentation_template_embed())
            try:
                await pres_msg.pin()
            except Exception:
                pass
            report_lines.append(f"  • Creado canal {ch_presentaciones.mention} con formato de presentación fijado")
        else:
            report_lines.append(f"  • Canal {ch_presentaciones.mention} detectado")

        # Canal #bienvenidas
        ch_bienvenidas = discord.utils.get(guild.text_channels, name="bienvenidas") or \
                         discord.utils.get(guild.text_channels, name="bienvenida")
        if not ch_bienvenidas:
            ch_bienvenidas = await guild.create_text_channel(name="bienvenidas", category=cat_inicio, reason="MiniJefe Setup")
            report_lines.append(f"  • Creado canal {ch_bienvenidas.mention} y configurado para tarjetas de bienvenida")
        else:
            report_lines.append(f"  • Canal {ch_bienvenidas.mention} enlazado para bienvenidas")
        await update_guild_setting(guild.id, "welcome_channel_id", ch_bienvenidas.id)

        # Canal #reportes (Auditoría oficial)
        ch_reportes = await get_or_create_reports_channel(guild)
        if ch_reportes:
            report_lines.append(f"  • Canal {ch_reportes.mention} configurado para auditoría y reportes continuos")

        # -------------------------------------------------------------
        # 2. CATEGORÍA "ESTUDIO"
        # -------------------------------------------------------------
        cat_estudio = discord.utils.get(guild.categories, name="Estudio")
        if not cat_estudio:
            cat_estudio = await guild.create_category(name="Estudio", reason="MiniJefe: Setup de comunidad")
            report_lines.append("📁 Creada categoría **Estudio**")
        else:
            report_lines.append("📁 Categoría **Estudio** ya existente")

        ch_roadmaps = discord.utils.get(guild.text_channels, name="roadmaps-personales") or \
                      discord.utils.get(guild.text_channels, name="rutas-de-estudio")
        if not ch_roadmaps:
            ch_roadmaps = await guild.create_text_channel(name="roadmaps-personales", category=cat_estudio, reason="MiniJefe Setup")
            road_msg = await ch_roadmaps.send(embed=create_roadmap_template_embed())
            try:
                await road_msg.pin()
            except Exception:
                pass
            report_lines.append(f"  • Creado canal {ch_roadmaps.mention} con plantilla de roadmap fijada")
        else:
            report_lines.append(f"  • Canal {ch_roadmaps.mention} detectado")

        # -------------------------------------------------------------
        # 3. FORO DE PROYECTOS (#proyectos-colaboracion)
        # -------------------------------------------------------------
        ch_proyectos = discord.utils.get(guild.channels, name="proyectos-colaboracion")
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
                report_lines.append(f"🚀 Creado canal de texto {text_proj.mention} con plantilla de proyectos fijada *(Habilita 'Comunidad' en Discord si deseas convertirlo en Foro nativo)*")
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

async def setup(bot: commands.Bot):
    await bot.add_cog(CommunityCog(bot))
