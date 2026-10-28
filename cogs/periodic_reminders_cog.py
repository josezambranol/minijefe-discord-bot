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

# IDs reconocidos con autoridad máxima de jefes
BOSS_IDS = {
    644124012871548958,  # jote (Dueño del bot)
    710931815271235645   # jordy (Fundador / Dueño del servidor)
}

def is_boss_or_staff(member: discord.Member) -> bool:
    """Verifica si un usuario es Jote, Jordy, o miembro del staff/admin."""
    if member.id in BOSS_IDS:
        return True
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
        # Solo el usuario asignado, el creador o un jefe pueden completarlo
        user = interaction.user
        member = interaction.guild.get_member(user.id) if interaction.guild else None
        is_authorized = (
            user.id == self.assigned_user_id or
            user.id == self.creator_id or
            (member and is_boss_or_staff(member))
        )

        if not is_authorized:
            await interaction.response.send_message("❌ Esta tarea está asignada a otro usuario. Solo ellos o los jefes pueden completarla.", ephemeral=True)
            return

        success = await complete_periodic_reminder(self.reminder_id)
        if success:
            button.disabled = True
            button.label = f"✅ Completada por {user.display_name}"
            # Desactivar botón cancelar también
            for child in self.children:
                child.disabled = True

            await interaction.response.edit_message(view=self)
            await interaction.followup.send(
                f"🎉 **¡Tarea completada!** Gran trabajo {user.mention}. El recordatorio periódico ha sido desactivado.",
                ephemeral=False
            )
        else:
            await interaction.response.send_message("⚠️ Esta tarea ya había sido completada o cancelada anteriormente.", ephemeral=True)

    @discord.ui.button(label="🛑 Cancelar Recordatorio", style=discord.ButtonStyle.danger, custom_id="btn_cancel_periodic")
    async def btn_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        member = interaction.guild.get_member(user.id) if interaction.guild else None
        is_authorized = (
            user.id == self.creator_id or
            (member and is_boss_or_staff(member))
        )

        if not is_authorized:
            await interaction.response.send_message("❌ Solo el creador de la tarea o un jefe/admin pueden cancelar este recordatorio.", ephemeral=True)
            return

        success = await cancel_periodic_reminder(self.reminder_id)
        if success:
            for child in self.children:
                child.disabled = True
            button.label = "🛑 Recordatorio Cancelado"
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(f"🛑 El recordatorio #{self.reminder_id} fue cancelado por {user.mention}.", ephemeral=False)
        else:
            await interaction.response.send_message("⚠️ Este recordatorio ya no está activo.", ephemeral=True)


