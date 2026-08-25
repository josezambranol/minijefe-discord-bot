import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Literal

from database import get_guild_settings
from utils.embeds import (
    day_schedule_embed, full_week_schedule_embed, today_live_class_embed,
    COLOR_INFO
)
from utils.date_parser import get_now
from utils.schedule_data import (
    SCHEDULE_DATA, get_day_key_from_datetime, get_all_subjects_list
)

from views.schedule_views import ScheduleView

class ScheduleCog(commands.Cog, name="Horario Académico"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="horario", description="Consultar el horario de clases interactivo por días o semanal")
    @app_commands.describe(
        dia="Día específico a consultar o semana completa"
    )
    async def schedule_cmd(
        self,
        interaction: discord.Interaction,
        dia: Optional[Literal["hoy", "lunes", "martes", "miercoles", "jueves", "viernes", "semana"]] = "hoy"
    ):
        settings = await get_guild_settings(interaction.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        now = get_now(tz_name)

        if dia == "hoy":
            today_key = get_day_key_from_datetime(now)
            if today_key:
                embed = day_schedule_embed(today_key, tz_name)
            else:
                embed = today_live_class_embed(tz_name)
        elif dia == "semana":
            embed = full_week_schedule_embed(tz_name)
        else:
            embed = day_schedule_embed(dia, tz_name)

        view = ScheduleView(guild_id=interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="clase", description="Ver qué clase toca hoy en vivo, la que está en curso o la siguiente")
    async def live_class_cmd(self, interaction: discord.Interaction):
        settings = await get_guild_settings(interaction.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        embed = today_live_class_embed(tz_name)
        view = ScheduleView(guild_id=interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="hoy", description="Resumen completo del día (clases de hoy con salones y tareas pendientes)")
    async def today_briefing_cmd(self, interaction: discord.Interaction):
        from database import get_tasks
        from utils.embeds import today_briefing_embed

        settings = await get_guild_settings(interaction.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        tasks = await get_tasks(guild_id=interaction.guild_id, status="pending")
        embed = today_briefing_embed(tasks, tz_name)
        view = ScheduleView(guild_id=interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="materias", description="Directorio completo de asignaturas, códigos, salones y docentes")

    async def subjects_directory_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📚 Directorio de Asignaturas & Docentes",
            description="Información detallada del semestre en Cedesarrollo:\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=COLOR_INFO
        )

        seen = set()
        for day_key, day_data in SCHEDULE_DATA.items():
            for cls in day_data["classes"]:
                if cls["subject"] in seen:
                    continue
                seen.add(cls["subject"])
                
                embed.add_field(
                    name=f"{cls['icon']} {cls['subject']}",
                    value=(
                        f"• **Día y Hora:** `{day_data['name']}` ({cls['start']} - {cls['end']})\n"
                        f"• **Docente:** `{cls['teacher']}`\n"
                        f"• **Salón:** `{cls['location']}`\n"
                        f"• **Código:** `{cls['code']}`"
                    ),
                    inline=False
                )

        embed.set_footer(text="MiniJefe • Horario de Ingeniería")
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ScheduleCog(bot))
