import discord
import re
from typing import Optional
from database import create_task, get_task, get_guild_settings
from utils.date_parser import parse_task_date
from utils.embeds import task_detail_embed
from .task_views import TaskActionView

class CreateTaskModal(discord.ui.Modal, title="📝 Nueva Tarea & Recordatorio"):
    def __init__(self, assigned_user: discord.Member, default_tz: str = "America/Bogota"):
        super().__init__()
        self.assigned_user = assigned_user
        self.default_tz = default_tz

    task_title = discord.ui.TextInput(
        label="Tema / Título de la Tarea",
        placeholder="Ej: Entregar informe financiero mensual",
        required=True,
        max_length=100
    )

    task_description = discord.ui.TextInput(
        label="Descripción o Detalles (Opcional)",
        placeholder="Detalles, enlaces de drive o requerimientos de la tarea...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )

    task_due_date = discord.ui.TextInput(
        label="Plazo / Fecha (Letras, Números o Flexible)",
        placeholder="Ej: 15 de septiembre 6 pm | a fin de mes | mañana 8 pm | por definir",
        required=True,
        max_length=80
    )

    task_reminder_time = discord.ui.TextInput(
        label="Hora del Recordatorio Diario (HH:MM)",
        placeholder="09:00 (o 08:30, 14:00, etc.)",
        default="09:00",
        required=False,
        max_length=5
    )

    async def on_submit(self, interaction: discord.Interaction):
        # 1. Obtener la zona horaria del servidor
        settings = await get_guild_settings(interaction.guild_id)
        tz_name = settings.get("timezone", self.default_tz)

        # 2. Validar y parsear la fecha límite (letras o números)
        parsed_dt, _, display_text = parse_task_date(self.task_due_date.value, tz_name)

        # 3. Validar formato de hora del recordatorio
        rem_time = self.task_reminder_time.value.strip() or "09:00"
        if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", rem_time):
            rem_time = "09:00"

        # 4. Guardar en Base de Datos
        task_id = await create_task(
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            creator_id=interaction.user.id,
            assigned_user_id=self.assigned_user.id,
            title=self.task_title.value.strip(),
            description=self.task_description.value.strip() if self.task_description.value else None,
            due_date_iso=parsed_dt.isoformat(),
            due_date_text=display_text,
            reminder_time=rem_time
        )

        task_data = await get_task(task_id)
        embed = task_detail_embed(task_data, tz_name)
        view = TaskActionView(task_id=task_id, guild_id=interaction.guild_id, assigned_user_id=self.assigned_user.id)

        await interaction.response.send_message(
            content=f"🎉 **¡Tarea agendada con éxito!** Plazo: `{display_text}` | Asignada a {self.assigned_user.mention}.",
            embed=embed,
            view=view
        )

