import discord
from discord.ext import commands, tasks
from datetime import datetime
import pytz
import logging
from typing import Tuple

from database import (
    get_all_active_tasks, get_guild_settings, update_last_reminded,
    mark_task_overdue, has_notification_been_sent, record_notification_sent,
    mark_overdue_alert_sent
)
from utils.embeds import daily_reminder_embed, overdue_alert_embed
from utils.auto_cleaner import send_clean_channel_message
from views.task_views import TaskActionView

logger = logging.getLogger("TaskBot.Reminders")

class RemindersLoopCog(commands.Cog, name="Recordatorios Automáticos"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminder_checker.start()

    def cog_unload(self):
        self.reminder_checker.cancel()

    @tasks.loop(seconds=60)
    async def reminder_checker(self):
        """Ciclo en segundo plano que corre cada 60 segundos."""
        try:
            await self.check_and_send_all_reminders(force=False)
            await self.check_and_send_class_reminders()
        except Exception as e:
            logger.error(f"Error en el ciclo de recordatorios: {e}", exc_info=True)

    @reminder_checker.before_loop
    async def before_reminder_checker(self):
        await self.bot.wait_until_ready()

    async def check_and_send_class_reminders(self):
        """Revisa si en 30 minutos empieza alguna clase y envía un aviso único (Anti-Spam)."""
        from utils.schedule_data import SCHEDULE_DATA, get_now, get_day_key_from_datetime, parse_time_str
        from utils.embeds import class_reminder_alert_embed
        from utils.team_data import get_team_mentions

        for guild in self.bot.guilds:
            settings = await get_guild_settings(guild.id)
            tz_name = settings.get("timezone", "America/Bogota")
            now = get_now(tz_name)
            day_key = get_day_key_from_datetime(now)

            if not day_key or day_key not in SCHEDULE_DATA:
                continue

            day_data = SCHEDULE_DATA[day_key]
            today_str = now.strftime("%Y-%m-%d")
            now_mins = now.hour * 60 + now.minute

            for cls in day_data["classes"]:
                t_start = parse_time_str(cls["start"])
                cls_start_mins = t_start.hour * 60 + t_start.minute
                diff = cls_start_mins - now_mins

                reminder_key = f"class:{today_str}:{day_key}:{cls['start']}:{guild.id}"

                # Enviar recordatorio cuando falten entre 25 y 30 minutos (Solo si no se ha enviado hoy)
                if 0 <= diff <= 30:
                    already_sent = await has_notification_been_sent(reminder_key)
                    if already_sent:
                        continue

                    # Registrar inmediatamente para evitar condiciones de carrera
                    await record_notification_sent(reminder_key)

                    channel_id = settings.get("reminder_channel_id")
                    channel = guild.get_channel(channel_id) if channel_id else guild.system_channel
                    if not channel:
                        for ch in guild.text_channels:
                            if ch.permissions_for(guild.me).send_messages:
                                channel = ch
                                break

                    if channel:
                        try:
                            embed = class_reminder_alert_embed(cls, minutes_before=diff if diff > 0 else 30, tz_name=tz_name)
                            team_mentions = get_team_mentions(guild)
                            msg_content = f"🔔 {team_mentions} ¡En **{diff if diff > 0 else 'unos'} minutos** inicia la clase de **{cls['subject']}**!"
                            await send_clean_channel_message(
                                bot=self.bot,
                                channel=channel,
                                category="class_reminder_alert",
                                embed=embed,
                                content=msg_content
                            )
                            logger.info(f"Aviso de clase enviado: {cls['subject']} en {guild.name}")
                        except Exception as e:
                            logger.warning(f"No se pudo enviar aviso de clase en {guild.name}: {e}")

    async def check_and_send_all_reminders(self, force: bool = False) -> Tuple[int, int]:
        """
        Verifica tareas que deben recibir recordatorio hoy y tareas que acaban de vencer.
        Retorna (recordatorios_enviados, tareas_vencidas_detectadas).
        """
        reminded_count = 0
        overdue_count = 0

        # ==========================================
        # 1. VERIFICAR TAREAS VENCIDAS (OVERDUE)
        # ==========================================
        all_pending_tasks = await get_all_active_tasks()
        
        for task in all_pending_tasks:
            guild_id = task["guild_id"]
            settings = await get_guild_settings(guild_id)
            tz_name = settings.get("timezone", "America/Bogota")
            
            try:
                tz = pytz.timezone(tz_name)
            except Exception:
                tz = pytz.timezone("America/Bogota")

            now_local = datetime.now(tz)
            today_str = now_local.strftime("%Y-%m-%d")
            current_time_str = now_local.strftime("%H:%M")

            due_dt = datetime.fromisoformat(task["due_date"])
            if due_dt.tzinfo is None:
                due_dt = tz.localize(due_dt)
            else:
                due_dt = due_dt.astimezone(tz)

            # Comprobar si ya expiró el plazo
            if now_local >= due_dt:
                await mark_task_overdue(task["id"])
                overdue_count += 1
                task["status"] = "overdue"
                
                # Enviar alerta de vencimiento ÚNICAMENTE si no se ha enviado antes (Anti-Spam)
                if not task.get("overdue_alert_sent"):
                    await mark_overdue_alert_sent(task["id"])
                    await self._send_task_notification(
                        task=task,
                        settings=settings,
                        embed=overdue_alert_embed(task, tz_name),
                        notification_type="overdue"
                    )
                continue

            # ==========================================
            # 2. VERIFICAR RECORDATORIO DIARIO
            # ==========================================
            task_rem_time = task.get("reminder_time", "09:00")
            has_reminded_today = (task.get("last_reminded_date") == today_str)

            should_remind = force or (
                not has_reminded_today and current_time_str >= task_rem_time
            )

            if should_remind:
                await update_last_reminded(task["id"], today_str)
                reminded_count += 1
                
                await self._send_task_notification(
                    task=task,
                    settings=settings,
                    embed=daily_reminder_embed(task, tz_name),
                    notification_type="daily_reminder"
                )

        return reminded_count, overdue_count


    async def _send_task_notification(
        self,
        task: dict,
        settings: dict,
        embed: discord.Embed,
        notification_type: str
    ):
        """Envía la notificación al canal configurado del servidor y por DM si corresponde."""
        guild = self.bot.get_guild(task["guild_id"])
        if not guild:
            return

        # 1. Determinar el canal de envío
        channel = None
        if settings.get("reminder_channel_id"):
            channel = guild.get_channel(settings["reminder_channel_id"])
        
        # Si no hay canal de recordatorios configurado, usar el canal donde se creó la tarea
        if not channel:
            channel = guild.get_channel(task["channel_id"])

        view = TaskActionView(
            task_id=task["id"],
            guild_id=task["guild_id"],
            assigned_user_id=task["assigned_user_id"]
        )

        # 2. Enviar al canal del servidor mencionando al equipo con auto-limpieza
        if channel and channel.permissions_for(guild.me).send_messages:
            try:
                team_mentions = get_team_mentions(guild)
                mention_text = f"🔔 {team_mentions} Recordatorio de entrega pendiente:"
                if notification_type == "overdue":
                    mention_text = f"🚨 {team_mentions} **¡ALERTA DE ENTREGA VENCIDA DEL EQUIPO!**"
                
                await send_clean_channel_message(
                    bot=self.bot,
                    channel=channel,
                    category=f"task_{task['id']}_{notification_type}",
                    embed=embed,
                    view=view,
                    content=mention_text
                )
            except Exception as e:
                logger.warning(f"No se pudo enviar mensaje al canal {channel.id}: {e}")

        # 3. Enviar por Mensaje Directo (DM) si está activado
        if settings.get("send_dm", 1):
            try:
                user = await self.bot.fetch_user(task["assigned_user_id"])
                if user and not user.bot:
                    dm_channel = await user.create_dm()
                    dm_view = TaskActionView(
                        task_id=task["id"],
                        guild_id=task["guild_id"],
                        assigned_user_id=task["assigned_user_id"]
                    )
                    await dm_channel.send(embed=embed, view=dm_view)
            except discord.Forbidden:
                # El usuario tiene los DMs cerrados para miembros del servidor
                pass
            except Exception as e:
                logger.debug(f"No se pudo enviar DM al usuario {task['assigned_user_id']}: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(RemindersLoopCog(bot))