class PeriodicRemindersCog(commands.Cog, name="Recordatorios Periódicos y Delegados"):
    """Permite a Jordy, Jote o Staff asignar tareas y recordar a usuarios cada X tiempo."""

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
                interval_mins = rem["interval_minutes"]
                last_sent_str = rem["last_reminded_at"]

                try:
                    last_dt = datetime.fromisoformat(last_sent_str)
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    last_dt = now_dt

                elapsed_seconds = (now_dt - last_dt).total_seconds()
                if elapsed_seconds >= (interval_mins * 60):
                    # Hora de enviar el recordatorio!
                    await self.dispatch_periodic_alert(rem)
        except Exception as e:
            logger.error(f"Error en reminder_check_loop: {e}", exc_info=True)

    @reminder_check_loop.before_loop
    async def before_reminder_loop(self):
        await self.bot.wait_until_ready()

    async def dispatch_periodic_alert(self, rem: dict):
        """Construye y envía el mensaje de recordatorio periódico."""
        rem_id = rem["id"]
        guild = self.bot.get_guild(rem["guild_id"])
        if not guild:
            return

        channel = guild.get_channel(rem["channel_id"])
        assigned_user = guild.get_member(rem["assigned_user_id"]) or await self.bot.fetch_user(rem["assigned_user_id"])
        creator = guild.get_member(rem["creator_id"]) or await self.bot.fetch_user(rem["creator_id"])

        interval_text = format_interval(rem["interval_minutes"])

        embed = discord.Embed(
            title="⏰ Recordatorio de Tarea Pendiente — MiniJefe",
            description=(
                f"👋 {assigned_user.mention}, tienes una tarea asignada que requiere tu atención:\n\n"
                f"📌 **{rem['title']}**\n\n"
                f"👤 **Asignado por:** {creator.mention}\n"
                f"🔄 **Frecuencia:** Cada **{interval_text}** hasta que la completes."
            ),
            color=COLOR_WARNING
        )
        embed.set_footer(text=f"ID de Tarea: #{rem_id} • Pulsa el botón cuando hayas terminado.")

        view = PeriodicReminderActionView(
            reminder_id=rem_id,
            assigned_user_id=rem["assigned_user_id"],
            creator_id=rem["creator_id"]
        )

        sent = False
        if channel and channel.permissions_for(guild.me).send_messages:
            try:
                await channel.send(
                    content=f"🔔 {assigned_user.mention} ¡Recordatorio de tarea pendiente!",
                    embed=embed,
                    view=view
                )
                sent = True
            except Exception as e:
                logger.warning(f"No se pudo enviar recordatorio en #{channel.name}: {e}")

        # Enviar DM si está habilitado
        if rem.get("send_dm") and assigned_user:
            try:
                dm_view = PeriodicReminderActionView(rem_id, rem["assigned_user_id"], rem["creator_id"])
                await assigned_user.send(embed=embed, view=dm_view)
            except Exception:
                pass

        if sent:
            now_iso = datetime.now(timezone.utc).isoformat()
            await update_periodic_reminder_sent(rem_id, now_iso)
            logger.info(f"Recordatorio #{rem_id} enviado a {assigned_user} cada {interval_text}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Escucha instrucciones en lenguaje natural dirigidas al bot por Jordy, Jote o Staff.
        Ej: '@MiniJefe recuérdale a @usuario subir el informe cada 2 horas'
        """
        if message.author.bot or not message.guild:
            return
        if not self.bot.user or self.bot.user not in message.mentions:
            return

        member = message.author
        if not is_boss_or_staff(member):
            return

        text = message.content.lower()

        # Chequear si es una orden de recordar o poner tarea
        keywords = ["recuerdale", "recuérdale", "recordar", "recuerda", "ponle una tarea", "asigna una tarea", "tarea para"]
        if not any(k in text for k in keywords):
            return

        # Buscar usuario mencionado que NO sea el bot
        target_members = [m for m in message.mentions if m.id != self.bot.user.id]
        if not target_members:
            # Si no mencionó a nadie, tal vez sea para sí mismo
            target_user = message.author
        else:
            target_user = target_members[0]

        # Extraer intervalo de tiempo: cada X horas / minutos
        # Ejemplos: "cada 2 horas", "cada 30 min", "cada 1h", "cada 45 minutos", "cada hora"
        interval_minutes = 120  # Por defecto 2 horas
        match = re.search(r"cada\s+(\d+)\s*(hora|horas|h|minuto|minutos|min|m)", text)
        if match:
            val = int(match.group(1))
            unit = match.group(2)
            if "h" in unit:
                interval_minutes = val * 60
            else:
                interval_minutes = max(val, 5)
        elif "cada hora" in text or "cada 1 hora" in text:
            interval_minutes = 60

        # Extraer el texto de la tarea
        clean_text = message.content
        for m in message.mentions:
            clean_text = clean_text.replace(f"<@{m.id}>", "").replace(f"<@!{m.id}>", "")
        for k in ["recuerdale a", "recuérdale a", "recordarle a", "ponle una tarea a", "tarea para", "que haga", "que"]:
            clean_text = re.sub(rf"(?i)\b{k}\b", "", clean_text)
        # Quitar la parte de 'cada X horas'
        clean_text = re.sub(r"(?i)cada\s+(\d+)?\s*(hora|horas|h|minuto|minutos|min|m)?", "", clean_text).strip()

        task_title = clean_text if clean_text else "Tarea pendiente asignada por el staff"

        rem_id = await add_periodic_reminder(
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            creator_id=message.author.id,
            assigned_user_id=target_user.id,
            title=task_title,
            interval_minutes=interval_minutes,
            send_dm=0
        )

        interval_display = format_interval(interval_minutes)
        embed = discord.Embed(
            title="🫡 ¡A la orden, Jefe! Recordatorio Registrado",
            description=(
                f"He registrado la tarea asignada por {message.author.mention}:\n\n"
                f"📌 **Tarea:** {task_title}\n"
                f"👤 **Asignada a:** {target_user.mention}\n"
                f"🔄 **Frecuencia:** Cada **{interval_display}**\n\n"
                f"*(Le estaré recordando periódicamente por este canal hasta que pulse 'Marcar como Listo').*"
            ),
            color=COLOR_SUCCESS
        )
        embed.set_footer(text=f"ID de Tarea: #{rem_id} • MiniJefe en acción")
        await message.reply(embed=embed, mention_author=False)

    @app_commands.command(name="recordar", description="Asigna una tarea o recordatorio periódico a un usuario con intervalo flexible")
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
        # Verificar permisos
        member = interaction.guild.get_member(interaction.user.id)
        if usuario.id != interaction.user.id and not is_boss_or_staff(member):
            await interaction.response.send_message("❌ Solo Jordy, Jote o miembros del Staff pueden asignar tareas a otros usuarios.", ephemeral=True)
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
            title="✅ Recordatorio Periódico Registrado",
            description=(
                f"📌 **Tarea:** {tarea.strip()}\n"
                f"👤 **Asignada a:** {usuario.mention}\n"
                f"👑 **Asignada por:** {interaction.user.mention}\n"
                f"⏰ **Frecuencia:** Cada **{interval_display}**{dm_note}"
            ),
            color=COLOR_SUCCESS
        )
        embed.set_footer(text=f"ID: #{rem_id} • El recordatorio se desactivará al marcar 'Listo'")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="recordatorios-activos", description="Lista todos los recordatorios periódicos activos en este servidor")
    async def list_active(self, interaction: discord.Interaction):
        """Muestra los recordatorios periódicos activos."""
        await interaction.response.defer()
        active = await get_active_periodic_reminders(interaction.guild_id)

        if not active:
            await interaction.followup.send("✨ No hay recordatorios periódicos pendientes en este servidor. ¡Todo al día!")
            return

        embed = discord.Embed(
            title="📋 Recordatorios Periódicos Activos",
            description=f"Total activos: **{len(active)}**",
            color=COLOR_INFO
        )

        for rem in active[:10]:
            target = f"<@{rem['assigned_user_id']}>"
            creator = f"<@{rem['creator_id']}>"
            freq = format_interval(rem["interval_minutes"])
            embed.add_field(
                name=f"#{rem['id']} • {rem['title'][:50]}",
                value=f"👤 Para: {target} | 👑 De: {creator} | ⏰ Cada {freq}\nCanal: <#{rem['channel_id']}>",
                inline=False
            )

        embed.set_footer(text="Para completar un recordatorio usa /tarea-lista [id]")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="tarea-lista", description="Marca un recordatorio periódico como completado")
    @app_commands.describe(id="ID del recordatorio a completar")
    async def slash_complete(self, interaction: discord.Interaction, id: int):
        rem = await get_periodic_reminder(id)
        if not rem or rem["guild_id"] != interaction.guild_id or rem["status"] != "active":
            await interaction.response.send_message("❌ No se encontró ningún recordatorio activo con ese ID.", ephemeral=True)
            return

        member = interaction.guild.get_member(interaction.user.id)
        is_authorized = (
            interaction.user.id == rem["assigned_user_id"] or
            interaction.user.id == rem["creator_id"] or
            is_boss_or_staff(member)
        )

        if not is_authorized:
            await interaction.response.send_message("❌ No tienes permiso para completar esta tarea.", ephemeral=True)
            return

        await complete_periodic_reminder(id)
        await interaction.response.send_message(f"✅ ¡La tarea **#{id} ({rem['title']})** ha sido marcada como lista y desactivada!", ephemeral=False)

    @app_commands.command(name="tarea-cancelar", description="Cancela un recordatorio periódico")
    @app_commands.describe(id="ID del recordatorio a cancelar")
    async def slash_cancel(self, interaction: discord.Interaction, id: int):
        rem = await get_periodic_reminder(id)
        if not rem or rem["guild_id"] != interaction.guild_id or rem["status"] != "active":
            await interaction.response.send_message("❌ No se encontró ningún recordatorio activo con ese ID.", ephemeral=True)
            return

        member = interaction.guild.get_member(interaction.user.id)
        if not (interaction.user.id == rem["creator_id"] or is_boss_or_staff(member)):
            await interaction.response.send_message("❌ Solo el creador o un jefe/admin pueden cancelar este recordatorio.", ephemeral=True)
            return

        await cancel_periodic_reminder(id)
        await interaction.response.send_message(f"🛑 El recordatorio **#{id} ({rem['title']})** fue cancelado.", ephemeral=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(PeriodicRemindersCog(bot))
