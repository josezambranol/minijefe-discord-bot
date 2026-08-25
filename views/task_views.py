import discord
from typing import Optional
from database import mark_task_completed, delete_task, postpone_task, get_task, get_guild_settings, get_tasks
from utils.date_parser import parse_task_date
from utils.embeds import task_detail_embed, task_list_embed, COLOR_SUCCESS, COLOR_DANGER

class PostponeModal(discord.ui.Modal, title="⏰ Posponer Fecha Límite"):
    def __init__(self, task_id: int, guild_id: int):
        super().__init__()
        self.task_id = task_id
        self.guild_id = guild_id

    new_date = discord.ui.TextInput(
        label="Nueva Fecha y Hora Límite",
        placeholder="Ej: mañana 18:00, en 3 dias, 30/08/2026 15:00",
        required=True,
        max_length=60
    )

    async def on_submit(self, interaction: discord.Interaction):
        settings = await get_guild_settings(self.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        
        parsed_dt, err = parse_task_date(self.new_date.value, tz_name)
        if err:
            await interaction.response.send_message(f"❌ **Error:** {err}", ephemeral=True)
            return

        success = await postpone_task(self.task_id, parsed_dt.isoformat())
        if success:
            updated_task = await get_task(self.task_id)
            embed = task_detail_embed(updated_task, tz_name)
            await interaction.response.send_message(
                f"✅ **Tarea #{self.task_id} pospuesta exitosamente.** Nuevo plazo fijado.",
                embed=embed,
                ephemeral=False
            )
        else:
            await interaction.response.send_message("❌ No se pudo actualizar la tarea.", ephemeral=True)

class TaskActionView(discord.ui.View):
    """Botonera interactiva para acciones rápidas en una tarea."""
    def __init__(self, task_id: int, guild_id: int, assigned_user_id: int, timeout: Optional[float] = None):
        super().__init__(timeout=timeout)
        self.task_id = task_id
        self.guild_id = guild_id
        self.assigned_user_id = assigned_user_id

    @discord.ui.button(label="Completar", style=discord.ButtonStyle.success, emoji="✅", custom_id="btn_complete")
    async def complete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        task = await get_task(self.task_id)
        if not task:
            await interaction.response.send_message("❌ Esta tarea ya no existe.", ephemeral=True)
            return

        if task["status"] == "completed":
            await interaction.response.send_message("ℹ️ Esta tarea ya estaba marcada como completada.", ephemeral=True)
            return

        await mark_task_completed(self.task_id)
        settings = await get_guild_settings(self.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        
        task["status"] = "completed"
        embed = task_detail_embed(task, tz_name)
        
        # Desactivar botones de acción principal
        for child in self.children:
            if child.custom_id in ["btn_complete", "btn_postpone"]:
                child.disabled = True

        await interaction.response.edit_message(
            content=f"🎉 **¡Tarea #{self.task_id} marcada como completada por {interaction.user.mention}!**",
            embed=embed,
            view=self
        )

    @discord.ui.button(label="Posponer", style=discord.ButtonStyle.secondary, emoji="⏰", custom_id="btn_postpone")
    async def postpone_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PostponeModal(self.task_id, self.guild_id))

    @discord.ui.button(label="Ver Detalles", style=discord.ButtonStyle.primary, emoji="🔍", custom_id="btn_details")
    async def details_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        task = await get_task(self.task_id)
        if not task:
            await interaction.response.send_message("❌ Esta tarea no existe.", ephemeral=True)
            return
        settings = await get_guild_settings(self.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        embed = task_detail_embed(task, tz_name)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Eliminar", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="btn_delete")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar permisos (creador, asignado o admin)
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
        if interaction.user.id not in [self.assigned_user_id] and not is_admin:
            # Permitir que el creador de la tarea también elimine
            task = await get_task(self.task_id)
            if not task or (task["creator_id"] != interaction.user.id and not is_admin):
                await interaction.response.send_message("❌ Solo el asignado, el creador o un administrador pueden eliminar esta tarea.", ephemeral=True)
                return

        await delete_task(self.task_id)
        await interaction.response.send_message(f"🗑️ Tarea #{self.task_id} eliminada permanentemente.", ephemeral=True)
        # Opcional: Desactivar toda la vista del mensaje original
        for child in self.children:
            child.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

class TaskListView(discord.ui.View):
    """Vista con botones de filtro para navegar entre listas de tareas."""
    def __init__(self, guild_id: int, user_id: Optional[int] = None, timeout: Optional[float] = 180):
        super().__init__(timeout=timeout)
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="Pendientes", style=discord.ButtonStyle.primary, emoji="📋")
    async def show_pending(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await get_guild_settings(self.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        tasks = await get_tasks(guild_id=self.guild_id, user_id=self.user_id, status="pending")
        embed = task_list_embed(tasks, "📋 Tareas Pendientes", "Tareas activas dentro del plazo", tz_name)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Vencidas", style=discord.ButtonStyle.danger, emoji="🔴")
    async def show_overdue(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await get_guild_settings(self.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        tasks = await get_tasks(guild_id=self.guild_id, user_id=self.user_id, status="overdue")
        embed = task_list_embed(tasks, "🔴 Tareas Vencidas", "Tareas cuyo plazo límite expiró", tz_name)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Completadas", style=discord.ButtonStyle.success, emoji="✅")
    async def show_completed(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await get_guild_settings(self.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        tasks = await get_tasks(guild_id=self.guild_id, user_id=self.user_id, status="completed")
        embed = task_list_embed(tasks, "✅ Tareas Completadas", "Historial de tareas finalizadas con éxito", tz_name)
        await interaction.response.edit_message(embed=embed, view=self)
