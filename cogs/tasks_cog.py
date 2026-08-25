import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Literal
from database import (
    get_task, get_tasks, get_overdue_tasks, mark_task_completed, 
    delete_task, postpone_task, get_guild_settings, get_task_stats, create_task
)
from utils.date_parser import parse_task_date
from utils.embeds import (
    task_detail_embed, task_list_embed, stats_embed, welcome_introduction_embed,
    COLOR_SUCCESS, COLOR_DANGER
)
from views.task_modal import CreateTaskModal
from views.task_views import TaskActionView, TaskListView

class TasksCog(commands.Cog, name="Gestión de Tareas"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="presentar", description="Muestra el mensaje de presentación de MiniJefe y guía de uso")
    async def introduce_bot_cmd(self, interaction: discord.Interaction):
        embed = welcome_introduction_embed()
        await interaction.response.send_message(embed=embed)

    task_group = app_commands.Group(name="tarea", description="Comandos para gestionar tareas y recordatorios")


    @task_group.command(name="crear", description="Agendar una nueva tarea con fecha límite y recordatorio diario")
    @app_commands.describe(
        asignar_a="Usuario al que se le asignará la tarea (por defecto tú mismo)",
        tema="Título o tema de la tarea (si no se especifica, se abrirá un formulario emergente)",
        materia="Materia o asignatura a la que pertenece esta tarea (opcional)",
        plazo="Fecha y hora límite (ej: mañana 18:00, 2026-08-30 15:00, en 3 dias)",
        descripcion="Detalles u observaciones de la tarea",
        hora_recordatorio="Hora para el recordatorio diario en formato 24h (ej: 09:00)"
    )
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: (i.guild_id, i.user.id))
    async def task_create(
        self,
        interaction: discord.Interaction,
        asignar_a: Optional[discord.Member] = None,
        tema: Optional[str] = None,
        materia: Optional[str] = None,
        plazo: Optional[str] = None,
        descripcion: Optional[str] = None,
        hora_recordatorio: Optional[str] = "09:00"
    ):
        target_user = asignar_a or interaction.user
        settings = await get_guild_settings(interaction.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")

        # Si especificó materia, concatenarla con estilo al tema
        final_title = f"[{materia}] {tema.strip()}" if materia and tema else (tema.strip() if tema else None)

        # Si no especificó tema ni plazo, abrir modal emergente
        if not final_title or not plazo:
            modal = CreateTaskModal(assigned_user=target_user, default_tz=tz_name)
            await interaction.response.send_modal(modal)
            return

        # Si especificó parámetros en el comando, crearlo directamente
        parsed_dt, err = parse_task_date(plazo, tz_name)
        if err:
            await interaction.response.send_message(f"❌ **Error en la fecha límite:** {err}", ephemeral=True)
            return

        task_id = await create_task(
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            creator_id=interaction.user.id,
            assigned_user_id=target_user.id,
            title=final_title,
            description=descripcion.strip() if descripcion else None,
            due_date_iso=parsed_dt.isoformat(),
            reminder_time=hora_recordatorio.strip() if hora_recordatorio else "09:00"
        )

        task_data = await get_task(task_id)
        embed = task_detail_embed(task_data, tz_name)
        view = TaskActionView(task_id=task_id, guild_id=interaction.guild_id, assigned_user_id=target_user.id)

        await interaction.response.send_message(
            content=f"🎉 **¡Tarea agendada con éxito!** Se asignó a {target_user.mention}.",
            embed=embed,
            view=view
        )

    @app_commands.command(name="tareas", description="Ver el panel de tareas asignadas (pendientes, vencidas, completadas)")
    @app_commands.describe(
        filtro="Filtrar por estado de la tarea",
        usuario="Ver únicamente las tareas de un usuario específico"
    )
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: (i.guild_id, i.user.id))
    async def list_tasks(
        self,
        interaction: discord.Interaction,
        filtro: Optional[Literal["pendientes", "vencidas", "completadas", "todas"]] = "pendientes",
        usuario: Optional[discord.Member] = None
    ):
        settings = await get_guild_settings(interaction.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        user_id = usuario.id if usuario else None

        status_filter = None if filtro == "todas" else ("pending" if filtro == "pendientes" else ("overdue" if filtro == "vencidas" else "completed"))
        tasks = await get_tasks(guild_id=interaction.guild_id, user_id=user_id, status=status_filter)

        titles = {
            "pendientes": "📋 Tareas Pendientes",
            "vencidas": "🔴 Tareas Vencidas (Atrasadas)",
            "completadas": "✅ Tareas Completadas",
            "todas": "📑 Todas las Tareas Registradas"
        }
        
        user_mention_str = f" de {usuario.display_name}" if usuario else ""
        embed = task_list_embed(
            tasks,
            title=f"{titles.get(filtro, '📋 Lista de Tareas')}{user_mention_str}",
            filter_desc=f"Filtro activo: `{filtro.upper()}`" + (f" | Usuario: {usuario.mention}" if usuario else ""),
            tz_name=tz_name
        )

        view = TaskListView(guild_id=interaction.guild_id, user_id=user_id)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="vencidas", description="Ver exclusivamente el apartado de tareas atrasadas/vencidas")
    @app_commands.describe(usuario="Filtrar por usuario asignado")
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: (i.guild_id, i.user.id))
    async def overdue_tasks_cmd(

        self,
        interaction: discord.Interaction,
        usuario: Optional[discord.Member] = None
    ):
        settings = await get_guild_settings(interaction.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        user_id = usuario.id if usuario else None

        tasks = await get_overdue_tasks(guild_id=interaction.guild_id, user_id=user_id)
        user_txt = f" de {usuario.display_name}" if usuario else ""
        
        embed = task_list_embed(
            tasks,
            title=f"🚨 Apartado de Tareas Vencidas{user_txt}",
            filter_desc="Estas tareas no se completaron antes de la fecha límite y requieren atención inmediata:",
            tz_name=tz_name
        )
        view = TaskListView(guild_id=interaction.guild_id, user_id=user_id)
        await interaction.response.send_message(embed=embed, view=view)

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

    @task_group.command(name="completar", description="Marcar una tarea como completada")
    @app_commands.describe(id="ID numérico de la tarea a completar")
    async def complete_task_cmd(self, interaction: discord.Interaction, id: int):
        task = await get_task(id)
        if not task or task["guild_id"] != interaction.guild_id:
            await interaction.response.send_message(f"❌ No se encontró la tarea `#{id}`.", ephemeral=True)
            return

        if task["status"] == "completed":
            await interaction.response.send_message(f"ℹ️ La tarea `#{id}` ya estaba completada.", ephemeral=True)
            return

        await mark_task_completed(id)
        settings = await get_guild_settings(interaction.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        task["status"] = "completed"
        embed = task_detail_embed(task, tz_name)

        await interaction.response.send_message(
            content=f"🎉 **¡Tarea #{id} completada exitosamente por {interaction.user.mention}!**",
            embed=embed
        )

    @task_group.command(name="posponer", description="Ampliar el plazo de una tarea")
    @app_commands.describe(
        id="ID de la tarea",
        nuevo_plazo="Nueva fecha límite (ej: mañana 20:00, 2026-09-01 12:00, en 3 dias)"
    )
    async def postpone_task_cmd(self, interaction: discord.Interaction, id: int, nuevo_plazo: str):
        task = await get_task(id)
        if not task or task["guild_id"] != interaction.guild_id:
            await interaction.response.send_message(f"❌ No se encontró la tarea `#{id}`.", ephemeral=True)
            return

        settings = await get_guild_settings(interaction.guild_id)
        tz_name = settings.get("timezone", "America/Bogota")
        parsed_dt, err = parse_task_date(nuevo_plazo, tz_name)
        if err:
            await interaction.response.send_message(f"❌ **Error:** {err}", ephemeral=True)
            return

        await postpone_task(id, parsed_dt.isoformat())
        updated_task = await get_task(id)
        embed = task_detail_embed(updated_task, tz_name)
        view = TaskActionView(task_id=id, guild_id=interaction.guild_id, assigned_user_id=task["assigned_user_id"])

        await interaction.response.send_message(
            content=f"⏰ **Tarea #{id} pospuesta con éxito.**",
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
    @app_commands.describe(usuario="Filtrar estadísticas por usuario")
    async def stats_cmd(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
        user_id = usuario.id if usuario else None
        stats = await get_task_stats(interaction.guild_id, user_id)
        target_name = usuario.display_name if usuario else interaction.guild.name
        embed = stats_embed(stats, target_name)
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(TasksCog(bot))
