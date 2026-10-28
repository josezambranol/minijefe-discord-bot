import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import unicodedata
import re
from datetime import datetime, timezone
import pytz
from typing import Optional

from database import (
    get_guild_settings,
    update_guild_setting,
    has_notification_been_sent,
    record_notification_sent
)
from utils.ai_service import generate_welcome_quote
from utils.image_generator import generate_welcome_card
from utils.embeds import COLOR_SUCCESS, COLOR_PRIMARY, create_anniversary_embed
from utils.reporting import log_to_reports

logger = logging.getLogger("MiniJefe.Welcome")

def normalize_channel_name(name: str) -> str:
    """Normaliza el nombre de un canal removiendo emojis, tildes y caracteres especiales."""
    n = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8').lower()
    return re.sub(r'[^a-z0-9]', '', n)

class WelcomeCog(commands.Cog, name="Bienvenidas"):
    """Gestión de bienvenida para nuevos miembros con tarjetas gráficas de programación e IA."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.anniversary_check_loop.start()

    def cog_unload(self):
        self.anniversary_check_loop.cancel()

    async def get_announcements_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Localiza el canal de anuncios oficial del servidor."""
        writable_channels = [
            ch for ch in guild.text_channels
            if ch.permissions_for(guild.me).send_messages
        ]
        for ch in writable_channels:
            clean = normalize_channel_name(ch.name)
            if "anuncio" in clean or "announc" in clean:
                return ch
        # Fallback al canal de bienvenida si no hay canal específico de anuncios
        return await self.get_welcome_channel(guild)

    async def check_guild_anniversaries(self, guild: discord.Guild):
        """Detecta miembros que cumplen aniversario de permanencia en el servidor y publica la conmemoración en #anuncios."""
        try:
            settings = await get_guild_settings(guild.id)
            tz_name = settings.get("timezone", "America/Bogota")
            try:
                tz = pytz.timezone(tz_name)
            except Exception:
                tz = pytz.timezone("America/Bogota")

            now = datetime.now(tz)
            # Solo enviar a partir de las 8:00 AM para respetar horas de descanso
            if now.hour < 8:
                return

            announcements_ch = await self.get_announcements_channel(guild)
            if not announcements_ch:
                return

            for member in list(guild.members):
                if member.bot or not member.joined_at:
                    continue

                joined_local = member.joined_at.astimezone(tz)
                if joined_local.month == now.month and joined_local.day == now.day:
                    years = now.year - joined_local.year
                    if years >= 1:
                        notif_key = f"member_anniversary_{guild.id}_{member.id}_{now.year}"
                        if await has_notification_been_sent(notif_key):
                            continue

                        embed = create_anniversary_embed(member, years, joined_local)
                        plural = "año" if years == 1 else "años"
                        content = f"Felicidades {member.mention} por cumplir hoy **{years} {plural}** siendo parte de la familia de **{guild.name}**."

                        try:
                            await announcements_ch.send(content=content, embed=embed)
                            await record_notification_sent(notif_key)
                            logger.info(f"Aniversario de {years} año(s) conmemorado para {member.display_name} en #{announcements_ch.name}")

                            await log_to_reports(
                                guild=guild,
                                title="Aniversario de Miembro Conmemorado",
                                description=f"Se publicó el reconocimiento por **{years} {plural}** de {member.mention} en {announcements_ch.mention}.",
                                action_type="aniversario",
                                user=member,
                                fields=[
                                    ("Miembro", f"{member.display_name} (`{member.id}`)", True),
                                    ("Trayectoria", f"{years} {plural}", True),
                                    ("Canal", announcements_ch.mention, True)
                                ]
                            )
                        except Exception as e:
                            logger.warning(f"Error al enviar felicitación de aniversario para {member.display_name}: {e}")
        except Exception as e:
            logger.error(f"Error comprobando aniversarios en {guild.name}: {e}")

    @tasks.loop(minutes=30.0)
    async def anniversary_check_loop(self):
        """Ciclo periódico para detectar y publicar aniversarios de miembros."""
        for guild in self.bot.guilds:
            await self.check_guild_anniversaries(guild)

    @anniversary_check_loop.before_loop
    async def before_anniversary_loop(self):
        await self.bot.wait_until_ready()

    async def get_welcome_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """
        Encuentra inteligentemente el mejor canal para enviar la bienvenida:
        1. Canal configurado manualmente vía /config-bienvenida.
        2. Canal del sistema si el bot tiene permisos de escritura.
        3. Canales cuyo nombre contenga 'bienvenida', 'welcome', 'llegada', 'inicio', 'general', 'chat', 'comunidad'.
        4. Cualquier canal de texto accesible por los miembros donde el bot pueda escribir.
        """
        # 1. Canal configurado explícitamente en base de datos
        try:
            settings = await get_guild_settings(guild.id)
            channel_id = settings.get("welcome_channel_id")
            if channel_id:
                ch = guild.get_channel(channel_id)
                if ch and isinstance(ch, discord.TextChannel) and ch.permissions_for(guild.me).send_messages:
                    return ch
        except Exception as e:
            logger.warning(f"Error al consultar configuración de bienvenida: {e}")

        # 2. Canal del sistema de Discord
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            return guild.system_channel

        # Canales donde el bot tiene permiso de enviar mensajes y embeber enlaces
        writable_channels = [
            ch for ch in guild.text_channels
            if ch.permissions_for(guild.me).send_messages
        ]

        if not writable_channels:
            return None

        # 3. Búsqueda por palabras clave con prioridad
        priority_groups = [
            ["bienvenid", "welcome", "llegad", "hola"],
            ["general", "chat", "principal", "comunidad", "charla", "conversacion"],
            ["inicio", "presentacion", "presentate", "lobby", "start"]
        ]

        for keywords in priority_groups:
            for ch in writable_channels:
                clean = normalize_channel_name(ch.name)
                if any(kw in clean for kw in keywords):
                    return ch

        # 4. Fallback al primer canal donde el bot pueda escribir
        return writable_channels[0]

    def create_welcome_embed(self, member: discord.Member, quote: str) -> discord.Embed:
        """Crea el embed limpio y profesional para la bienvenida."""
        guild = member.guild

        def get_ch_ref(kw_list, fallback_str):
            for ch in guild.text_channels:
                clean = normalize_channel_name(ch.name)
                if any(k in clean for k in kw_list):
                    return ch.mention
            return f"**#{fallback_str}**"

        reglas_ref = get_ch_ref(["regla", "rules"], "reglas")
        roles_ref = get_ch_ref(["role", "rol"], "roles")
        pres_ref = get_ch_ref(["presentaci"], "presentaciones")
        proj_ref = get_ch_ref(["proyecto"], "proyectos")

        embed = discord.Embed(
            title=f"Bienvenido/a a {guild.name}",
            description=(
                f"Damos la bienvenida a {member.mention} a la comunidad de desarrollo.\n\n"
                f"> *{quote}*\n\n"
                f"**Primeros pasos recomendados:**\n"
                f"- Revisa la normativa del servidor en {reglas_ref}.\n"
                f"- Configura tus lenguajes y áreas técnicas en {roles_ref}.\n"
                f"- Comparte tu perfil y tecnologías en {pres_ref}.\n"
                f"- Explora o publica iniciativas de código en {proj_ref}."
            ),
            color=COLOR_PRIMARY
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url="attachment://welcome_card.png")
        embed.set_footer(
            text=f"Integrante #{guild.member_count} • {guild.name}",
            icon_url=guild.icon.url if guild.icon else None
        )
        return embed

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Dispara el saludo automático con tarjeta gráfica cuando alguien entra al servidor."""
        if member.bot:
            return

        logger.info(f"Nuevo integrante detectado: {member.display_name} ({member.id}) en '{member.guild.name}'")

        channel = await self.get_welcome_channel(member.guild)
        if not channel:
            logger.warning(f"No se encontró ningún canal con permisos de escritura en {member.guild.name}")
            return

        # 1. Generar cita de bienvenida con IA en tono profesional
        quote = await generate_welcome_quote(member.display_name, member.guild.name)
        embed = self.create_welcome_embed(member, quote)

        # 2. Generar tarjeta gráfica estética con fondo de código y avatar
        try:
            avatar_url = member.display_avatar.url if member.display_avatar else None
            card_buf = await generate_welcome_card(
                username=member.display_name,
                member_count=member.guild.member_count or 1,
                avatar_url=avatar_url
            )
            file = discord.File(card_buf, filename="welcome_card.png")
            await channel.send(
                content=f"Bienvenido/a {member.mention} a **{member.guild.name}**.",
                embed=embed,
                file=file
            )
            logger.info(f"Bienvenida con tarjeta gráfica enviada exitosamente a {member.display_name} en #{channel.name}")
        except Exception as e:
            logger.error(f"Error generando tarjeta gráfica de bienvenida para {member.display_name}: {e}", exc_info=True)
            # Fallback seguro: enviar el embed sin archivo si Pillow o la red falla
            try:
                embed.set_image(url=None)
                await channel.send(
                    content=f"Bienvenido/a {member.mention} a **{member.guild.name}**.",
                    embed=embed
                )
            except Exception as e2:
                logger.error(f"Error al enviar mensaje de bienvenida en fallback: {e2}")

        # Registrar el evento en #reportes
        try:
            await log_to_reports(
                guild=member.guild,
                title="Nuevo Miembro Recibido",
                description=f"Se ha procesado y enviado la bienvenida a {member.mention} en {channel.mention}.",
                action_type="bienvenida",
                user=member,
                fields=[
                    ("Miembro", f"{member.display_name} (`{member.id}`)", True),
                    ("Contador de Comunidad", f"#{member.guild.member_count}", True),
                    ("Canal asignado", channel.mention, True)
                ]
            )
        except Exception as e:
            logger.warning(f"Error registrando bienvenida en #reportes: {e}")

    @app_commands.command(name="simular", description="Envía un mensaje de simulación (bienvenida, reglas, roles, reporte o aniversario) para previsualización")
    @app_commands.describe(tipo="Elemento a simular: bienvenida, reglas, roles, reporte o aniversario")
    @app_commands.choices(tipo=[
        app_commands.Choice(name="Bienvenida con tarjeta gráfica", value="bienvenida"),
        app_commands.Choice(name="Reconocimiento de Aniversario", value="aniversario"),
        app_commands.Choice(name="Reglas simplificadas (1 línea)", value="reglas"),
        app_commands.Choice(name="Panel de Roles Técnicos", value="roles"),
        app_commands.Choice(name="Reporte Diario Autónomo", value="reporte")
    ])
    @app_commands.default_permissions(administrator=True)
    async def simulate_message(self, interaction: discord.Interaction, tipo: Optional[str] = "bienvenida"):
        """Comando único para simular cualquier vista principal del servidor."""
        await interaction.response.defer(ephemeral=True)
        choice = (tipo or "bienvenida").lower()

        if choice == "aniversario":
            # Calcular o simular 1 año de permanencia para la previsualización
            now_dt = datetime.now()
            joined = interaction.user.joined_at.replace(tzinfo=None) if interaction.user.joined_at else now_dt
            years = max(now_dt.year - joined.year, 1)
            embed = create_anniversary_embed(interaction.user, years, joined)
            plural = "año" if years == 1 else "años"
            await interaction.followup.send(
                content=f"**[Simulación — Anuncio de Aniversario]** Felicidades {interaction.user.mention} por cumplir hoy **{years} {plural}** siendo parte de la familia de **{interaction.guild.name}**.",
                embed=embed,
                ephemeral=True
            )
            return

        if choice == "reglas":
            from utils.embeds import create_server_rules_embeds
            for emb in create_server_rules_embeds():
                await interaction.followup.send(content="**[Simulación — Reglas del Servidor]**", embed=emb, ephemeral=True)
            return

        if choice == "roles":
            from utils.embeds import create_roles_panel_embed
            from cogs.roles_cog import RolesPanelView
            await interaction.followup.send(
                content="**[Simulación — Panel de Roles]**",
                embed=create_roles_panel_embed(),
                view=RolesPanelView(),
                ephemeral=True
            )
            return

        if choice == "reporte":
            from utils.reporting import build_daily_autonomous_report_embed
            emb = await build_daily_autonomous_report_embed(interaction.guild, self.bot)
            await interaction.followup.send(content="**[Simulación — Reporte Diario Autónomo]**", embed=emb, ephemeral=True)
            return

        quote = await generate_welcome_quote(interaction.user.display_name, interaction.guild.name)
        embed = self.create_welcome_embed(interaction.user, quote)

        try:
            avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None
            card_buf = await generate_welcome_card(
                username=interaction.user.display_name,
                member_count=interaction.guild.member_count or 1,
                avatar_url=avatar_url
            )
            file = discord.File(card_buf, filename="welcome_card.png")
            await interaction.followup.send(
                content=f"**[Simulación — Bienvenida]** Bienvenido/a {interaction.user.mention} a **{interaction.guild.name}**.",
                embed=embed,
                file=file,
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error al generar simulación de bienvenida: {e}", exc_info=True)
            embed.set_image(url=None)
            await interaction.followup.send(
                content=f"**[Simulación — Bienvenida]** Bienvenido/a {interaction.user.mention} a **{interaction.guild.name}**.",
                embed=embed,
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
