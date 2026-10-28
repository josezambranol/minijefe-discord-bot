import discord
from discord.ext import commands
from discord import app_commands
import random
import time
import re
import logging
from collections import defaultdict, deque
from typing import Dict, Deque, Optional

from database import get_guild_settings, update_guild_setting, add_periodic_reminder
from utils.ai_service import ask_gemini_smart, ask_gemini
from utils.embeds import COLOR_INFO, COLOR_SUCCESS, COLOR_WARNING
from utils.reporting import log_to_reports
from cogs.periodic_reminders_cog import PeriodicReminderActionView, format_interval

logger = logging.getLogger("MiniJefe.AIChat")

class AIChatCog(commands.Cog, name="IA y Gestión Inteligente"):
    """Permite interactuar con MiniJefe, resolver dudas y agendar tareas automáticamente con IA."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_conversations: Dict[int, Deque[dict]] = defaultdict(lambda: deque(maxlen=8))
        self.user_last_ai_time: Dict[int, float] = {}

    def clean_mentions(self, content: str) -> str:
        """Remueve menciones al bot del texto para pasarlo limpio a la IA."""
        if not self.bot.user:
            return content
        clean = content.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "").strip()
        return clean

    async def execute_task_registration(
        self,
        message: discord.Message,
        task_title: str,
        interval_minutes: int,
        target_username_hint: Optional[str] = None
    ) -> bool:
        """Registra efectivamente la tarea en la base de datos y envía el panel interactivo."""
        # 1. Determinar el usuario asignado
        target_user = message.author
        target_members = [m for m in message.mentions if m.id != self.bot.user.id]
        if target_members:
            target_user = target_members[0]
        elif target_username_hint and target_username_hint.lower() not in ["autor", "yo", "mismo", "mi"]:
            # Buscar coincidencia en el servidor
            clean_hint = target_username_hint.lower().replace("@", "").strip()
            match = discord.utils.find(lambda m: clean_hint in m.display_name.lower() or clean_hint in m.name.lower(), message.guild.members)
            if match:
                target_user = match

        # 2. Guardar en SQLite
        clean_title = task_title.strip() if task_title else "Tarea asignada por chat"
        interval_mins = max(interval_minutes or 120, 5)

        try:
            rem_id = await add_periodic_reminder(
                guild_id=message.guild.id,
                channel_id=message.channel.id,
                creator_id=message.author.id,
                assigned_user_id=target_user.id,
                title=clean_title,
                interval_minutes=interval_mins,
                send_dm=0
            )

            interval_display = format_interval(interval_mins)
            embed = discord.Embed(
                title="📋 Tarea Registrada en el Sistema",
                description=(
                    f"He registrado la siguiente tarea solicitada por {message.author.mention}:\n\n"
                    f"📌 **Tarea:** {clean_title}\n"
                    f"👤 **Asignada a:** {target_user.mention}\n"
                    f"🔄 **Frecuencia:** Cada **{interval_display}**\n\n"
                    f"*(Se enviarán recordatorios periódicos por este canal hasta que sea marcada como completada).*"
                ),
                color=COLOR_SUCCESS
            )
            embed.set_footer(text=f"ID de Tarea: #{rem_id} • Servidor: {message.guild.name}")
            view = PeriodicReminderActionView(reminder_id=rem_id, assigned_user_id=target_user.id, creator_id=message.author.id)

            await message.reply(embed=embed, view=view, mention_author=False)
            logger.info(f"Tarea #{rem_id} registrada vía IA para {target_user.display_name} en {message.guild.name}")

            # Registrar en #reportes
            try:
                await log_to_reports(
                    guild=message.guild,
                    title="Tarea Registrada vía Asistente IA",
                    description=f"Se registró la tarea **#{rem_id}** solicitada por {message.author.mention}.",
                    action_type="recordatorio",
                    user=message.author,
                    fields=[
                        ("Descripción", clean_title, False),
                        ("Asignada a", target_user.mention, True),
                        ("Frecuencia", interval_display, True)
                    ]
                )
            except Exception as e:
                logger.warning(f"Error al reportar tarea de IA en #reportes: {e}")

            return True
        except Exception as e:
            logger.error(f"Error registrando tarea vía IA: {e}", exc_info=True)
            await message.reply("❌ Ocurrió un error al registrar la tarea en la base de datos.", mention_author=False)
            return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Atiende menciones al bot y ejecuta acciones de IA o registro de tareas."""
        if message.author.bot or not message.guild:
            return
        if not self.bot.user or self.bot.user not in message.mentions:
            return

        settings = await get_guild_settings(message.guild.id)
        if not settings.get("ai_chat_enabled", 1):
            return

        clean_text = self.clean_mentions(message.content)
        author_name = message.author.display_name

        # Si solo lo mencionan sin texto
        if not clean_text:
            professional_calls = [
                f"Hola {author_name}, estoy a tu disposición en **{message.guild.name}**. ¿En qué puedo colaborarte?",
                f"Saludos {author_name}. Indícame qué consulta técnica tienes o qué tarea deseas registrar.",
                f"Hola {author_name}. ¿En qué te puedo apoyar el día de hoy?",
                f"Presente en **{message.guild.name}**. ¿Qué actividad o duda tienes?"
            ]
            await message.reply(random.choice(professional_calls), mention_author=False)
            return

        # Cooldown anti-abuso de 3 segundos por usuario para proteger la cuota de la API
        now = time.time()
        is_admin = message.author.guild_permissions.administrator
        if not is_admin:
            last_call = self.user_last_ai_time.get(message.author.id, 0)
            if now - last_call < 3.0:
                await message.reply(
                    f"⏳ Por favor espera un momento, {author_name}. Procesa las consultas con un intervalo de 3 segundos.",
                    mention_author=False
                )
                return
            self.user_last_ai_time[message.author.id] = now

        personality = settings.get("ai_personality", "profesional")
        history = list(self.channel_conversations[message.channel.id])

        # Consultar Gemini con herramientas (Function Calling)
        async with message.channel.typing():
            text_response, tool_call = await ask_gemini_smart(
                prompt=f"[{author_name}]: {clean_text}",
                personality=personality,
                chat_history=history,
                guild_name=message.guild.name,
                enable_tools=True
            )

        # 1. Si la IA detectó la intención de registrar una tarea
        if tool_call and tool_call.get("name") == "crear_recordatorio":
            args = tool_call.get("args", {})
            tarea_desc = args.get("tarea", clean_text)
            intervalo = args.get("intervalo_minutos", 120)
            usuario_hint = args.get("usuario")
            await self.execute_task_registration(message, tarea_desc, intervalo, usuario_hint)
            return

        # 2. Si no hubo llamada a herramienta, verificar si coincide con regex local de tareas (fallback seguro)
        text_lower = clean_text.lower()
        task_intent_keywords = ["recuérdale a", "recuerdale a", "ponle una tarea", "asigna una tarea", "recuérdame", "recuerdame", "anota una tarea", "registra una tarea", "pon una tarea"]
        if any(k in text_lower for k in task_intent_keywords):
            # Parsear minutos
            mins = 120
            match = re.search(r"cada\s+(\d+)\s*(hora|horas|h|minuto|minutos|min|m)", text_lower)
            if match:
                val = int(match.group(1))
                unit = match.group(2)
                mins = val * 60 if "h" in unit else max(val, 5)

            # Limpiar texto para extraer título
            clean_title = clean_text
            for k in task_intent_keywords:
                clean_title = re.sub(rf"(?i)\b{k}\b", "", clean_title)
            clean_title = re.sub(r"(?i)cada\s+(\d+)?\s*(hora|horas|h|minuto|minutos|min|m)?", "", clean_title).strip()

            await self.execute_task_registration(message, clean_title, mins)
            return

        # 3. Respuesta conversacional estándar
        if text_response:
            self.channel_conversations[message.channel.id].append({"role": "user", "content": clean_text})
            self.channel_conversations[message.channel.id].append({"role": "model", "content": text_response})

            if len(text_response) <= 2000:
                await message.reply(text_response, mention_author=False)
            else:
                chunks = [text_response[i:i+1950] for i in range(0, len(text_response), 1950)]
                for chunk in chunks:
                    await message.channel.send(chunk)

    @app_commands.command(name="hablar", description="Consulta técnica o charla profesional con MiniJefe vía IA")
    @app_commands.describe(mensaje="Tu consulta técnica o mensaje para MiniJefe")
    @app_commands.checks.cooldown(1, 3.0)
    async def slash_ask(self, interaction: discord.Interaction, mensaje: str):
        """Comando slash para interactuar con la IA de MiniJefe."""
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
        except Exception:
            pass

        settings = await get_guild_settings(interaction.guild_id)
        personality = settings.get("ai_personality", "profesional")
        history = list(self.channel_conversations[interaction.channel_id])

        text_response, tool_call = await ask_gemini_smart(
            prompt=mensaje,
            personality=personality,
            chat_history=history,
            guild_name=interaction.guild.name if interaction.guild else "el servidor",
            enable_tools=False
        )

        final_text = text_response or "No se pudo obtener respuesta del servicio de IA."

        self.channel_conversations[interaction.channel_id].append({"role": "user", "content": mensaje})
        self.channel_conversations[interaction.channel_id].append({"role": "model", "content": final_text})

        embed = discord.Embed(
            description=final_text,
            color=0x5865F2
        )
        embed.set_author(name="MiniJefe • Asistente de la Comunidad", icon_url=self.bot.user.display_avatar.url if self.bot.user else None)
        embed.set_footer(text=f"Consulta de {interaction.user.display_name}")

        await interaction.followup.send(content=f"💬 **\"{mensaje}\"**", embed=embed)

    @app_commands.command(name="personalidad", description="Configura el tono de respuesta de MiniJefe")
    @app_commands.describe(estilo="Selecciona el estilo de comunicación")
    @app_commands.default_permissions(administrator=True)
    async def set_personality(
        self,
        interaction: discord.Interaction,
        estilo: str
    ):
        clean_style = estilo.strip().lower()
        if clean_style not in ["profesional", "amigable", "programador", "tranquilo"]:
            await interaction.response.send_message(
                "❌ Estilo no válido. Opciones: `profesional`, `amigable`, `programador`, `tranquilo`.",
                ephemeral=True
            )
            return

        await update_guild_setting(interaction.guild_id, "ai_personality", clean_style)
        embed = discord.Embed(
            title="🎭 Tono de Comunicación Actualizado",
            description=f"El estilo de respuesta de MiniJefe ahora es: **`{clean_style.capitalize()}`**.",
            color=COLOR_SUCCESS
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="olvidar-charla", description="Reinicia el historial de memoria en este canal")
    async def clear_history(self, interaction: discord.Interaction):
        self.channel_conversations[interaction.channel_id].clear()
        embed = discord.Embed(
            title="🧠 Memoria Reiniciada",
            description="He limpiado el contexto previo de conversación en este canal.",
            color=COLOR_INFO
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AIChatCog(bot))
