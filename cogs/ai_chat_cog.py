import discord
from discord.ext import commands
from discord import app_commands
import logging
from collections import defaultdict, deque
from typing import Dict, Deque, Literal

from database import get_guild_settings, update_guild_setting
from utils.ai_service import ask_gemini
from utils.embeds import COLOR_INFO, COLOR_SUCCESS

logger = logging.getLogger("MiniJefe.AIChat")

class AIChatCog(commands.Cog, name="IA y Charla Viva"):
    """Permite que MiniJefe cobre vida, converse de forma natural y responda preguntas."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # channel_id -> deque de {"role": "user"|"model", "content": str}
        self.channel_conversations: Dict[int, Deque[dict]] = defaultdict(lambda: deque(maxlen=8))

    def clean_mentions(self, content: str) -> str:
        """Remueve las menciones del bot del texto para pasarlo limpio a la IA."""
        if not self.bot.user:
            return content
        clean = content.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "").strip()
        return clean

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Responde cuando alguien menciona a MiniJefe en el chat."""
        # Evitar responder a otros bots o a sí mismo
        if message.author.bot:
            return
        if not message.guild:
            return
        if not self.bot.user or self.bot.user not in message.mentions:
            return

        # Verificar si la IA está activa en este servidor
        settings = await get_guild_settings(message.guild.id)
        if not settings.get("ai_chat_enabled", 1):
            return

        clean_text = self.clean_mentions(message.content)
        if not clean_text:
            await message.reply(
                "¡Qué onda compa! 👋 Aquí está el Mini Jefe presente. ¿En qué te puedo colaborar o de qué charlamos hoy?",
                mention_author=False
            )
            return

        personality = settings.get("ai_personality", "amigable")
        history = list(self.channel_conversations[message.channel.id])

        # Mostrar que el bot está escribiendo mientras consulta la IA
        async with message.channel.typing():
            try:
                response = await ask_gemini(clean_text, personality=personality, chat_history=history)
            except Exception as e:
                logger.error(f"Error procesando charla con IA: {e}")
                response = "⚡ *El Mini Jefe se quedó recalculando la jugada... ¡Pregúntame de nuevo en un segundo!*"

        # Guardar en el historial de conversación del canal
        self.channel_conversations[message.channel.id].append({"role": "user", "content": clean_text})
        self.channel_conversations[message.channel.id].append({"role": "model", "content": response})

        # Si la respuesta excede 2000 caracteres (límite de Discord), dividirla
        if len(response) <= 2000:
            await message.reply(response, mention_author=False)
        else:
            chunks = [response[i:i+1950] for i in range(0, len(response), 1950)]
            for chunk in chunks:
                await message.channel.send(chunk)

    @app_commands.command(name="hablar", description="Charla directamente con MiniJefe o hazle cualquier pregunta con IA")
    @app_commands.describe(mensaje="Lo que le quieras preguntar o comentar a MiniJefe")
    async def slash_ask(self, interaction: discord.Interaction, mensaje: str):
        """Comando slash para interactuar con la IA de MiniJefe."""
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
        except Exception:
            pass

        settings = await get_guild_settings(interaction.guild_id)
        personality = settings.get("ai_personality", "amigable")
        history = list(self.channel_conversations[interaction.channel_id])

        response = await ask_gemini(mensaje, personality=personality, chat_history=history)

        self.channel_conversations[interaction.channel_id].append({"role": "user", "content": mensaje})
        self.channel_conversations[interaction.channel_id].append({"role": "model", "content": response})

        embed = discord.Embed(
            description=response,
            color=0x5865F2
        )
        embed.set_author(name=f"MiniJefe • {personality.capitalize()}", icon_url=self.bot.user.display_avatar.url if self.bot.user else None)
        embed.set_footer(text=f"Preguntado por {interaction.user.display_name}")

        await interaction.followup.send(content=f"💬 **\"{mensaje}\"**", embed=embed)

    @app_commands.command(name="personalidad", description="Cambia el estilo de personalidad y tono de MiniJefe")
    @app_commands.describe(estilo="Elige la vibra que tendrá MiniJefe al conversar")
    @app_commands.default_permissions(administrator=True)
    async def set_personality(
        self,
        interaction: discord.Interaction,
        estilo: Literal["amigable", "jefe_motivador", "programador", "tranquilo"]
    ):
        await update_guild_setting(interaction.guild_id, "ai_personality", estilo)

        nombres = {
            "amigable": "😎 Amigable & Bromista (Relajado, con chispa y compa del servidor)",
            "jefe_motivador": "🔥 Jefe Motivador (Energía alta, liderazgo y superación)",
            "programador": "💻 Tech Lead / Programador Senior (Consejos de código, técnico y limpio)",
            "tranquilo": "🌿 Compa Zen (Calmado, empático y buena vibra)"
        }

        embed = discord.Embed(
            title="🎭 Personalidad de MiniJefe Actualizada",
            description=f"El bot ahora adoptará el estilo: **{nombres.get(estilo, estilo)}**.",
            color=COLOR_SUCCESS
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="olvidar-charla", description="Limpia la memoria del hilo de conversación en este canal")
    async def clear_memory(self, interaction: discord.Interaction):
        if interaction.channel_id in self.channel_conversations:
            self.channel_conversations[interaction.channel_id].clear()
        await interaction.response.send_message("🧹 Memoria de conversación reiniciada para este canal. ¡Empecemos de cero!", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AIChatCog(bot))
