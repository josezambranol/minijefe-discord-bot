import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional

from database import get_guild_settings, update_guild_setting
from utils.ai_service import generate_welcome_quote
from utils.embeds import COLOR_SUCCESS, COLOR_INFO

logger = logging.getLogger("MiniJefe.Welcome")

class WelcomeCog(commands.Cog, name="Bienvenidas"):
    """Gestión de bienvenida para nuevos miembros con mensajes vivos y dinámicos."""

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

        # Si no, el primer canal de texto donde el bot pueda enviar mensajes
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                return ch

        return None

    def create_welcome_embed(self, member: discord.Member, quote: str) -> discord.Embed:
        """Crea el embed estético para la bienvenida."""
        embed = discord.Embed(
            title="👋 ¡Pónganse de pie! Ha llegado un nuevo recluta",
            description=f"Le damos una cálida bienvenida a {member.mention} a **{member.guild.name}**.\n\n"
                        f"💬 **Mensaje del Mini Jefe:**\n> *\"{quote}\"*\n\n"
                        f"✨ **¿Por dónde empezar?**\n"
                        f"• Pásate por los canales de chat a saludar a la banda.\n"
                        f"• Si necesitas ayuda o quieres charlar, ¡mencióname con `@{self.bot.user.name}` o usa `/hablar`!",
            color=0x5865F2
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(
            text=f"Miembro #{member.guild.member_count} • ¡Ponte cómodo y disfruta la estancia!",
            icon_url=member.guild.icon.url if member.guild.icon else None
        )
        return embed

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Dispara el saludo automático cuando alguien entra al servidor."""
        if member.bot:
            return

        channel = await self.get_welcome_channel(member.guild)
        if not channel:
            logger.warning(f"No se encontró un canal adecuado de bienvenida en {member.guild.name}")
            return

        quote = await generate_welcome_quote(member.display_name, member.guild.name)
        embed = self.create_welcome_embed(member, quote)

        try:
            await channel.send(content=f"🎉 ¡Hey {member.mention}, bienvenido/a!", embed=embed)
            logger.info(f"Bienvenida enviada a {member.display_name} en #{channel.name}")
        except Exception as e:
            logger.error(f"Error al enviar bienvenida a {member.display_name}: {e}")

    @app_commands.command(name="config-bienvenida", description="Configura el canal oficial de bienvenidas")
    @app_commands.describe(canal="Canal donde MiniJefe saludará a los nuevos miembros")
    @app_commands.default_permissions(administrator=True)
    async def config_welcome_channel(self, interaction: discord.Interaction, canal: discord.TextChannel):
        """Comando para que administradores definan el canal de bienvenida."""
        await update_guild_setting(interaction.guild_id, "welcome_channel_id", canal.id)
        embed = discord.Embed(
            title="✅ Canal de Bienvenida Configurado",
            description=f"A partir de ahora, recibiré a cada nuevo integrante en {canal.mention} con toda la vibra.",
            color=COLOR_SUCCESS
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="probar-bienvenida", description="Simula un mensaje de bienvenida para ver cómo queda")
    @app_commands.default_permissions(administrator=True)
    async def test_welcome(self, interaction: discord.Interaction):
        """Comando para previsualizar el mensaje de bienvenida."""
        await interaction.response.defer(ephemeral=False)
        quote = await generate_welcome_quote(interaction.user.display_name, interaction.guild.name)
        embed = self.create_welcome_embed(interaction.user, quote)
        await interaction.followup.send(content=f"🧪 *(Prueba de Bienvenida)* 🎉 ¡Bienvenido/a {interaction.user.mention}!", embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
