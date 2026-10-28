import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from utils.embeds import (
    create_server_rules_embeds,
    create_project_template_embed,
    create_roadmap_template_embed,
    create_presentation_template_embed
)

class CommunityCog(commands.Cog, name="Comunidad y Recursos"):
    """Comandos para desplegar reglas, plantillas de proyectos, roadmaps y presentaciones."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

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
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(CommunityCog(bot))
