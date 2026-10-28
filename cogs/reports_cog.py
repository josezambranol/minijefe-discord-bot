import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
from datetime import datetime, timezone, timedelta
import pytz
from typing import Optional

from database import (
    get_guild_settings,
    update_guild_setting,
    has_notification_been_sent,
    record_notification_sent,
    get_activities_since
)
from utils.reporting import (
    get_or_create_reports_channel,
    log_to_reports,
    build_daily_autonomous_report_embed,
    ACTION_STYLES
)
from utils.embeds import COLOR_SUCCESS, COLOR_INFO, COLOR_WARNING

logger = logging.getLogger("MiniJefe.ReportsCog")

class ReportsCog(commands.Cog, name="Reportes y Auditoría"):
    """Gestor de auditoría para todos los cambios y reporte diario autónomo de MiniJefe."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.daily_report_loop.start()
        self.has_announced_boot = False

    def cog_unload(self):
        self.daily_report_loop.cancel()

    def get_guild_now(self, tz_name: str = "America/Bogota") -> datetime:
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.timezone("America/Bogota")
        return datetime.now(tz)

    @commands.Cog.listener()
    async def on_ready(self):
        """Notifica en #reportes cuando MiniJefe entra en línea tras una actualización o reinicio."""
        if self.has_announced_boot:
            return
        self.has_announced_boot = True

        for guild in self.bot.guilds:
            try:
                report_ch = await get_or_create_reports_channel(guild)
                if report_ch and report_ch.permissions_for(guild.me).send_messages:
                    embed = discord.Embed(
                        title="🟢 MiniJefe en Línea — Servicios Activos",
                        description=(
                            f"MiniJefe se ha conectado exitosamente al servidor **{guild.name}**.\n\n"
                            f"✨ **Módulos y automatizaciones operativas:**\n"
                            f"• 📋 **Auditoría continua**: Todo cambio o implementación se registrará en este canal.\n"
                            f"• 🤖 **Reporte Diario Autónomo**: Balance operacional publicado diariamente.\n"
                            f"• ⏰ **Recordatorios periódicos**: Tareas en bucle con persistencia en SQLite.\n"
                            f"• 👋 **Bienvenidas gráficas**: Tarjetas de programación generadas con Pillow.\n"
                            f"• 🧹 **Moderación & Anti-Spam**: Limpieza avanzada por canal, usuario y días.\n"
                            f"• 🧠 **Asistente Gemini IA**: Conexión con Function Calling para registrar tareas."
                        ),
                        color=COLOR_SUCCESS,
                        timestamp=datetime.now(timezone.utc)
                    )
                    embed.set_footer(text=f"MiniJefe Sistema • Latencia: {round(self.bot.latency * 1000)}ms")
                    await report_ch.send(embed=embed)
            except Exception as e:
                logger.warning(f"No se pudo enviar anuncio de arranque a {guild.name}: {e}")

    @tasks.loop(minutes=1.0)
    async def daily_report_loop(self):
        """Revisa cada minuto si es hora de publicar el balance diario autónomo en #reportes."""
        for guild in self.bot.guilds:
            try:
                settings = await get_guild_settings(guild.id)
                tz_name = settings.get("timezone", "America/Bogota")
                now = self.get_guild_now(tz_name)

                target_hour = settings.get("daily_report_hour", 9)
                if now.hour == target_hour and now.minute == 0:
                    today_str = now.strftime("%Y-%m-%d")
                    notif_key = f"daily_autonomous_report_{guild.id}_{today_str}"

                    if await has_notification_been_sent(notif_key):
                        continue

                    report_ch = await get_or_create_reports_channel(guild)
                    if report_ch and report_ch.permissions_for(guild.me).send_messages:
                        embed = await build_daily_autonomous_report_embed(guild, self.bot)
                        await report_ch.send(embed=embed)
                        await record_notification_sent(notif_key)
                        logger.info(f"Reporte diario autónomo publicado exitosamente en {guild.name} (#{report_ch.name})")
            except Exception as e:
                logger.error(f"Error en daily_report_loop para {guild.name}: {e}")

    @daily_report_loop.before_loop
    async def before_daily_report_loop(self):
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="reporte-diario",
        description="Genera y publica inmediatamente en #reportes el balance diario de operaciones autónomas"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def slash_daily_report(self, interaction: discord.Interaction):
        """Comando manual para generar el reporte diario sin esperar a la hora programada."""
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            await interaction.followup.send("❌ Servidor no encontrado.", ephemeral=True)
            return

        report_ch = await get_or_create_reports_channel(guild)
        if not report_ch or not report_ch.permissions_for(guild.me).send_messages:
            await interaction.followup.send("❌ No se encontró o no se pudo crear el canal de `#reportes`.", ephemeral=True)
            return

        embed = await build_daily_autonomous_report_embed(guild, self.bot)
        sent_msg = await report_ch.send(embed=embed)

        await interaction.followup.send(
            f"✅ **Reporte diario autónomo generado exitosamente.** Se ha publicado en {report_ch.mention}.\n🔗 [Ver Reporte]({sent_msg.jump_url})",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(ReportsCog(bot))
