import discord
from discord.ext import commands, tasks
from discord import app_commands
import re
import logging
from datetime import datetime, timezone
from typing import Optional, List

from database import (
    add_periodic_reminder,
    get_active_periodic_reminders,
    get_periodic_reminder,
    update_periodic_reminder_sent,
    complete_periodic_reminder,
    cancel_periodic_reminder
)
from utils.embeds import COLOR_WARNING, COLOR_SUCCESS, COLOR_DANGER, COLOR_INFO

logger = logging.getLogger("MiniJefe.PeriodicReminders")

def is_staff(member: discord.Member) -> bool:
    """Verifica si un usuario cuenta con permisos de moderación o administración en el servidor."""
    if member.guild and member.id == member.guild.owner_id:
        return True
    if member.guild_permissions.administrator or member.guild_permissions.manage_guild or member.guild_permissions.manage_messages:
        return True
    return False

def format_interval(minutes: int) -> str:
    """Formatea minutos a texto legible."""
    if minutes < 60:
        return f"{minutes} minutos"
    hours = minutes // 60
    rem = minutes % 60
    if rem == 0:
        return f"{hours} hora{'s' if hours > 1 else ''}"
    return f"{hours}h {rem}m"


class PeriodicReminderActionView(discord.ui.View):
    """Botonera interactiva en cada mensaje de recordatorio."""

    def __init__(self, reminder_id: int, assigned_user_id: int, creator_id: int):
        super().__init__(timeout=None)
        self.reminder_id = reminder_id
        self.assigned_user_id = assigned_user_id
        self.creator_id = creator_id

    @discord.ui.button(label="✅ Marcar como Listo", style=discord.ButtonStyle.success, custom_id="btn_complete_periodic")
    async def btn_complete(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        member = interaction.guild.get_member(user.id) if interaction.guild else None
        is_authorized = (
            user.id == self.assigned_user_id or
            user.id == self.creator_id or
            (member and is_staff(member))
        )

        if not is_authorized:
            await interaction.response.send_message("❌ Esta tarea está asignada a otro usuario. Solo la persona asignada, quien la creó o el Staff pueden completarla.", ephemeral=True)
            return

        success = await complete_periodic_reminder(self.reminder_id)
        if success:
            button.disabled = True
            button.label = f"✅ Completada por {user.display_name}"
            for child in self.children:
                child.disabled = True

            embed = discord.Embed(
                title="🎉 Tarea Finalizada",
                description=f"La tarea **#{self.reminder_id}** ha sido completada por {user.mention}.\n*(Se han desactivado los recordatorios periódicos).*",
                color=COLOR_SUCCESS
            )
            embed.set_footer(text=f"Servidor: {interaction.guild.name if interaction.guild else 'Comunidad'}")
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message("⚠️ Esta tarea ya no se encuentra activa o ya fue completada.", ephemeral=True)

    @discord.ui.button(label="🛑 Cancelar Recordatorio", style=discord.ButtonStyle.danger, custom_id="btn_cancel_periodic")
    async def btn_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        member = interaction.guild.get_member(user.id) if interaction.guild else None
        is_authorized = (
            user.id == self.creator_id or
            user.id == self.assigned_user_id or
            (member and is_staff(member))
        )

        if not is_authorized:
            await interaction.response.send_message("❌ Solo quien creó la tarea, la persona asignada o un miembro del Staff pueden cancelarla.", ephemeral=True)
            return

        success = await cancel_periodic_reminder(self.reminder_id)
        if success:
            for child in self.children:
                child.disabled = True

            embed = discord.Embed(
                title="🛑 Recordatorio Cancelado",
                description=f"El recordatorio **#{self.reminder_id}** fue cancelado por {user.mention}.\nNo se enviarán más avisos.",
                color=COLOR_DANGER
            )
            embed.set_footer(text=f"Servidor: {interaction.guild.name if interaction.guild else 'Comunidad'}")
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message("⚠️ Este recordatorio ya no está activo.", ephemeral=True)


class PeriodicRemindersCog(commands.Cog, name="Recordatorios Periódicos y Delegados"):
    """Permite asignar tareas y recordar a usuarios periódicamente en el servidor."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminder_check_loop.start()

    def cog_unload(self):
        self.reminder_check_loop.cancel()

    @tasks.loop(seconds=45)
    async def reminder_check_loop(self):
        """Revisa cada 45 segundos si algún recordatorio periódico ha cumplido su intervalo."""
        try:
            active_reminders = await get_active_periodic_reminders()
            now_dt = datetime.now(timezone.utc)

            for rem in active_reminders:
                rem_id = rem["id"]
                guild_id = rem["guild_id"]
                channel_id = rem["channel_id"]
                assigned_user_id = rem["assigned_user_id"]
                creator_id = rem["creator_id"]
                title = rem["title"]
                interval_minutes = rem["interval_minutes"]
                send_dm = rem["send_dm"]
                last_reminded_str = rem["last_reminded_at"]

                # Parsear última fecha de recordatorio
                try:
                    last_reminded_dt = datetime.fromisoformat(last_reminded_str)
                    if last_reminded_dt.tzinfo is None:
                        last_reminded_dt = last_reminded_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    last_reminded_dt = now_dt

                elapsed_seconds = (now_dt - last_reminded_dt).total_seconds()
                required_seconds = interval_minutes * 60

                if elapsed_seconds >= required_seconds:
                    await self.send_periodic_notification(
                        rem_id=rem_id,
                        guild_id=guild_id,
                        channel_id=channel_id,
                        assigned_user_id=assigned_user_id,
                        creator_id=creator_id,
                        title=title,
                        interval_minutes=interval_minutes,
                        send_dm=bool(send_dm)
                    )
        except Exception as e:
            logger.error(f"Error en reminder_check_loop: {e}", exc_info=True)

    @reminder_check_loop.before_loop
    async def before_reminder_loop(self):
        await self.bot.wait_until_ready()

    async def send_periodic_notification(
        self,
        rem_id: int,
        guild_id: int,
        channel_id: int,
        assigned_user_id: int,
        creator_id: int,
        title: str,
        interval_minutes: int,
        send_dm: bool = False
    ):
        """Envía el mensaje de recordatorio periódico en el canal y opcionalmente por DM."""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        channel = guild.get_channel(channel_id)
        assigned_user = guild.get_member(assigned_user_id) or await self.bot.fetch_user(assigned_user_id)
        if not assigned_user:
            return

        interval_text = format_interval(interval_minutes)

        embed = discord.Embed(
            title="⏰ Recordatorio de Tarea Pendiente",
            description=(
                f"Hola {assigned_user.mention}, tienes una tarea activa en **{guild.name}**:\n\n"
                f"📌 **Tarea:** {title}\n"
                f"🔄 **Frecuencia:** Cada **{interval_text}**\n"
                f"✍️ **Asignada por:** <@{creator_id}>\n\n"
                f"Cuando termines, pulsa el botón **`[✅ Marcar como Listo]`** para confirmar su finalización."
            ),
            color=COLOR_WARNING
        )
        embed.set_footer(text=f"ID de Tarea: #{rem_id} • Servidor: {guild.name}")

        view = PeriodicReminderActionView(reminder_id=rem_id, assigned_user_id=assigned_user_id, creator_id=creator_id)

        sent = False
        if channel and isinstance(channel, discord.TextChannel):
            try:
                await channel.send(
                    content=f"🔔 {assigned_user.mention} — Recordatorio de tu tarea pendiente:",
                    embed=embed,
                    view=view
                )
                sent = True
            except Exception as e:
                logger.warning(f"No se pudo enviar recordatorio en canal #{channel.name}: {e}")

        if send_dm and hasattr(assigned_user, "send"):
            try:
                dm_view = PeriodicReminderActionView(reminder_id=rem_id, assigned_user_id=assigned_user_id, creator_id=creator_id)
                await assigned_user.send(
                    content=f"🔔 Recordatorio de tu tarea en **{guild.name}**:",
                    embed=embed,
                    view=dm_view
                )
                sent = True
            except Exception:
                pass

        if sent:
            now_iso = datetime.now(timezone.utc).isoformat()
            await update_periodic_reminder_sent(rem_id, now_iso)
            logger.info(f"Recordatorio #{rem_id} enviado a {assigned_user.display_name} cada {interval_text}")

    @app_commands.command(name="recordar", description="Asigna una tarea o recordatorio periódico con intervalo flexible")
    @app_commands.describe(
        usuario="Usuario a quien se le asignará la tarea",
        tarea="Descripción de la tarea o pendiente",
        cada_horas="Frecuencia del recordatorio en horas (ej: 2 para cada 2 horas, 0.5 para cada 30 min)",
        por_md="Si es True, además del canal le enviará un mensaje directo al usuario"
    )
    async def slash_recordar(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        tarea: str,
        cada_horas: Optional[float] = 2.0,
        por_md: Optional[bool] = False
    ):
        """Comando slash para delegar recordatorios periódicos."""
        member = interaction.guild.get_member(interaction.user.id)
        if usuario.id != interaction.user.id and not is_staff(member):
            await interaction.response.send_message("❌ Solo miembros del Staff pueden asignar tareas a otros usuarios. Puedes asignarte tareas a ti mismo.", ephemeral=True)
            return

        interval_minutes = max(int(cada_horas * 60), 5)
        rem_id = await add_periodic_reminder(
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            creator_id=interaction.user.id,
            assigned_user_id=usuario.id,
            title=tarea.strip(),
            interval_minutes=interval_minutes,
            send_dm=1 if por_md else 0
        )

        interval_display = format_interval(interval_minutes)
        dm_note = " (con avisos por Mensaje Directo)" if por_md else ""

        embed = discord.Embed(
            title="📋 Tarea Registrada Exitosamente",
            description=(
                f"Se ha registrado la tarea en el sistema de **{interaction.guild.name}**:\n\n"
                f"📌 **Tarea:** {tarea.strip()}\n"
                f"👤 **Asignada a:** {usuario.mention}\n"
                f"🔄 **Frecuencia:** Cada **{interval_display}**{dm_note}\n\n"
                f"*(Se notificarán avisos periódicos hasta que sea completada).*"
            ),
            color=COLOR_SUCCESS
        )
        embed.set_footer(text=f"ID de Tarea: #{rem_id} • Servidor: {interaction.guild.name}")
        view = PeriodicReminderActionView(reminder_id=rem_id, assigned_user_id=usuario.id, creator_id=interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="recordatorios-activos", description="Muestra todas las tareas periódicas activas en el servidor")
    async def slash_list_reminders(self, interaction: discord.Interaction):
        """Consulta todos los recordatorios activos del servidor."""
        reminders = await get_active_periodic_reminders(interaction.guild_id)
        if not reminders:
            await interaction.response.send_message("✨ **No hay recordatorios periódicos activos en este momento.** Todo se encuentra al día.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📋 Tareas y Recordatorios Activos — {interaction.guild.name}",
            description=f"Hay **{len(reminders)}** tareas en seguimiento activo:",
            color=COLOR_INFO
        )

        for rem in reminders[:15]:
            interval_display = format_interval(rem["interval_minutes"])
            dm_badge = " 📬 *(Avisos por DM)*" if rem["send_dm"] else ""
            field_name = f"#{rem['id']} — {rem['title'][:80]}"
            field_val = (
                f"• **Asignada a:** <@{rem['assigned_user_id']}>\n"
                f"• **Frecuencia:** Cada `{interval_display}`{dm_badge}\n"
                f"• **Canal:** <#{rem['channel_id']}> | **Por:** <@{rem['creator_id']}>"
            )
            embed.add_field(name=field_name, value=field_val, inline=False)

        embed.set_footer(text=f"Servidor: {interaction.guild.name} • Completa con /tarea-lista [id]")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="tarea-lista", description="Marca una tarea periódica como completada y detiene los avisos")
    @app_commands.describe(id="ID del recordatorio a completar (ej: 1, 2, 3)")
    async def slash_complete_task(self, interaction: discord.Interaction, id: int):
        rem = await get_periodic_reminder(id)
        if not rem or rem["guild_id"] != interaction.guild_id:
            await interaction.response.send_message(f"❌ No se encontró ninguna tarea con el ID `#{id}` en este servidor.", ephemeral=True)
            return

        member = interaction.guild.get_member(interaction.user.id)
        is_authorized = (
            interaction.user.id == rem["assigned_user_id"] or
            interaction.user.id == rem["creator_id"] or
            (member and is_staff(member))
        )

        if not is_authorized:
            await interaction.response.send_message("❌ No tienes permisos para completar esta tarea (solo la persona asignada, el creador o el Staff).", ephemeral=True)
            return

        success = await complete_periodic_reminder(id)
        if success:
            embed = discord.Embed(
                title="✅ Tarea Completada",
                description=f"La tarea **#{id}** (*{rem['title']}*) fue marcada como completada por {interaction.user.mention}. Los recordatorios se han detenido.",
                color=COLOR_SUCCESS
            )
            embed.set_footer(text=f"Servidor: {interaction.guild.name}")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"⚠️ La tarea `#{id}` ya estaba completada o no se encontraba activa.", ephemeral=True)

    @app_commands.command(name="tarea-cancelar", description="Cancela un recordatorio periódico activo")
    @app_commands.describe(id="ID del recordatorio a cancelar")
    async def slash_cancel_task(self, interaction: discord.Interaction, id: int):
        rem = await get_periodic_reminder(id)
        if not rem or rem["guild_id"] != interaction.guild_id:
            await interaction.response.send_message(f"❌ No se encontró ninguna tarea con el ID `#{id}`.", ephemeral=True)
            return

        member = interaction.guild.get_member(interaction.user.id)
        is_authorized = (
            interaction.user.id == rem["creator_id"] or
            interaction.user.id == rem["assigned_user_id"] or
            (member and is_staff(member))
        )

        if not is_authorized:
            await interaction.response.send_message("❌ No tienes permisos para cancelar esta tarea.", ephemeral=True)
            return

        success = await cancel_periodic_reminder(id)
        if success:
            embed = discord.Embed(
                title="🛑 Recordatorio Cancelado",
                description=f"El recordatorio **#{id}** (*{rem['title']}*) ha sido cancelado por {interaction.user.mention}.",
                color=COLOR_DANGER
            )
            embed.set_footer(text=f"Servidor: {interaction.guild.name}")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"⚠️ La tarea `#{id}` ya no estaba activa.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(PeriodicRemindersCog(bot))
