import discord
from discord.ext import commands
from discord import app_commands
import logging
import unicodedata
import re
from typing import Optional

from database import get_guild_settings, update_guild_setting
from utils.ai_service import generate_welcome_quote
from utils.image_generator import generate_welcome_card
from utils.embeds import COLOR_SUCCESS, COLOR_PRIMARY

logger = logging.getLogger("MiniJefe.Welcome")

def normalize_channel_name(name: str) -> str:
    """Normaliza el nombre de un canal removiendo emojis, tildes y caracteres especiales."""
    n = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8').lower()
    return re.sub(r'[^a-z0-9]', '', n)

class WelcomeCog(commands.Cog, name="Bienvenidas"):
    """Gestión de bienvenida para nuevos miembros con tarjetas gráficas de programación e IA."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_welcome_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """
        Encuentra inteligentemente el mejor canal para enviar la bienvenida:
        1. Canal configurado manualmente vía /config-bienvenida.
        2. Canal del sistema si el bot tiene permisos de escritura.
        3. Canales cuyo nombre contenga 'bienvenida', 'welcome', 'llegada', 'inicio', 'general', 'chat', 'comunidad'.
        4. Cualquier canal de texto accesible por los miembros donde el bot pueda escribir.
        """
        # 1. Canal configurado explícitamente en base de datos
        try:
            settings = await get_guild_settings(guild.id)
            channel_id = settings.get("welcome_channel_id")
            if channel_id:
                ch = guild.get_channel(channel_id)
                if ch and isinstance(ch, discord.TextChannel) and ch.permissions_for(guild.me).send_messages:
                    return ch
        except Exception as e:
            logger.warning(f"Error al consultar configuración de bienvenida: {e}")

        # 2. Canal del sistema de Discord
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            return guild.system_channel

        # Canales donde el bot tiene permiso de enviar mensajes y embeber enlaces
        writable_channels = [
            ch for ch in guild.text_channels
            if ch.permissions_for(guild.me).send_messages
        ]

        if not writable_channels:
            return None

        # 3. Búsqueda por palabras clave con prioridad
        priority_groups = [
            ["bienvenid", "welcome", "llegad", "hola"],
            ["general", "chat", "principal", "comunidad", "charla", "conversacion"],
            ["inicio", "presentacion", "presentate", "lobby", "start"]
        ]

        for keywords in priority_groups:
            for ch in writable_channels:
                clean = normalize_channel_name(ch.name)
                if any(kw in clean for kw in keywords):
                    return ch

        # 4. Fallback al primer canal donde el bot pueda escribir
        return writable_channels[0]

    def create_welcome_embed(self, member: discord.Member, quote: str) -> discord.Embed:
        """Crea el embed estético y profesional para la bienvenida."""
        embed = discord.Embed(
            title="👋 ¡Bienvenido/a a la comunidad!",
            description=(
                f"Le damos una cordial bienvenida a {member.mention} a **{member.guild.name}**.\n\n"
                f"💬 **Mensaje de Bienvenida:**\n> *\"{quote}\"*\n\n"
                f"✨ **Ruta inicial recomendada:**\n"
                f"• Selecciona tus tecnologías en **#roles**.\n"
                f"• Preséntate ante el equipo en **#presentaciones**.\n"
                f"• Revisa las directrices en **#reglas** y comparte tus ideas en **#proyectos-colaboracion**.\n"
                f"• Si requieres asistencia técnica o deseas registrar tareas, mencióname con `@{self.bot.user.name}` o usa `/hablar`."
            ),
            color=COLOR_PRIMARY
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url="attachment://welcome_card.png")
        embed.set_footer(
            text=f"Miembro #{member.guild.member_count} • Comunidad de {member.guild.name} • ¡Mucho éxito en tus proyectos!",
            icon_url=member.guild.icon.url if member.guild.icon else None
        )
        return embed

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Dispara el saludo automático con tarjeta gráfica cuando alguien entra al servidor."""
        if member.bot:
            return

        logger.info(f"Nuevo integrante detectado: {member.display_name} ({member.id}) en '{member.guild.name}'")

        channel = await self.get_welcome_channel(member.guild)
        if not channel:
            logger.warning(f"No se encontró ningún canal con permisos de escritura en {member.guild.name}")
            return

        # 1. Generar cita de bienvenida con IA en tono profesional
        quote = await generate_welcome_quote(member.display_name, member.guild.name)
        embed = self.create_welcome_embed(member, quote)

        # 2. Generar tarjeta gráfica estética con fondo de código y avatar
        try:
            avatar_url = member.display_avatar.url if member.display_avatar else None
            card_buf = await generate_welcome_card(
                username=member.display_name,
                member_count=member.guild.member_count or 1,
                avatar_url=avatar_url
            )
            file = discord.File(card_buf, filename="welcome_card.png")
            await channel.send(
                content=f"🎉 ¡Bienvenido/a {member.mention} a la comunidad de **{member.guild.name}**!",
                embed=embed,
                file=file
            )
            logger.info(f"Bienvenida con tarjeta gráfica enviada exitosamente a {member.display_name} en #{channel.name}")
        except Exception as e:
            logger.error(f"Error generando tarjeta gráfica de bienvenida para {member.display_name}: {e}", exc_info=True)
            # Fallback seguro: enviar el embed sin archivo si Pillow o la red falla
            try:
                embed.set_image(url=None)
                await channel.send(
                    content=f"🎉 ¡Bienvenido/a {member.mention} a la comunidad de **{member.guild.name}**!",
                    embed=embed
                )
            except Exception as e2:
                logger.error(f"Error al enviar mensaje de bienvenida en fallback: {e2}")

    @app_commands.command(name="config-bienvenida", description="Configura el canal oficial de bienvenidas del servidor")
    @app_commands.describe(canal="Canal donde MiniJefe saludará a los nuevos miembros")
    @app_commands.default_permissions(administrator=True)
    async def config_welcome_channel(self, interaction: discord.Interaction, canal: discord.TextChannel):
        """Comando para que administradores definan el canal de bienvenida."""
        await update_guild_setting(interaction.guild_id, "welcome_channel_id", canal.id)
        embed = discord.Embed(
            title="✅ Canal de Bienvenida Configurado",
            description=f"A partir de ahora, recibiré a cada nuevo integrante en {canal.mention} con su tarjeta gráfica y bienvenida personalizada.",
            color=COLOR_SUCCESS
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="probar-bienvenida", description="Simula un mensaje de bienvenida con tarjeta gráfica para previsualizarlo")
    @app_commands.default_permissions(administrator=True)
    async def test_welcome(self, interaction: discord.Interaction):
        """Comando para previsualizar la tarjeta gráfica y el mensaje de bienvenida."""
        await interaction.response.defer(ephemeral=False)
        quote = await generate_welcome_quote(interaction.user.display_name, interaction.guild.name)
        embed = self.create_welcome_embed(interaction.user, quote)

        try:
            avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None
            card_buf = await generate_welcome_card(
                username=interaction.user.display_name,
                member_count=interaction.guild.member_count or 1,
                avatar_url=avatar_url
            )
            file = discord.File(card_buf, filename="welcome_card.png")
            await interaction.followup.send(
                content=f"🧪 *(Prueba de Bienvenida)* 🎉 ¡Bienvenido/a {interaction.user.mention}!",
                embed=embed,
                file=file
            )
        except Exception as e:
            logger.error(f"Error al generar previsualización de bienvenida: {e}", exc_info=True)
            embed.set_image(url=None)
            await interaction.followup.send(
                content=f"🧪 *(Prueba de Bienvenida)* 🎉 ¡Bienvenido/a {interaction.user.mention}!",
                embed=embed
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
