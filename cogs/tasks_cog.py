import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Literal, List
from database import (
    get_task, get_tasks, get_overdue_tasks, mark_task_completed, 
    delete_task, postpone_task, get_guild_settings, get_task_stats, create_task
)
from utils.date_parser import parse_task_date
from utils.schedule_data import get_all_subjects_list
from utils.team_data import get_team_directory_info, find_guild_member_for_team_entry
from utils.embeds import (
    task_detail_embed, task_list_embed, stats_embed, welcome_introduction_embed,
    team_directory_embed
)
from utils.auto_cleaner import send_clean_panel_interaction
from views.task_modal import CreateTaskModal
from views.task_views import TaskActionView, TaskListView

class TasksCog(commands.Cog, name="Gestión de Tareas"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="presentar", description="Muestra el mensaje de presentación de MiniJefe y guía de uso")
    async def introduce_bot_cmd(self, interaction: discord.Interaction):
        embed = welcome_introduction_embed()
        await send_clean_panel_interaction(interaction, "intro_panel", embed)

    @app_commands.command(name="equipo", description="Ver el directorio y estado del equipo oficial (5 integrantes)")
    async def squad_directory_cmd(self, interaction: discord.Interaction):
        """Muestra el estado de los 5 miembros (jote, jordy, rafxzz, ByLogan, SEVINHO)."""
        pending_tasks = await get_tasks(guild_id=interaction.guild_id, status="pending")
        counts = {}
        for t in pending_tasks:
            u_id = t["assigned_user_id"]
            counts[u_id] = counts.get(u_id, 0) + 1

        embed = team_directory_embed(interaction.guild, member_task_counts=counts)
        await send_clean_panel_interaction(interaction, "team_panel", embed)

    task_group = app_commands.Group(name="tarea", description="Comandos para gestionar entregas y recordatorios")

    async def subject_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        subjects = get_all_subjects_list()
        choices = []
        for s in subjects:
            if current.lower() in s.lower():
                choices.append(app_commands.Choice(name=s, value=s))
            if len(choices) >= 25:
                break
        return choices

    @task_group.command(name="crear", description="Agendar una nueva entrega para el equipo (en números, letras o flexible)")
    @app_commands.describe(
        tema="Título o tema de la tarea (si no se especifica, se abrirá un formulario)",
        materia="Materia o asignatura a la que pertenece esta entrega (con autocompletado)",
        plazo="Fecha o plazo (ej: 15 de septiembre 6 pm, a fin de mes, mañana 8 pm, por definir)",
        descripcion="Detalles, enlaces de drive o requerimientos de la entrega",
        hora_recordatorio="Hora para el recordatorio diario en formato 24h (ej: 09:00)"
    )
    @app_commands.autocomplete(materia=subject_autocomplete)
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: (i.guild_id, i.user.id))
    async def task_create(
        self,
        interaction: discord.Interaction,
        tema: Optional[str] = None,
        materia: Optional[str] = None,
        plazo: Optional[str] = None,
        descripcion: Optional[str] = None,
        hora_recordatorio: Optional[str] = "09:00"
    ):
        settings = await get_guild_settings(interaction.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")

        final_title = f"[{materia}] {tema.strip()}" if materia and tema else (tema.strip() if tema else None)

        # Si no especificó tema ni plazo, abrir modal emergente
        if not final_title or not plazo:
            modal = CreateTaskModal(default_tz=tz_name)
            await interaction.response.send_modal(modal)
            return

        # Parseo universal (letras o números)
        parsed_dt, _, display_text = parse_task_date(plazo, tz_name)

        task_id = await create_task(
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            creator_id=interaction.user.id,
            assigned_user_id=interaction.user.id,
            title=final_title,
            description=descripcion.strip() if descripcion else None,
            due_date_iso=parsed_dt.isoformat(),
            due_date_text=display_text,
            reminder_time=hora_recordatorio.strip() if hora_recordatorio else "09:00"
        )

        task_data = await get_task(task_id)
        embed = task_detail_embed(task_data, tz_name)
        view = TaskActionView(task_id=task_id, guild_id=interaction.guild_id, assigned_user_id=interaction.user.id)

        await interaction.response.send_message(
            content=f"🎉 **¡Nueva entrega agendada para el equipo!** Plazo: `{display_text}` | Agendada por {interaction.user.mention}.",
            embed=embed,
            view=view
        )

    @app_commands.command(name="tareas", description="Ver todas las tareas y entregas compartidas del equipo")
    @app_commands.describe(
        filtro="Filtrar por estado de la tarea (pendientes, vencidas, completadas, todas)"
    )
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: (i.guild_id, i.user.id))
    async def list_tasks(
        self,
        interaction: discord.Interaction,
        filtro: Optional[Literal["pendientes", "vencidas", "completadas", "todas"]] = "pendientes"
    ):
        settings = await get_guild_settings(interaction.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")

        status_filter = None if filtro == "todas" else ("pending" if filtro == "pendientes" else ("overdue" if filtro == "vencidas" else "completed"))
        tasks = await get_tasks(guild_id=interaction.guild_id, status=status_filter)

        titles = {
            "pendientes": "📋 Tareas Pendientes del Equipo",
            "vencidas": "🔴 Tareas Vencidas del Equipo",
            "completadas": "✅ Tareas Completadas",
            "todas": "📑 Todas las Tareas del Equipo"
        }
        
        embed = task_list_embed(
            tasks,
            title=titles.get(filtro, "📋 Lista de Tareas del Equipo"),
            filter_desc=f"Filtro activo: `{filtro.upper()}` • Tareas visibles para los 5 integrantes",
            tz_name=tz_name
        )

        view = TaskListView(guild_id=interaction.guild_id)
        await send_clean_panel_interaction(interaction, "tasks_panel", embed, view=view)

    @app_commands.command(name="vencidas", description="Ver todas las tareas atrasadas/vencidas del equipo")
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: (i.guild_id, i.user.id))
    async def overdue_tasks_cmd(
        self,
        interaction: discord.Interaction
    ):
        settings = await get_guild_settings(interaction.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")

        tasks = await get_overdue_tasks(guild_id=interaction.guild_id)
        
        embed = task_list_embed(
            tasks,
            title="🚨 Apartado de Tareas Vencidas del Equipo",
            filter_desc="Estas entregas del equipo no se completaron a tiempo y requieren atención inmediata:",
            tz_name=tz_name
        )
        view = TaskListView(guild_id=interaction.guild_id)
        await send_clean_panel_interaction(interaction, "overdue_panel", embed, view=view)

    @task_group.command(name="ver", description="Consultar los detalles de una tarea por su ID")
    @app_commands.describe(id="ID numérico de la tarea")
    async def view_task_cmd(self, interaction: discord.Interaction, id: int):
        task = await get_task(id)
        if not task or task["guild_id"] != interaction.guild_id:
            await interaction.response.send_message(f"❌ No se encontró ninguna tarea con el ID `#{id}`.", ephemeral=True)
            return

        settings = await get_guild_settings(interaction.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        embed = task_detail_embed(task, tz_name)
        view = TaskActionView(task_id=id, guild_id=interaction.guild_id, assigned_user_id=task["assigned_user_id"])
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="completar", description="Marcar una tarea como completada y silenciar sus recordatorios")
    @app_commands.describe(id="ID numérico de la tarea")
    async def complete_direct_cmd(self, interaction: discord.Interaction, id: int):
        await self._handle_completion(interaction, id)

    @task_group.command(name="completar", description="Marcar una tarea como completada")
    @app_commands.describe(id="ID numérico de la tarea")
    async def complete_task_cmd(self, interaction: discord.Interaction, id: int):
        await self._handle_completion(interaction, id)

    async def _handle_completion(self, interaction: discord.Interaction, id: int):
        task = await get_task(id)
        if not task or task["guild_id"] != interaction.guild_id:
            await interaction.response.send_message(f"❌ No se encontró la tarea `#{id}`.", ephemeral=True)
            return

        if task["status"] == "completed":
            await interaction.response.send_message(f"ℹ️ La tarea `#{id}` ya estaba finalizada.", ephemeral=True)
            return

        await mark_task_completed(id, completed_by_id=interaction.user.id)
        settings = await get_guild_settings(interaction.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        
        updated_task = await get_task(id)
        embed = task_detail_embed(updated_task, tz_name)

        await interaction.response.send_message(
            content=f"🎉 **¡Tarea #{id} completada exitosamente por {interaction.user.mention}!** ✨\n*(Los recordatorios automáticos han sido desactivados)*",
            embed=embed
        )

    @task_group.command(name="posponer", description="Ampliar el plazo de una tarea (en letras o números)")
    @app_commands.describe(
        id="ID de la tarea",
        nuevo_plazo="Nuevo plazo (ej: 15 de septiembre 6 pm, a fin de mes, en 1 semana)"
    )
    async def postpone_task_cmd(self, interaction: discord.Interaction, id: int, nuevo_plazo: str):
        task = await get_task(id)
        if not task or task["guild_id"] != interaction.guild_id:
            await interaction.response.send_message(f"❌ No se encontró la tarea `#{id}`.", ephemeral=True)
            return

        settings = await get_guild_settings(interaction.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        parsed_dt, _, display_text = parse_task_date(nuevo_plazo, tz_name)

        await postpone_task(id, parsed_dt.isoformat())
        updated_task = await get_task(id)
        embed = task_detail_embed(updated_task, tz_name)
        view = TaskActionView(task_id=id, guild_id=interaction.guild_id, assigned_user_id=task["assigned_user_id"])

        await interaction.response.send_message(
            content=f"⏰ **Tarea #{id} pospuesta con éxito.** Nuevo plazo: `{display_text}`",
            embed=embed,
            view=view
        )

    @task_group.command(name="eliminar", description="Eliminar permanentemente una tarea")
    @app_commands.describe(id="ID de la tarea a eliminar")
    async def delete_task_cmd(self, interaction: discord.Interaction, id: int):
        task = await get_task(id)
        if not task or task["guild_id"] != interaction.guild_id:
            await interaction.response.send_message(f"❌ No se encontró la tarea `#{id}`.", ephemeral=True)
            return

        is_admin = interaction.user.guild_permissions.administrator
        if interaction.user.id not in [task["assigned_user_id"], task["creator_id"]] and not is_admin:
            await interaction.response.send_message("❌ Solo el asignado, el creador o un administrador pueden eliminar esta tarea.", ephemeral=True)
            return

        await delete_task(id)
        await interaction.response.send_message(f"🗑️ **Tarea #{id} ('{task['title']}') eliminada con éxito.**", ephemeral=True)

    @app_commands.command(name="estadisticas", description="Ver el tablero de estadísticas de tareas")
    @app_commands.describe(usuario="Filtrar estadísticas por integrante")
    async def stats_cmd(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
        user_id = usuario.id if usuario else None
        stats = await get_task_stats(interaction.guild_id, user_id)
        target_name = usuario.display_name if usuario else interaction.guild.name
        embed = stats_embed(stats, target_name)
        await send_clean_panel_interaction(interaction, "stats_panel", embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(TasksCog(bot))
