import discord
from discord.ext import commands
from discord import app_commands
import time
import re
import logging
from collections import defaultdict, deque
from typing import Dict, Deque, Optional

from database import get_guild_settings, update_guild_setting
from utils.embeds import COLOR_WARNING, COLOR_SUCCESS, COLOR_DANGER

logger = logging.getLogger("MiniJefe.Moderation")

class ModerationCog(commands.Cog, name="Moderación y Anti-Spam"):
    """Detección inteligente de spam con alertas amigables y personalizadas de MiniJefe."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Estructuras en memoria para seguimiento de actividad
        # user_id -> deque de timestamps (segundos)
        self.user_message_times: Dict[int, Deque[float]] = defaultdict(lambda: deque(maxlen=10))
        # user_id -> deque de (texto, timestamp)
        self.user_message_history: Dict[int, Deque[tuple[str, float]]] = defaultdict(lambda: deque(maxlen=5))
        # user_id -> último timestamp de advertencia emitida para evitar spamear advertencias
        self.last_warn_time: Dict[int, float] = {}
        # user_id -> conteo de infracciones recientes (expira con el tiempo)
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
        """Intercepta mensajes para moderación y órdenes de limpieza."""
        if not message.guild or message.author.bot:
            return

        # 1. Orden directa de borrar mensajes por chat: '@MiniJefe borra 5 mensajes'
        if self.bot.user and self.bot.user in message.mentions and self.is_exempt(message):
            text = message.content.lower()
            match = re.search(r"(?:borra|elimina|limpia|purge)\s+(\d+)", text)
            if match:
                count = min(int(match.group(1)), 100)
                if message.channel.permissions_for(message.guild.me).manage_messages:
                    try:
                        await message.delete()
                        deleted = await message.channel.purge(limit=count)
                        confirm = await message.channel.send(f"🧹 ¡A la orden jefe! Se eliminaron **{len(deleted)} mensajes**.")
                        await confirm.delete(delay=4)
                        return
                    except Exception as e:
                        logger.warning(f"Error al purgar mensajes por chat: {e}")
                else:
                    await message.reply("❌ Necesito el permiso de **Gestionar Mensajes** (`Manage Messages`) para poder borrar mensajes de otros usuarios.", mention_author=False)
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
                        f"¡Epa, {message.author.mention}! 🛑 Frena un toque los caballos 🐎\n"
                        f"El Mini Jefe no lee a la velocidad de la luz. Tómate un respiro de unos segundos para que todos puedan leer el chat con calma."
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
                        f"Hey {message.author.mention} 😉 ¡Ya te leímos a la primera!\n"
                        f"No hace falta hacer eco en el canal, te prometo que el mensaje llegó claro y fuerte."
                    ),
                    delete_trigger=True
                )
                return

        # --- C. CHECK MAYÚSCULAS EXCESIVAS (Gritos sostenidos: >25 caracteres y >75% caps) ---
        letters = [c for c in content if c.isalpha()]
        if len(letters) >= 25:
            upper_count = sum(1 for c in letters if c.isupper())
            if (upper_count / len(letters)) >= 0.75:
                await self.handle_violation(
                    message,
                    reason="caps",
                    friendly_text=(
                        f"¡Tranquilo vaquero {message.author.mention}! 📢\n"
                        f"Esas mayúsculas retumbaron hasta el servidor de al lado. Desactiva el Bloq Mayús y charlemos tranquilos 😎."
                    ),
                    delete_trigger=False
                )
                return

        # --- D. CHECK MENCIONES MASIVAS (>5 menciones en un solo mensaje) ---
        if len(message.mentions) >= 5:
            await self.handle_violation(
                message,
                reason="mass_mentions",
                friendly_text=(
                    f"⚠️ {message.author.mention}, ojo con las menciones masivas.\n"
                    f"Cuidado con etiquetar a media galaxia en un solo mensaje, cuidemos la paz de las notificaciones."
                ),
                delete_trigger=True
            )
            return

    async def handle_violation(self, message: discord.Message, reason: str, friendly_text: str, delete_trigger: bool):
        """Maneja la advertencia amigable y el control de escalado."""
        user_id = message.author.id

        # Intentar borrar el mensaje si corresponde y el bot tiene permisos
        if delete_trigger:
            try:
                if message.channel.permissions_for(message.guild.me).manage_messages:
                    await message.delete()
            except Exception as e:
                logger.warning(f"No se pudo borrar mensaje de spam: {e}")

        # Enviar advertencia amigable solo si no está en cooldown
        if await self.can_send_warning(user_id):
            self.warn_counts[user_id] += 1
            current_warns = self.warn_counts[user_id]

            embed = discord.Embed(
                title="🛡️ Alerta de Convivencia — MiniJefe",
                description=friendly_text,
                color=COLOR_WARNING
            )
            embed.set_footer(text=f"Aviso #{current_warns} • Mantengamos el servidor amigable y limpio.")

            try:
                # Enviarlo y auto-borrar la advertencia del bot tras 12 segundos para no generar más ruido
                sent_msg = await message.channel.send(content=f"👋 {message.author.mention}", embed=embed)
                await sent_msg.delete(delay=12)
            except Exception as e:
                logger.error(f"Error enviando alerta anti-spam: {e}")

            # Si ya van 3 advertencias acumuladas, notificar a los moderadores
            if current_warns >= 3:
                await self.notify_moderators(message, current_warns)

    async def notify_moderators(self, message: discord.Message, count: int):
        """Avisa a los moderadores si un usuario ignora reiteradas advertencias."""
        # Buscar un canal de moderación o auditoría
        mod_channel = discord.utils.get(message.guild.text_channels, name="mod-logs") or \
                      discord.utils.get(message.guild.text_channels, name="moderacion") or \
                      discord.utils.get(message.guild.text_channels, name="staff")

        if mod_channel and mod_channel.permissions_for(message.guild.me).send_messages:
            embed = discord.Embed(
                title="🚨 MiniJefe Reporte: Reincidencia de Spam",
                description=f"El usuario {message.author.mention} (`{message.author.id}`) ha recibido **{count} advertencias de spam** en {message.channel.mention}.",
                color=COLOR_DANGER
            )
            await mod_channel.send(embed=embed)

    @app_commands.command(name="config-antispam", description="Activa o desactiva el escudo anti-spam de MiniJefe")
    @app_commands.describe(activar="True para activar la protección de spam, False para desactivarla")
    @app_commands.default_permissions(administrator=True)
    async def toggle_antispam(self, interaction: discord.Interaction, activar: bool):
        val = 1 if activar else 0
        await update_guild_setting(interaction.guild_id, "spam_shield_enabled", val)
        status_text = "ACTIVADO 🛡️" if activar else "DESACTIVADO 💤"
        embed = discord.Embed(
            title="🛡️ Escudo Anti-Spam de MiniJefe",
            description=f"El sistema inteligente de detección y alertas de spam ha sido: **{status_text}**.",
            color=COLOR_SUCCESS if activar else COLOR_WARNING
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="limpiar", description="Elimina una cantidad de mensajes recientes de este canal")
    @app_commands.describe(
        cantidad="Número de mensajes a eliminar (entre 1 y 100)",
        usuario="Opcional: Solo borrar los mensajes de este usuario específico"
    )
    @app_commands.default_permissions(manage_messages=True)
    async def purge_messages(
        self,
        interaction: discord.Interaction,
        cantidad: app_commands.Range[int, 1, 100],
        usuario: Optional[discord.Member] = None
    ):
        if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
            await interaction.response.send_message("❌ No tengo el permiso de **Gestionar Mensajes** (`Manage Messages`) en este canal.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        def check(m):
            if usuario:
                return m.author.id == usuario.id
            return True

        try:
            deleted = await interaction.channel.purge(limit=cantidad, check=check)
            target_str = f" de {usuario.mention}" if usuario else ""
            await interaction.followup.send(f"🧹 Se eliminaron con éxito **{len(deleted)} mensajes**{target_str}.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error al eliminar mensajes: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))
