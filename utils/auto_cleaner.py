"""
Módulo de Auto-Limpieza de Mensajes Antiguos (MiniJefe)
Permite enviar paneles interactivos, consultas y recordatorios borrando automáticamente
los mensajes obsoletos previos de la misma categoría para mantener limpios los canales.
"""

from typing import Optional
import discord
from database import get_last_panel_message, save_last_panel_message

async def delete_previous_panel_message(bot: discord.Client, guild_id: int, category: str):
    """Busca si existe un mensaje previo de esta categoría y lo elimina del canal."""
    try:
        last_rec = await get_last_panel_message(guild_id, category)
        if not last_rec:
            return

        guild = bot.get_guild(guild_id)
        if not guild:
            return

        channel = guild.get_channel(last_rec["channel_id"])
        if not channel:
            return

        try:
            old_msg = await channel.fetch_message(last_rec["message_id"])
            if old_msg:
                await old_msg.delete()
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass
    except Exception:
        pass

async def send_clean_panel_interaction(
    interaction: discord.Interaction,
    category: str,
    embed: discord.Embed,
    view: Optional[discord.ui.View] = None,
    content: Optional[str] = None
):
    """
    Envía una respuesta de panel por comando slash, eliminando previamente
    el mensaje anterior de la misma categoría en el servidor.
    """
    guild_id = interaction.guild_id
    if guild_id:
        await delete_previous_panel_message(interaction.client, guild_id, category)

    if view:
        await interaction.response.send_message(content=content, embed=embed, view=view)
    else:
        await interaction.response.send_message(content=content, embed=embed)

    if guild_id:
        try:
            msg = await interaction.original_response()
            if msg:
                await save_last_panel_message(guild_id, category, interaction.channel_id, msg.id)
        except Exception:
            pass

async def send_clean_channel_message(
    bot: discord.Client,
    channel: discord.TextChannel,
    category: str,
    embed: discord.Embed,
    view: Optional[discord.ui.View] = None,
    content: Optional[str] = None
) -> Optional[discord.Message]:
    """
    Envía un mensaje o recordatorio a un canal de texto eliminando previamente
    el mensaje anterior de la misma categoría.
    """
    guild_id = channel.guild.id
    await delete_previous_panel_message(bot, guild_id, category)

    if view:
        new_msg = await channel.send(content=content, embed=embed, view=view)
    else:
        new_msg = await channel.send(content=content, embed=embed)

    if new_msg:
        await save_last_panel_message(guild_id, category, channel.id, new_msg.id)

    return new_msg
