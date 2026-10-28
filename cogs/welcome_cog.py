import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional

from database import get_guild_settings, update_guild_setting
from utils.ai_service import generate_welcome_quote
from utils.image_generator import generate_welcome_card
from utils.embeds import COLOR_SUCCESS, COLOR_PRIMARY

logger = logging.getLogger("MiniJefe.Welcome")

class WelcomeCog(commands.Cog, name="Bienvenidas"):
    """Gestión de bienvenida para nuevos miembros con tarjetas gráficas de programación e IA."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_welcome_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Encuentra el canal adecuado para enviar la bienvenida."""
        settings = await get_guild_settings(guild.id)
        channel_id = settings.get("welcome_channel_id")
        if channel_id:
            ch = guild.get_channel(channel_id)
            if ch and isinstance(ch, discord.TextChannel):
                return ch

        # Buscar por nombres comunes
        for name in ["bienvenida", "bienvenidas", "welcome", "llegadas", "general", "chat-general"]:
            ch = discord.utils.get(guild.text_channels, name=name)
            if ch:
                return ch

        # Usar el canal del sistema si existe
        if guild.system_channel:
            return guild.system_channel

        # Si no, el primer canal donde el bot pueda escribir
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                return ch

        return None

    def create_welcome_embed(self, member: discord.Member, quote: str) -> discord.Embed:
        """Crea el embed estético para la bienvenida."""
        embed = discord.Embed(
            title="👋 ¡Pónganse de pie! Ha llegado un nuevo desarrollador",
            description=(
                f"Le damos una cálida bienvenida a {member.mention} a **{member.guild.name}**.\n\n"
                f"💬 **Mensaje de MiniJefe:**\n> *\"{quote}\"*\n\n"
                f"✨ **Primeros pasos sugeridos:**\n"
                f"• Pasa por **#roles** para seleccionar tus tecnologías y especialidad.\n"
                f"• Preséntate en **#presentaciones** para que la comunidad te conozca.\n"
                f"• Revisa las **#reglas** y comparte tus proyectos en **#proyectos-colaboracion**.\n"
                f"• Si quieres charlar o necesitas ayuda con código, ¡mencióname con `@{self.bot.user.name}` o usa `/hablar`!"
            ),
            color=COLOR_PRIMARY
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url="attachment://welcome_card.png")
        embed.set_footer(
            text=f"Miembro #{member.guild.member_count} • Servidor de Jordy • ¡Ponte cómodo y a codear!",
            icon_url=member.guild.icon.url if member.guild.icon else None
        )
        return embed

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Dispara el saludo automático con tarjeta gráfica cuando alguien entra al servidor."""
        if member.bot:
            return

        channel = await self.get_welcome_channel(member.guild)
        if not channel:
            logger.warning(f"No se encontró un canal adecuado de bienvenida en {member.guild.name}")
            return

        # 1. Frase de bienvenida con IA
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
                content=f"🎉 ¡Hey {member.mention}, bienvenido/a a la comunidad dev!",
                embed=embed,
                file=file
            )
            logger.info(f"Bienvenida con tarjeta gráfica enviada a {member.display_name} en #{channel.name}")
        except Exception as e:
            logger.error(f"Error al enviar tarjeta gráfica de bienvenida a {member.display_name}: {e}", exc_info=True)
            # Fallback a enviar solo el embed si la imagen falla
            try:
                await channel.send(content=f"🎉 ¡Hey {member.mention}, bienvenido/a!", embed=embed)
            except Exception:
                pass

    @app_commands.command(name="config-bienvenida", description="Configura el canal oficial de bienvenidas")
    @app_commands.describe(canal="Canal donde MiniJefe saludará a los nuevos miembros")
    @app_commands.default_permissions(administrator=True)
    async def config_welcome_channel(self, interaction: discord.Interaction, canal: discord.TextChannel):
        """Comando para que administradores definan el canal de bienvenida."""
        await update_guild_setting(interaction.guild_id, "welcome_channel_id", canal.id)
        embed = discord.Embed(
            title="✅ Canal de Bienvenida Configurado",
            description=f"A partir de ahora, recibiré a cada nuevo integrante en {canal.mention} con su tarjeta gráfica y saludo con IA.",
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
            await interaction.followup.send(
                content=f"🧪 *(Prueba de Bienvenida)* 🎉 ¡Bienvenido/a {interaction.user.mention}!",
                embed=embed
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
