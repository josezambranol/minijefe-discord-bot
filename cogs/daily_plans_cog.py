import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
from datetime import datetime
import pytz
from typing import Optional, List

from database import (
    get_guild_settings,
    update_guild_setting,
    add_daily_plan,
    get_daily_plans_for_date,
    toggle_daily_plan,
    delete_daily_plan,
    has_notification_been_sent,
    record_notification_sent
)
from utils.ai_service import generate_daily_briefing
from utils.embeds import COLOR_INFO, COLOR_SUCCESS, COLOR_WARNING

logger = logging.getLogger("MiniJefe.DailyPlans")

class DailyPlanItemSelect(discord.ui.Select):
    """Menú desplegable para interactuar con los planes diarios (completar o eliminar)."""

    def __init__(self, plans: List[dict]):
        options = []
        for p in plans[:25]:
            status_emoji = "✅" if p["is_completed"] else "⏳"
            time_part = f"[{p['time_text']}] " if p.get("time_text") else ""
            label = f"{time_part}{p['title']}"[:100]
            options.append(
                discord.SelectOption(
                    label=label,
                    value=str(p["id"]),
                    description=f"Estado: {'Completada' if p['is_completed'] else 'Pendiente'}",
                    emoji=status_emoji
                )
            )
        super().__init__(placeholder="Selecciona una actividad para cambiar su estado...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        plan_id = int(self.values[0])
        await toggle_daily_plan(plan_id)
        await interaction.response.send_message(f"🔄 ¡Estado de la actividad #{plan_id} actualizado con éxito!", ephemeral=True)


class DailyPlanView(discord.ui.View):
    """Vista interactiva con el menú de planes diarios."""

    def __init__(self, plans: List[dict]):
        super().__init__(timeout=300)
        if plans:
            self.add_item(DailyPlanItemSelect(plans))


class DailyPlansCog(commands.Cog, name="Planes Diarios"):
    """Gestor de la agenda diaria del servidor y briefing matutino interactivo."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.briefing_loop.start()

    def cog_unload(self):
        self.briefing_loop.cancel()

    def get_guild_now(self, tz_name: str = "America/Bogota") -> datetime:
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.timezone("America/Bogota")
        return datetime.now(tz)

    async def build_daily_embed(self, guild: discord.Guild, date_dt: datetime) -> discord.Embed:
        """Construye el embed visual con el plan del día y actividades de la comunidad."""
        settings = await get_guild_settings(guild.id)
        tz_name = settings.get("timezone", "America/Bogota")
        today_str = date_dt.strftime("%Y-%m-%d")
        day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        day_name = day_names[date_dt.weekday()]
        readable_date = date_dt.strftime("%d/%m/%Y")

        # 1. Obtener planes comunitarios de la DB
        plans = await get_daily_plans_for_date(guild.id, today_str)

        # 2. Generar mensaje de la IA
        act_texts = [f"{p.get('time_text', '')} {p['title']}".strip() for p in plans]
        ai_greeting = await generate_daily_briefing(day_name, act_texts, [])

        embed = discord.Embed(
            title=f"📅 Plan y Resumen del Día — {day_name} {readable_date}",
            description=f"💬 **Mensaje de MiniJefe:**\n> {ai_greeting}\n",
            color=0x3498DB
        )

        # Campo de actividades de la comunidad
        if plans:
            lines = []
            for p in plans:
                check = "~~" if p["is_completed"] else ""
                emoji = "✅" if p["is_completed"] else "🔹"
                time_str = f"**[{p['time_text']}]** " if p.get("time_text") else ""
                lines.append(f"{emoji} {time_str}{check}{p['title']}{check}")
            embed.add_field(name="📌 Actividades & Planes de la Comunidad", value="\n".join(lines), inline=False)
        else:
            embed.add_field(
                name="📌 Actividades de la Comunidad",
                value="*No hay actividades registradas hoy. ¡Usa `/plan-agregar` para agendar algo con la banda!*",
                inline=False
            )

        embed.set_footer(text=f"Servidor: {guild.name} • ¡Que sea un día productivo!")
        return embed

    @app_commands.command(name="plan-agregar", description="Agrega una actividad o evento a la agenda de hoy")
    @app_commands.describe(
        actividad="Nombre o descripción del evento (ej: Torneo de Valorant, Repaso de examen)",
        hora="Hora opcional del evento (ej: 4:00 PM, 20:00, Tarde)"
    )
    async def add_plan(self, interaction: discord.Interaction, actividad: str, hora: Optional[str] = None):
        """Agrega un plan a la lista del día."""
        settings = await get_guild_settings(interaction.guild_id)
        now = self.get_guild_now(settings.get("timezone", "America/Bogota"))
        today_str = now.strftime("%Y-%m-%d")

        plan_id = await add_daily_plan(
            guild_id=interaction.guild_id,
            creator_id=interaction.user.id,
            title=actividad.strip(),
            time_text=hora.strip() if hora else None,
            plan_date=today_str
        )

        hora_display = f" a las **{hora.strip()}**" if hora else ""
        await interaction.response.send_message(
            f"✅ **¡Anotado en el plan de hoy!**\n📌 **{actividad.strip()}**{hora_display} agregado por {interaction.user.mention}."
        )

    @app_commands.command(name="plan-hoy", description="Muestra el plan y actividades del día con controles interactivos")
    async def view_today_plan(self, interaction: discord.Interaction):
        """Muestra el panel de planes de hoy."""
        await interaction.response.defer()
        settings = await get_guild_settings(interaction.guild_id)
        now = self.get_guild_now(settings.get("timezone", "America/Bogota"))
        today_str = now.strftime("%Y-%m-%d")

        plans = await get_daily_plans_for_date(interaction.guild_id, today_str)
        embed = await self.build_daily_embed(interaction.guild, now)
        view = DailyPlanView(plans) if plans else None

        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="plan-diario-enviar", description="Envía el resumen diario matutino inmediatamente a este canal")
    @app_commands.default_permissions(administrator=True)
    async def force_daily_briefing(self, interaction: discord.Interaction):
        """Fuerza el envío del resumen diario para probarlo."""
        await interaction.response.defer()
        settings = await get_guild_settings(interaction.guild_id)
        now = self.get_guild_now(settings.get("timezone", "America/Bogota"))

        embed = await self.build_daily_embed(interaction.guild, now)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="config-plan-diario", description="Configura el canal y hora para el resumen diario automático")
    @app_commands.describe(
        canal="Canal donde se publicará el plan del día cada mañana",
        hora="Hora de la mañana en formato 24h (ej: 8 para las 8:00 AM)"
    )
    @app_commands.default_permissions(administrator=True)
    async def config_daily_plan(self, interaction: discord.Interaction, canal: discord.TextChannel, hora: Optional[int] = 8):
        if hora is not None and not (0 <= hora <= 23):
            await interaction.response.send_message("❌ La hora debe estar entre 0 y 23 (ej: 8 para las 8:00 AM).", ephemeral=True)
            return

        await update_guild_setting(interaction.guild_id, "daily_plan_channel_id", canal.id)
        if hora is not None:
            await update_guild_setting(interaction.guild_id, "daily_plan_hour", hora)

        embed = discord.Embed(
            title="✅ Plan Diario Automático Configurado",
            description=f"El resumen matutino se publicará todos los días en {canal.mention} a las **{hora or 8}:00 AM**.",
            color=COLOR_SUCCESS
        )
        await interaction.response.send_message(embed=embed)

    @tasks.loop(minutes=1.0)
    async def briefing_loop(self):
        """Revisa cada minuto si es hora de publicar el plan matutino en los servidores."""
        for guild in self.bot.guilds:
            try:
                settings = await get_guild_settings(guild.id)
                tz_name = settings.get("timezone", "America/Bogota")
                now = self.get_guild_now(tz_name)

                target_hour = settings.get("daily_plan_hour", 8)
                # Ejecutar en el minuto 0 de la hora configurada
                if now.hour == target_hour and now.minute == 0:
                    today_str = now.strftime("%Y-%m-%d")
                    notif_key = f"daily_briefing_{guild.id}_{today_str}"

                    if await has_notification_been_sent(notif_key):
                        continue

                    # Determinar canal de destino
                    ch_id = settings.get("daily_plan_channel_id")
                    channel = guild.get_channel(ch_id) if ch_id else None

                    if not channel:
                        # Buscar por defecto
                        channel = discord.utils.get(guild.text_channels, name="general") or \
                                  discord.utils.get(guild.text_channels, name="chat-general") or \
                                  guild.system_channel

                    if channel and channel.permissions_for(guild.me).send_messages:
                        embed = await self.build_daily_embed(guild, now)
                        await channel.send(embed=embed)
                        await record_notification_sent(notif_key)
                        logger.info(f"Resumen diario enviado exitosamente a {guild.name} en #{channel.name}")
            except Exception as e:
                logger.error(f"Error en briefing_loop para {guild.name}: {e}")

    @briefing_loop.before_loop
    async def before_briefing_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(DailyPlansCog(bot))
