import discord
from typing import Optional
from database import get_guild_settings
from utils.embeds import day_schedule_embed, full_week_schedule_embed, today_live_class_embed

class ScheduleSelect(discord.ui.Select):
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        options = [
            discord.SelectOption(
                label="Lunes",
                value="lunes",
                description="Visualización de Datos I & Electiva I",
                emoji="🔵"
            ),
            discord.SelectOption(
                label="Martes",
                value="martes",
                description="Desarrollo de Software II",
                emoji="🟢"
            ),
            discord.SelectOption(
                label="Miércoles",
                value="miercoles",
                description="Bases de Datos II",
                emoji="🟡"
            ),
            discord.SelectOption(
                label="Jueves",
                value="jueves",
                description="Inglés III & Redes de Computadoras",
                emoji="🟠"
            ),
            discord.SelectOption(
                label="Viernes",
                value="viernes",
                description="Ecuaciones Diferenciales",
                emoji="🟣"
            ),
            discord.SelectOption(
                label="Semana Completa",
                value="semana",
                description="Ver toda la programación de Lunes a Viernes",
                emoji="🗓️"
            ),
            discord.SelectOption(
                label="¿Qué toca hoy? / En Vivo",
                value="hoy",
                description="Ver clase actual en curso y la que sigue hoy",
                emoji="🎓"
            )
        ]
        super().__init__(
            placeholder="📅 Elige un día para ver materias y salones...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        settings = await get_guild_settings(self.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        val = self.values[0]

        if val == "semana":
            embed = full_week_schedule_embed(tz_name)
        elif val == "hoy":
            embed = today_live_class_embed(tz_name)
        else:
            embed = day_schedule_embed(val, tz_name)

        await interaction.response.edit_message(embed=embed, view=self.view)

class ScheduleView(discord.ui.View):
    """Vista interactiva con menú selector y botones rápidos para el horario."""
    def __init__(self, guild_id: int, timeout: Optional[float] = 300):
        super().__init__(timeout=timeout)
        self.guild_id = guild_id
        self.add_item(ScheduleSelect(guild_id=guild_id))

    @discord.ui.button(label="Hoy en Vivo", style=discord.ButtonStyle.primary, emoji="🎓", row=1)
    async def btn_today(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await get_guild_settings(self.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        embed = today_live_class_embed(tz_name)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Semana", style=discord.ButtonStyle.secondary, emoji="🗓️", row=1)
    async def btn_week(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await get_guild_settings(self.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        embed = full_week_schedule_embed(tz_name)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Lunes", style=discord.ButtonStyle.secondary, emoji="🔵", row=2)
    async def btn_lunes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_day(interaction, "lunes")

    @discord.ui.button(label="Martes", style=discord.ButtonStyle.secondary, emoji="🟢", row=2)
    async def btn_martes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_day(interaction, "martes")

    @discord.ui.button(label="Miércoles", style=discord.ButtonStyle.secondary, emoji="🟡", row=2)
    async def btn_miercoles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_day(interaction, "miercoles")

    @discord.ui.button(label="Jueves", style=discord.ButtonStyle.secondary, emoji="🟠", row=2)
    async def btn_jueves(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_day(interaction, "jueves")

    @discord.ui.button(label="Viernes", style=discord.ButtonStyle.secondary, emoji="🟣", row=2)
    async def btn_viernes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_day(interaction, "viernes")

    async def _show_day(self, interaction: discord.Interaction, day_key: str):
        settings = await get_guild_settings(self.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        embed = day_schedule_embed(day_key, tz_name)
        await interaction.response.edit_message(embed=embed, view=self)
