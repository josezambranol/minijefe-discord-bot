import discord
from discord.ext import commands
from discord import app_commands
import time
import re
import logging
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
from typing import Dict, Deque, Optional

from database import get_guild_settings, update_guild_setting
from utils.embeds import COLOR_WARNING, COLOR_SUCCESS, COLOR_DANGER, COLOR_INFO
from utils.reporting import log_to_reports

logger = logging.getLogger("MiniJefe.Moderation")

class ModerationCog(commands.Cog, name="Moderación y Anti-Spam"):
    """Detección inteligente de spam y herramientas avanzadas de limpieza de chat."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_message_times: Dict[int, Deque[float]] = defaultdict(lambda: deque(maxlen=10))
        self.user_message_history: Dict[int, Deque[tuple[str, float]]] = defaultdict(lambda: deque(maxlen=5))
        self.last_warn_time: Dict[int, float] = {}
        self.warn_counts: Dict[int, int] = defaultdict(int)

    def is_exempt(self, message: discord.Message) -> bool:
        """Determina si un mensaje o usuario está exento de chequeos de moderación."""
        if message.author.bot:
            return True
        if not isinstance(message.author, discord.Member):
            return True
        # Admins y moderadores exentos
        if message.author.guild_permissions.administrator or message.author.guild_permissions.manage_messages:
            return True
        return False

    async def can_send_warning(self, user_id: int) -> bool:
        """Evita que MiniJefe responda más de una vez cada 15 segundos al mismo usuario."""
        now = time.time()
        last = self.last_warn_time.get(user_id, 0)
        if now - last < 15:
            return False
        self.last_warn_time[user_id] = now
        return True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Intercepta mensajes para moderación y órdenes directas de limpieza de chat."""
        if not message.guild or message.author.bot:
            return

        # 1. Órdenes directas de moderación por chat (ej: '@MiniJefe limpia 20 mensajes de @usuario')
        if self.bot.user and self.bot.user in message.mentions and self.is_exempt(message):
            text = message.content.lower()
            keywords = ["borra", "elimina", "limpia", "purge", "clear"]
            if any(k in text for k in keywords):
                # Extraer cantidad (si no se especifica, por defecto 25)
                count_match = re.search(r"\b(\d+)\b", text)
                count = min(int(count_match.group(1)), 100) if count_match else 25

                # Extraer canal objetivo (si se mencionó #canal)
                target_channel = message.channel
                if message.channel_mentions:
                    target_channel = message.channel_mentions[0]

                # Extraer usuario objetivo (si se mencionó a alguien que no sea el bot)
                target_user = None
                other_mentions = [m for m in message.mentions if m.id != self.bot.user.id]
                if other_mentions:
                    target_user = other_mentions[0]

                # Extraer días (ej: "últimos 2 días" o "hace 1 dia")
                dias_match = re.search(r"(\d+)\s*(?:dia|dias|día|días)", text)
                dias = int(dias_match.group(1)) if dias_match else None

                # Detectar si es solo spam
                solo_spam = ("spam" in text or "enlaces" in text or "links" in text)

                # Validar permisos en el canal objetivo
                bot_perms = target_channel.permissions_for(message.guild.me)
                if not bot_perms.manage_messages:
                    await message.reply(f"❌ Se requiere el permiso de **Gestionar Mensajes** en {target_channel.mention}.", mention_author=False)
                    return

                now_utc = datetime.now(timezone.utc)
                threshold_dt = (now_utc - timedelta(days=dias)) if dias else None
                oldest_bulk = now_utc - timedelta(days=14)
                after_arg = threshold_dt if threshold_dt and threshold_dt > oldest_bulk else oldest_bulk

                def check(m: discord.Message) -> bool:
                    if target_user and m.author.id != target_user.id:
                        return False
                    if threshold_dt and m.created_at < threshold_dt:
                        return False
                    if solo_spam:
                        c = m.content.lower()
                        if "discord.gg/" in c or "http://" in c or "https://" in c or len(m.mentions) >= 3 or "@everyone" in c:
                            return True
                        return False
                    return True

                try:
                    if target_channel.id == message.channel.id:
                        await message.delete()

                    deleted = await target_channel.purge(
                        limit=count,
                        check=check,
                        after=after_arg,
                        bulk=True,
                        reason=f"Orden de limpieza por chat de {message.author.display_name}"
                    )

                    desc_parts = [f"**{len(deleted)} mensajes**"]
                    if target_user:
                        desc_parts.append(f"de {target_user.mention}")
                    if dias:
                        desc_parts.append(f"de los últimos {dias} día(s)")
                    if solo_spam:
                        desc_parts.append("(spam/enlaces)")
                    if target_channel.id != message.channel.id:
                        desc_parts.append(f"en {target_channel.mention}")

                    confirm = await message.channel.send(f"🧹 Se han eliminado {' '.join(desc_parts)} correctamente.")
                    await confirm.delete(delay=5)

                    # Registrar en #reportes
                    try:
                        filter_summary = f"Usuario: {target_user.mention if target_user else 'Todos'} | Días: {dias or '14 bulk'} | Spam: {solo_spam}"
                        await log_to_reports(
                            guild=message.guild,
                            title="Limpieza de Chat por Comando",
                            description=f"Se han eliminado **{len(deleted)} mensajes** en {target_channel.mention}.",
                            action_type="moderacion",
                            user=message.author,
                            fields=[
                                ("Canal afectado", target_channel.mention, True),
                                ("Mensajes eliminados", str(len(deleted)), True),
                                ("Filtros aplicados", filter_summary, False)
                            ]
                        )
                    except Exception as e:
                        logger.warning(f"Error registrando limpieza en #reportes: {e}")

                    return
                except Exception as e:
                    logger.warning(f"Error al purgar mensajes por chat: {e}")
                    await message.channel.send(f"❌ Ocurrió un error al eliminar los mensajes: {e}", delete_after=5)
                    return

        if self.is_exempt(message):
            return

        settings = await get_guild_settings(message.guild.id)
        if not settings.get("spam_shield_enabled", 1):
            return

        now = time.time()
        user_id = message.author.id
        content = message.content.strip()

        # 1. Registrar timestamp para flood check
        msg_times = self.user_message_times[user_id]
        msg_times.append(now)

        # 2. Registrar historial de contenido para repetición
        msg_history = self.user_message_history[user_id]
        if content:
            msg_history.append((content.lower(), now))

        # --- A. CHECK FLOOD (Ráfaga excesiva: >5 mensajes en menos de 4 segundos) ---
        if len(msg_times) >= 5:
            delta_time = msg_times[-1] - msg_times[-5]
            if delta_time < 4.0:
                await self.handle_violation(
                    message,
                    reason="flood",
                    friendly_text=(
                        f"Atención, {message.author.mention}: Por favor modera la frecuencia de mensajes para mantener el canal ordenado."
                    ),
                    delete_trigger=True
                )
                return

        # --- B. CHECK MENSAJES DUPLICADOS (3 veces el mismo texto en menos de 15 segundos) ---
        if len(msg_history) >= 3 and len(content) > 3:
            recent_same = [text for text, t in msg_history if text == content.lower() and (now - t) < 15]
            if len(recent_same) >= 3:
                await self.handle_violation(
                    message,
                    reason="duplicate",
                    friendly_text=(
                        f"Atención, {message.author.mention}: Por favor evita enviar mensajes duplicados repetidamente en el canal."
                    ),
                    delete_trigger=True
                )
                return

        # --- C. CHECK MAYÚSCULAS EXCESIVAS (>75% mayúsculas en mensajes largos) ---
        if len(content) > 25:
            upper_count = sum(1 for char in content if char.isupper())
            ratio = upper_count / len(content)
            if ratio > 0.75:
                await self.handle_violation(
                    message,
                    reason="caps",
                    friendly_text=(
                        f"Atención, {message.author.mention}: Por favor evita escribir en mayúsculas sostenidas."
                    ),
                    delete_trigger=False
                )
                return

        # --- D. CHECK MENCIONES MASIVAS NO AUTORIZADAS (>=5 menciones en un solo mensaje) ---
        if len(message.mentions) >= 5:
            await self.handle_violation(
                message,
                reason="mass_mention",
                friendly_text=(
                    f"Atención, {message.author.mention}: El uso masivo de menciones no está permitido en el servidor."
                ),
                delete_trigger=True
            )
            return

    async def handle_violation(self, message: discord.Message, reason: str, friendly_text: str, delete_trigger: bool):
        """Maneja la advertencia y el control de escalado ante infracciones de spam."""
        user_id = message.author.id

        if delete_trigger:
            try:
                if message.channel.permissions_for(message.guild.me).manage_messages:
                    await message.delete()
            except Exception as e:
                logger.warning(f"No se pudo borrar mensaje de spam: {e}")

        if await self.can_send_warning(user_id):
            self.warn_counts[user_id] += 1
            current_warns = self.warn_counts[user_id]

            embed = discord.Embed(
                title="🛡️ Notificación de Moderación",
                description=friendly_text,
                color=COLOR_WARNING
            )
            embed.set_footer(text=f"Aviso #{current_warns} • Mantengamos un entorno de desarrollo ordenado.")

            try:
                sent_msg = await message.channel.send(content=f"👋 {message.author.mention}", embed=embed)
                await sent_msg.delete(delay=10)
            except Exception as e:
                logger.error(f"Error enviando alerta anti-spam: {e}")

            if current_warns >= 3:
                await self.notify_moderators(message, current_warns)

    async def notify_moderators(self, message: discord.Message, count: int):
        """Avisa a los moderadores si un usuario ignora reiteradas advertencias de spam."""
        mod_channel = discord.utils.get(message.guild.text_channels, name="mod-logs") or \
                      discord.utils.get(message.guild.text_channels, name="moderacion") or \
                      discord.utils.get(message.guild.text_channels, name="staff")

        if mod_channel and mod_channel.permissions_for(message.guild.me).send_messages:
            embed = discord.Embed(
                title="🚨 Reporte de Moderación: Reincidencia de Spam",
                description=f"El usuario {message.author.mention} (`{message.author.id}`) ha acumulado **{count} advertencias de spam** en {message.channel.mention}.",
                color=COLOR_DANGER
            )
            embed.set_footer(text=f"Servidor: {message.guild.name}")
            await mod_channel.send(embed=embed)

        try:
            await log_to_reports(
                guild=message.guild,
                title="Alerta de Seguridad: Reincidencia de Spam",
                description=f"El usuario {message.author.mention} acumuló **{count} advertencias de spam** en {message.channel.mention}.",
                action_type="moderacion",
                user=message.author,
                fields=[
                    ("Canal", message.channel.mention, True),
                    ("Advertencias acumuladas", str(count), True)
                ]
            )
        except Exception as e:
            logger.warning(f"Error al enviar log de spam a #reportes: {e}")

    @app_commands.command(
        name="limpiar",
        description="Elimina mensajes con filtros avanzados (canal, usuario, fecha/días, spam o bots)"
    )
    @app_commands.describe(
        cantidad="Cantidad de mensajes a revisar/eliminar (entre 1 y 100, por defecto 50)",
        canal="Opcional: Canal donde se ejecutará la limpieza (por defecto el canal actual)",
        usuario="Opcional: Solo borrar los mensajes de este usuario específico",
        dias="Opcional: Solo borrar mensajes enviados en los últimos X días (1 a 14 días)",
        solo_spam="Opcional: Si es True, solo borra mensajes con enlaces sospechosos, invites o flood",
        solo_bots="Opcional: Si es True, solo borra mensajes generados por bots"
    )
    @app_commands.default_permissions(manage_messages=True)
    async def purge_messages(
        self,
        interaction: discord.Interaction,
        cantidad: app_commands.Range[int, 1, 100] = 50,
        canal: Optional[discord.TextChannel] = None,
        usuario: Optional[discord.User] = None,
        dias: Optional[app_commands.Range[int, 1, 14]] = None,
        solo_spam: Optional[bool] = False,
        solo_bots: Optional[bool] = False
    ):
        """Comando slash avanzado de purga de chat con filtros múltiples."""
        target_channel = canal or interaction.channel
        if not isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message("❌ El canal indicado debe ser un canal de texto.", ephemeral=True)
            return

        bot_perms = target_channel.permissions_for(interaction.guild.me)
        if not bot_perms.manage_messages:
            await interaction.response.send_message(
                f"❌ El bot no tiene el permiso de **Gestionar Mensajes** (`Manage Messages`) en {target_channel.mention}.",
                ephemeral=True
            )
            return
        if not bot_perms.read_message_history:
            await interaction.response.send_message(
                f"❌ El bot no tiene el permiso de **Leer el Historial de Mensajes** (`Read Message History`) en {target_channel.mention}.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        now_utc = datetime.now(timezone.utc)
        threshold_dt = (now_utc - timedelta(days=dias)) if dias is not None else None
        oldest_bulk = now_utc - timedelta(days=14)
        after_arg = threshold_dt if threshold_dt and threshold_dt > oldest_bulk else oldest_bulk

        def check(m: discord.Message) -> bool:
            # 1. Filtro por usuario
            if usuario and m.author.id != usuario.id:
                return False
            # 2. Filtro por bots
            if solo_bots and not m.author.bot:
                return False
            # 3. Filtro por fecha / días
            if threshold_dt and m.created_at < threshold_dt:
                return False
            # 4. Filtro por spam
            if solo_spam:
                c = m.content.lower()
                is_spam = False
                if "discord.gg/" in c or "discord.com/invite/" in c or "http://" in c or "https://" in c:
                    is_spam = True
                elif len(m.mentions) >= 3 or len(m.role_mentions) >= 2 or "@everyone" in c or "@here" in c:
                    is_spam = True
                elif len(m.content) > 15 and (sum(1 for char in m.content if char.isupper()) / len(m.content)) > 0.75:
                    is_spam = True
                if not is_spam:
                    return False
            return True

        try:
            deleted = await target_channel.purge(
                limit=cantidad,
                check=check,
                after=after_arg,
                bulk=True,
                reason=f"Limpieza ejecutada por {interaction.user.display_name} ({interaction.user.id})"
            )

            details = []
            if usuario:
                details.append(f"del usuario {usuario.mention}")
            if dias:
                details.append(f"de los últimos {dias} día(s)")
            if solo_spam:
                details.append("(solo spam/enlaces)")
            if solo_bots:
                details.append("(solo bots)")

            details_str = f" {', '.join(details)}" if details else ""
            in_channel_str = f" en {target_channel.mention}" if target_channel.id != interaction.channel_id else ""

            embed = discord.Embed(
                title="🧹 Limpieza de Chat Exitosa",
                description=(
                    f"Se han eliminado **{len(deleted)} mensajes**{details_str}{in_channel_str}.\n"
                    f"*(El historial ha quedado depurado correctamente).*"
                ),
                color=COLOR_SUCCESS
            )
            embed.set_footer(text=f"Servidor: {interaction.guild.name} • Moderación")
            await interaction.followup.send(embed=embed, ephemeral=True)

            # Registrar en #reportes
            try:
                filter_str = f"Usuario: {usuario.mention if usuario else 'Todos'} | Días: {dias or '14 bulk'} | Spam: {solo_spam} | Bots: {solo_bots}"
                await log_to_reports(
                    guild=interaction.guild,
                    title="Purga de Mensajes Ejecutada (/limpiar)",
                    description=f"Se han eliminado **{len(deleted)} mensajes** en {target_channel.mention}.",
                    action_type="moderacion",
                    user=interaction.user,
                    fields=[
                        ("Canal", target_channel.mention, True),
                        ("Cantidad eliminada", str(len(deleted)), True),
                        ("Filtros", filter_str, False)
                    ]
                )
            except Exception as e:
                logger.warning(f"Error al reportar /limpiar en #reportes: {e}")
        except Exception as e:
            logger.error(f"Error ejecutando /limpiar: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Ocurrió un error al eliminar los mensajes: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))
