import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import List, Optional

from utils.embeds import create_roles_panel_embed, COLOR_SUCCESS, COLOR_WARNING, COLOR_DARK
from utils.reporting import log_to_reports

logger = logging.getLogger("MiniJefe.Roles")

# Definición de roles técnicos limpios y sin ruido visual
SPECIALTY_ROLES = [
    {"name": "Frontend Developer", "desc": "Interfaces web, HTML, CSS, React, Angular, Vue"},
    {"name": "Backend Developer", "desc": "Servicios, APIs, lógica de negocio y bases de datos"},
    {"name": "Fullstack Developer", "desc": "Desarrollo integral Frontend y Backend"},
    {"name": "Mobile Developer", "desc": "Aplicaciones móviles Android, iOS, Flutter, React Native"},
    {"name": "DevOps / Cloud", "desc": "Infraestructura, Docker, CI/CD, Linux y Cloud"},
    {"name": "UI / UX Designer", "desc": "Diseño de interfaces, prototipado y experiencia de usuario"},
    {"name": "Data & AI", "desc": "Ingeniería de datos, análisis, Machine Learning e IA"},
    {"name": "QA & Software Tester", "desc": "Aseguramiento de calidad y pruebas automatizadas"}
]

LANGUAGE_ROLES = [
    {"name": "Java", "desc": "Desarrollo con Java SE, POO y ecosistema JVM"},
    {"name": "Spring Boot", "desc": "Microservicios, Spring Security, JPA y APIs empresariales"},
    {"name": "Python", "desc": "Backend con FastAPI/Django, automatización y ciencia de datos"},
    {"name": "JavaScript / TypeScript", "desc": "Ecosistema web, Node.js, TypeScript y frameworks modernos"},
    {"name": "C / C++", "desc": "Programación de sistemas, algoritmos y alto rendimiento"},
    {"name": "C# / .NET", "desc": "Desarrollo con plataforma .NET, C# y servicios backend"},
    {"name": "Go (Golang)", "desc": "Servicios concurrentes, microservicios y sistemas distribuidos"},
    {"name": "SQL / Bases de Datos", "desc": "Modelado relacional, PostgreSQL, MySQL y optimización"}
]

NOTIFICATION_ROLES = [
    {"name": "Notificaciones Anuncios", "desc": "Avisos generales y actualizaciones del servidor"},
    {"name": "Notificaciones Proyectos", "desc": "Convocatorias para colaborar en proyectos de software"},
    {"name": "Notificaciones Eventos", "desc": "Sesiones de estudio, talleres técnicos y actividades"}
]

SPECIALTY_NAMES = [r["name"] for r in SPECIALTY_ROLES]
LANGUAGE_NAMES = [r["name"] for r in LANGUAGE_ROLES]
NOTIFICATION_NAMES = [r["name"] for r in NOTIFICATION_ROLES]
ALL_MANAGED_ROLE_NAMES = SPECIALTY_NAMES + LANGUAGE_NAMES + NOTIFICATION_NAMES


def get_role_color(role_name: str) -> discord.Color:
    """Devuelve el color sobrio correspondiente según la categoría del rol."""
    if role_name in SPECIALTY_NAMES:
        return discord.Color(0x3B82F6)
    if role_name in LANGUAGE_NAMES:
        return discord.Color(0x0EA5E9)
    return discord.Color(0x64748B)


