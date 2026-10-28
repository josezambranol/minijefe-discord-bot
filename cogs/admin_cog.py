import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Literal
import pytz
from database import get_guild_settings, update_guild_setting
from utils.embeds import COLOR_INFO, COLOR_SUCCESS, COLOR_WARNING

class AdminCog(commands.Cog, name="Configuración del Servidor"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    config_group = app_commands.Group(
        name="config",
        description="Configuraciones generales del bot de tareas en este servidor",
        default_permissions=discord.Permissions(administrator=True)
    )

    @config_group.command(name="canal-recordatorios", description="Establecer el canal donde se enviarán los recordatorios automáticos")
    @app_commands.describe(canal="Canal de texto para los recordatorios diarios y avisos de vencimiento")
    async def set_channel(self, interaction: discord.Interaction, canal: discord.TextChannel):
        await update_guild_setting(interaction.guild_id, "reminder_channel_id", canal.id)
        embed = discord.Embed(
            title="✅ Canal de Recordatorios Configurado",
            description=f"A partir de ahora, los recordatorios diarios y alertas de vencimiento se publicarán en {canal.mention}.",
            color=COLOR_SUCCESS
        )
        await interaction.response.send_message(embed=embed)

    @config_group.command(name="zona-horaria", description="Configurar la zona horaria del servidor")
    @app_commands.describe(
        zona="Selecciona o escribe la zona horaria (ej: America/Bogota, America/Mexico_City, Europe/Madrid)"
    )
    async def set_timezone(
        self,
        interaction: discord.Interaction,
        zona: str
    ):
        clean_zone = zona.strip()
        if clean_zone not in pytz.all_timezones:
            # Sugerir opciones comunes
            common_tzs = "\n".join([
                "• `America/Bogota` (Colombia, Perú, Ecuador)",
                "• `America/Mexico_City` (México)",
                "• `America/Santiago` (Chile)",
                "• `America/Argentina/Buenos_Aires` (Argentina)",
                "• `America/Caracas` (Venezuela)",
                "• `America/Guatemala` (Centroamérica)",
                "• `Europe/Madrid` (España)"
            ])
            await interaction.response.send_message(
                f"❌ **Zona horaria inválida:** `{clean_zone}`\n\n**Opciones comunes recomendadas:**\n{common_tzs}",
                ephemeral=True
            )
            return

        await update_guild_setting(interaction.guild_id, "timezone", clean_zone)
        embed = discord.Embed(
            title="🌍 Zona Horaria Actualizada",
            description=f"La zona horaria del servidor ahora es **`{clean_zone}`**.",
            color=COLOR_SUCCESS
        )
        await interaction.response.send_message(embed=embed)

    @config_group.command(name="enviar-md", description="Activar o desactivar el envío de recordatorios por Mensaje Directo (DM)")
    @app_commands.describe(activar="Si está activo, el bot enviará un mensaje directo al usuario asignado además del canal")
    async def toggle_dm(self, interaction: discord.Interaction, activar: bool):
        val = 1 if activar else 0
        await update_guild_setting(interaction.guild_id, "send_dm", val)
        state_str = "ACTIVADO ✅" if activar else "DESACTIVADO ❌"
        embed = discord.Embed(
            title="📬 Recordatorios por Mensaje Directo",
            description=f"El envío de recordatorios por mensaje directo privado ha sido: **{state_str}**",
            color=COLOR_SUCCESS
        )
        await interaction.response.send_message(embed=embed)

    @config_group.command(name="ver", description="Ver la configuración actual del bot en este servidor")
    async def view_config(self, interaction: discord.Interaction):
        settings = await get_guild_settings(interaction.guild_id)
        
        channel_mention = f"<#{settings['reminder_channel_id']}>" if settings.get("reminder_channel_id") else "*No configurado (canal por defecto)*"
        welcome_mention = f"<#{settings['welcome_channel_id']}>" if settings.get("welcome_channel_id") else "*Detección automática de canal de bienvenida*"
        daily_mention = f"<#{settings['daily_plan_channel_id']}>" if settings.get("daily_plan_channel_id") else "*Canal general por defecto*"
        dm_status = "✅ Activado" if settings.get("send_dm", 1) else "❌ Desactivado"
        spam_status = "🛡️ Activado" if settings.get("spam_shield_enabled", 1) else "❌ Desactivado"
        ai_personality = settings.get("ai_personality", "amigable").capitalize()

        embed = discord.Embed(
            title=f"⚙️ Configuración de MiniJefe — {interaction.guild.name}",
            color=COLOR_INFO
        )
        embed.add_field(name="👋 Canal de Bienvenidas", value=welcome_mention, inline=True)
        embed.add_field(name="📅 Canal de Planes Diarios", value=daily_mention, inline=True)
        embed.add_field(name="📢 Canal de Recordatorios", value=channel_mention, inline=True)
        embed.add_field(name="🛡️ Escudo Anti-Spam", value=spam_status, inline=True)
        embed.add_field(name="🎭 Personalidad de IA", value=f"`{ai_personality}`", inline=True)
        embed.add_field(name="🌍 Zona Horaria", value=f"`{settings.get('timezone', 'America/Bogota')}`", inline=True)
        embed.add_field(name="📬 Recordatorios por DM", value=dm_status, inline=True)
        embed.set_footer(text="Comandos disponibles: /config-bienvenida, /config-antispam, /personalidad, /config-plan-diario")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="probar-recordatorios", description="Ejecuta de forma manual e inmediata el ciclo de comprobación de tareas periódicas")
    @app_commands.default_permissions(administrator=True)
    async def force_reminders(self, interaction: discord.Interaction):
        periodic_cog = self.bot.get_cog("Recordatorios Periódicos y Delegados")
        if not periodic_cog:
            await interaction.response.send_message("❌ El módulo de recordatorios periódicos no está cargado.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            # Ejecutar una ronda de comprobación inmediata
            from database import get_active_periodic_reminders
            active = await get_active_periodic_reminders(interaction.guild_id)
            await interaction.followup.send(
                f"✅ **Ciclo de recordatorios verificado:**\n• Recordatorios periódicos activos en este servidor: **{len(active)}**",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Error al comprobar recordatorios: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