async def apply_role_changes(
    interaction: discord.Interaction,
    selected_role_names: List[str]
):
    """
    Aplica cambios de roles en modo alternancia (Toggle) sin latencia:
    - Si el usuario selecciona un rol que NO tiene, se le asigna.
    - Si el usuario selecciona un rol que YA tiene, se le retira.
    - Si el rol aún no existe en el servidor, el bot lo crea automáticamente.
    - Al finalizar, restablece el menú desplegable para permitir nuevas selecciones inmediatas.
    """
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    member = interaction.user

    if not guild or not isinstance(member, discord.Member):
        await interaction.followup.send("No se pudo identificar tu perfil en el servidor.", ephemeral=True)
        return

    if not selected_role_names:
        await interaction.followup.send("No seleccionaste ningún rol en el menú.", ephemeral=True)
        return

    roles_cache = {r.name.lower(): r for r in guild.roles}
    member_role_ids = {r.id for r in member.roles}
    bot_top_role = guild.me.top_role

    to_add = []
    to_remove = []
    hierarchy_blocked = []

    for name in selected_role_names:
        role = roles_cache.get(name.lower())

        # Si el rol no existe en el servidor, crearlo automáticamente
        if not role and guild.me.guild_permissions.manage_roles:
            try:
                role = await guild.create_role(
                    name=name,
                    color=get_role_color(name),
                    mentionable=False,
                    reason="Creación automática de rol técnico solicitado en el panel"
                )
                roles_cache[name.lower()] = role
            except Exception as e:
                logger.warning(f"No se pudo crear automáticamente el rol '{name}': {e}")

        if not role:
            continue

        # Verificar jerarquía de roles para evitar bloqueos Forbidden 403
        if role >= bot_top_role and guild.owner_id != guild.me.id:
            hierarchy_blocked.append(role.name)
            continue

        if role.id in member_role_ids:
            to_remove.append(role)
        else:
            to_add.append(role)

    try:
        if to_add:
            await member.add_roles(*to_add, reason="Asignación de roles desde panel de perfil")
        if to_remove:
            await member.remove_roles(*to_remove, reason="Retiro de roles desde panel de perfil")
    except discord.Forbidden:
        await interaction.followup.send(
            "Permiso insuficiente: El rol del bot debe estar ubicado por encima de los roles técnicos en "
            "Ajustes del Servidor > Roles.",
            ephemeral=True
        )
        return
    except Exception as e:
        logger.error(f"Error al actualizar roles de {member.display_name}: {e}")
        await interaction.followup.send(f"Error al actualizar tus roles: {e}", ephemeral=True)
        return

    # Restablecer el estado visual de los menús desplegables en el mensaje del canal
    try:
        if interaction.message:
            await interaction.message.edit(view=RolesPanelView())
    except Exception:
        pass

    lines = ["**Perfil técnico actualizado:**"]
    if to_add:
        lines.append("Asignados: " + ", ".join([f"`{r.name}`" for r in to_add]))
    if to_remove:
        lines.append("Retirados: " + ", ".join([f"`{r.name}`" for r in to_remove]))
    if hierarchy_blocked:
        lines.append(
            "No modificados por jerarquía de permisos: " +
            ", ".join([f"`{n}`" for n in hierarchy_blocked]) +
            " *(el rol del bot debe estar por encima en Ajustes del Servidor)*"
        )

    await interaction.followup.send("\n".join(lines), ephemeral=True)

    if to_add or to_remove:
        try:
            added_str = ", ".join([r.name for r in to_add]) if to_add else "Ninguno"
            removed_str = ", ".join([r.name for r in to_remove]) if to_remove else "Ninguno"
            await log_to_reports(
                guild=guild,
                title="Actualización de Roles de Perfil",
                description=f"El integrante {member.mention} actualizó sus roles técnicos.",
                action_type="roles",
                user=member,
                fields=[
                    ("Roles asignados", added_str, True),
                    ("Roles retirados", removed_str, True)
                ]
            )
        except Exception as e:
            logger.warning(f"Error al registrar cambio de roles en reportes: {e}")


class SpecialtySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=r["name"],
                value=r["name"],
                description=r["desc"][:100]
            )
            for r in SPECIALTY_ROLES
        ]
        super().__init__(
            placeholder="Seleccionar o retirar Especialidad...",
            min_values=1,
            max_values=len(options),
            options=options,
            custom_id="roles_specialty_select"
        )

    async def callback(self, interaction: discord.Interaction):
        await apply_role_changes(interaction, self.values)


class LanguageSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=r["name"],
                value=r["name"],
                description=r["desc"][:100]
            )
            for r in LANGUAGE_ROLES
        ]
        super().__init__(
            placeholder="Seleccionar o retirar Lenguajes y Tecnologías...",
            min_values=1,
            max_values=len(options),
            options=options,
            custom_id="roles_language_select"
        )

    async def callback(self, interaction: discord.Interaction):
        await apply_role_changes(interaction, self.values)


class NotificationSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=r["name"],
                value=r["name"],
                description=r["desc"][:100]
            )
            for r in NOTIFICATION_ROLES
        ]
        super().__init__(
            placeholder="Seleccionar o retirar Preferencias de Avisos...",
            min_values=1,
            max_values=len(options),
            options=options,
            custom_id="roles_notification_select"
        )

    async def callback(self, interaction: discord.Interaction):
        await apply_role_changes(interaction, self.values)


class RolesPanelView(discord.ui.View):
    """Vista persistente para el panel de configuración de roles."""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SpecialtySelect())
        self.add_item(LanguageSelect())
        self.add_item(NotificationSelect())

    @discord.ui.button(
        label="Retirar todos mis roles",
        style=discord.ButtonStyle.secondary,
        custom_id="roles_clear_all_btn"
    )
    async def clear_all_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        member = interaction.user

        if not guild or not isinstance(member, discord.Member):
            await interaction.followup.send("No se pudo identificar tu usuario.", ephemeral=True)
            return

        roles_cache = {r.name.lower(): r for r in guild.roles}
        bot_top_role = guild.me.top_role
        to_remove = []

        for name in ALL_MANAGED_ROLE_NAMES:
            role = roles_cache.get(name.lower())
            if role and role in member.roles:
                if role < bot_top_role or guild.owner_id == guild.me.id:
                    to_remove.append(role)

        if not to_remove:
            await interaction.followup.send("No tienes ningún rol técnico asignado actualmente.", ephemeral=True)
            return

        try:
            await member.remove_roles(*to_remove, reason="Restablecimiento completo de roles solicitado por el usuario")
            removed_list = ", ".join([f"`{r.name}`" for r in to_remove])
            await interaction.followup.send(f"**Se han retirado todos tus roles técnicos:**\n{removed_list}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error al retirar roles: {e}", ephemeral=True)


async def ensure_all_managed_roles(guild: discord.Guild) -> List[str]:
    """Verifica y crea en el servidor todos los roles técnicos que aún no existan."""
    if not guild.me.guild_permissions.manage_roles:
        return []
    existing = {r.name.lower() for r in guild.roles}
    created = []
    for name in ALL_MANAGED_ROLE_NAMES:
        if name.lower() not in existing:
            try:
                await guild.create_role(
                    name=name,
                    color=get_role_color(name),
                    mentionable=False,
                    reason="Configuración de roles técnicos del servidor"
                )
                created.append(name)
            except Exception as e:
                logger.warning(f"Error creando rol '{name}': {e}")
    return created


async def deploy_clean_roles_panel(channel: discord.TextChannel) -> Optional[discord.Message]:
    """Elimina paneles antiguos del bot en el canal de roles y publica el panel limpio actualizado."""
    guild = channel.guild
    await ensure_all_managed_roles(guild)

    # Limpiar mensajes previos enviados por el bot en este canal
    try:
        async for msg in channel.history(limit=30):
            if msg.author.id == guild.me.id:
                try:
                    await msg.delete()
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"No se pudieron limpiar mensajes previos en #{channel.name}: {e}")

    embed = create_roles_panel_embed()
    view = RolesPanelView()
    return await channel.send(embed=embed, view=view)


class RolesCog(commands.Cog, name="Roles"):
    """Gestión de roles técnicos para la comunidad."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        """Auto-recuperación: si el mensaje del panel en #roles se borra por accidente, lo vuelve a publicar."""
        if not payload.guild_id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        channel = guild.get_channel(payload.channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        clean_name = "".join(c for c in channel.name.lower() if c.isalnum())
        if "rol" not in clean_name:
            return

        # Verificar si quedó algún mensaje del bot en el canal de roles
        try:
            has_bot_panel = False
            async for msg in channel.history(limit=15):
                if msg.author.id == guild.me.id and msg.embeds:
                    has_bot_panel = True
                    break
            if not has_bot_panel and channel.permissions_for(guild.me).send_messages:
                logger.info(f"Panel de roles eliminado accidentalmente en #{channel.name}. Regenerando panel...")
                await channel.send(embed=create_roles_panel_embed(), view=RolesPanelView())
        except Exception as e:
            logger.warning(f"Error en auto-regeneración del panel de roles: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(RolesCog(bot))
