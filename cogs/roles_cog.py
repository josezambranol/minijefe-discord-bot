import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import List, Optional

from utils.embeds import create_roles_panel_embed, COLOR_SUCCESS, COLOR_WARNING, COLOR_PRIMARY
from utils.reporting import log_to_reports

logger = logging.getLogger("MiniJefe.Roles")

# Definición de roles estándar para la comunidad dev
SPECIALTY_ROLES = [
    {"name": "Frontend Developer", "emoji": "💻", "desc": "HTML, CSS, React, Vue, Angular, Next"},
    {"name": "Backend Developer", "emoji": "⚙️", "desc": "Java, Python, Node, Spring, APIs, DBs"},
    {"name": "Fullstack Developer", "emoji": "🌐", "desc": "Frontend + Backend end-to-end"},
    {"name": "Mobile Developer", "emoji": "📱", "desc": "Android, iOS, Flutter, React Native"},
    {"name": "DevOps / Cloud", "emoji": "☁️", "desc": "Docker, Kubernetes, CI/CD, AWS, Linux"},
    {"name": "UI / UX Designer", "emoji": "🎨", "desc": "Figma, diseño de interfaces y experiencia"},
    {"name": "Data & AI", "emoji": "🤖", "desc": "Machine Learning, Data Science, Python, IA"},
    {"name": "QA & Software Tester", "emoji": "🧪", "desc": "Testing automatizado, calidad de código"}
]

LANGUAGE_ROLES = [
    {"name": "Java", "emoji": "☕", "desc": "Java SE, Spring Boot, POO, Maven"},
    {"name": "Python", "emoji": "🐍", "desc": "Python, Django, FastAPI, Data"},
    {"name": "JavaScript / TypeScript", "emoji": "🟨", "desc": "JS, TS, Node, React, Vue"},
    {"name": "C / C++", "emoji": "🔷", "desc": "Sistemas, embebidos, alto rendimiento"},
    {"name": "C# / .NET", "emoji": "💜", "desc": ".NET Core, C#, Unity, Azure"},
    {"name": "Rust", "emoji": "🦀", "desc": "Memory safe, sistemas y alto rendimiento"},
    {"name": "Go (Golang)", "emoji": "🐹", "desc": "Microservicios, concurrencia, backend"},
    {"name": "PHP", "emoji": "🐘", "desc": "PHP, Laravel, desarrollo web"}
]

NOTIFICATION_ROLES = [
    {"name": "Notificaciones Anuncios", "emoji": "📢", "desc": "Avisos importantes del servidor"},
    {"name": "Notificaciones Proyectos", "emoji": "🚀", "desc": "Nuevas convocatorias y colaboraciones"},
    {"name": "Notificaciones Eventos", "emoji": "📚", "desc": "Talleres, directos y charlas de estudio"}
]

SPECIALTY_NAMES = [r["name"] for r in SPECIALTY_ROLES]
LANGUAGE_NAMES = [r["name"] for r in LANGUAGE_ROLES]
NOTIFICATION_NAMES = [r["name"] for r in NOTIFICATION_ROLES]
ALL_MANAGED_ROLE_NAMES = SPECIALTY_NAMES + LANGUAGE_NAMES + NOTIFICATION_NAMES


async def apply_role_changes(
    interaction: discord.Interaction,
    selected_role_names: List[str],
    category_role_names: List[str]
):
    """
    Aplica cambios de roles por lote de forma ultra-rápida y sin latencia.
    Difiere la interacción de inmediato para garantizar respuesta instantánea (<100ms).
    """
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    member = interaction.user

    if not guild or not isinstance(member, discord.Member):
        await interaction.followup.send("❌ No se pudo identificar al usuario en el servidor.", ephemeral=True)
        return

    # Buscar roles en memoria usando el caché local del servidor (evita peticiones de red lentas)
    roles_cache = {r.name.lower(): r for r in guild.roles}
    member_role_ids = {r.id for r in member.roles}

    to_add = []
    to_remove = []
    missing_roles = []

    for name in category_role_names:
        role = roles_cache.get(name.lower())
        if not role:
            if name in selected_role_names:
                missing_roles.append(name)
            continue

        is_selected = (name in selected_role_names)
        has_role = (role.id in member_role_ids)

        if is_selected and not has_role:
            to_add.append(role)
        elif not is_selected and has_role:
            to_remove.append(role)

    # Si faltan roles en el servidor por crear
    missing_warn = ""
    if missing_roles:
        missing_warn = f"\n⚠️ *Nota: Los roles [{', '.join(missing_roles)}] aún no han sido creados en el servidor.*"

    # Aplicar cambios en lote
    try:
        if to_add:
            await member.add_roles(*to_add, reason="MiniJefe: Auto-asignación de roles rápida")
        if to_remove:
            await member.remove_roles(*to_remove, reason="MiniJefe: Auto-desasignación de roles")
    except discord.Forbidden:
        await interaction.followup.send(
            "🚫 **Permiso denegado por Discord:** El rol de **MiniJefe** debe estar ubicado en la lista de roles "
            "**por encima** de los roles que intenta asignar. Por favor verifica la jerarquía de roles en los Ajustes del Servidor.",
            ephemeral=True
        )
        return
    except Exception as e:
        logger.error(f"Error al cambiar roles de {member.display_name}: {e}")
        await interaction.followup.send(f"❌ Error al procesar los roles: {e}", ephemeral=True)
        return

    # Confirmación al usuario
    if not to_add and not to_remove:
        await interaction.followup.send(
            "ℹ️ Tus roles ya coinciden exactamente con tu selección." + missing_warn,
            ephemeral=True
        )
        return

    added_text = ", ".join([f"`{r.name}`" for r in to_add]) if to_add else "Ninguno"
    removed_text = ", ".join([f"`{r.name}`" for r in to_remove]) if to_remove else "Ninguno"

    await interaction.followup.send(
        f"⚡ **¡Roles actualizados al instante!**\n\n"
        f"➕ **Añadidos:** {added_text}\n"
        f"➖ **Removidos:** {removed_text}"
        f"{missing_warn}",
        ephemeral=True
    )

    # Registrar en #reportes
    try:
        await log_to_reports(
            guild=guild,
            title="Actualización de Roles de Usuario",
            description=f"El miembro {member.mention} actualizó sus roles desde el panel interactivo.",
            action_type="roles",
            user=member,
            fields=[
                ("Roles añadidos (+)", added_text, True),
                ("Roles removidos (-)", removed_text, True)
            ]
        )
    except Exception as e:
        logger.warning(f"Error al registrar cambio de roles en #reportes: {e}")


class SpecialtySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=r["name"],
                value=r["name"],
                description=r["desc"][:100],
                emoji=r["emoji"]
            )
            for r in SPECIALTY_ROLES
        ]
        super().__init__(
            placeholder="💼 Selecciona tus Especialidades / Áreas...",
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id="roles_specialty_select"
        )

    async def callback(self, interaction: discord.Interaction):
        await apply_role_changes(interaction, self.values, SPECIALTY_NAMES)


class LanguageSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=r["name"],
                value=r["name"],
                description=r["desc"][:100],
                emoji=r["emoji"]
            )
            for r in LANGUAGE_ROLES
        ]
        super().__init__(
            placeholder="💻 Selecciona tus Lenguajes de Programación...",
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id="roles_language_select"
        )

    async def callback(self, interaction: discord.Interaction):
        await apply_role_changes(interaction, self.values, LANGUAGE_NAMES)


class NotificationSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=r["name"],
                value=r["name"],
                description=r["desc"][:100],
                emoji=r["emoji"]
            )
            for r in NOTIFICATION_ROLES
        ]
        super().__init__(
            placeholder="🔔 Selecciona tus Notificaciones / Pings...",
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id="roles_notification_select"
        )

    async def callback(self, interaction: discord.Interaction):
        await apply_role_changes(interaction, self.values, NOTIFICATION_NAMES)


class RolesPanelView(discord.ui.View):
    """Vista persistente que sobrevive a reinicios del bot para el panel de roles."""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SpecialtySelect())
        self.add_item(LanguageSelect())
        self.add_item(NotificationSelect())

    @discord.ui.button(
        label="🧹 Limpiar Todos Mis Roles",
        style=discord.ButtonStyle.secondary,
        custom_id="roles_clear_all_btn"
    )
    async def clear_all_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        member = interaction.user

        if not guild or not isinstance(member, discord.Member):
            await interaction.followup.send("❌ Error al identificar tu usuario.", ephemeral=True)
            return

        roles_cache = {r.name.lower(): r for r in guild.roles}
        to_remove = []

        for name in ALL_MANAGED_ROLE_NAMES:
            role = roles_cache.get(name.lower())
            if role and role in member.roles:
                to_remove.append(role)

        if not to_remove:
            await interaction.followup.send("ℹ️ No tienes ningún rol de desarrollo o notificación asignado actualmente.", ephemeral=True)
            return

        try:
            await member.remove_roles(*to_remove, reason="MiniJefe: Limpieza de roles solicitada por el usuario")
            removed_list = ", ".join([f"`{r.name}`" for r in to_remove])
            await interaction.followup.send(f"🧹 **Se han removido los siguientes roles:**\n{removed_list}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error al limpiar roles: {e}", ephemeral=True)


class RolesCog(commands.Cog, name="Roles"):
    """Gestión optimizada y sin latencia de roles interactivos para la comunidad."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="panel-roles", description="Publica el panel interactivo de roles en el canal de roles")
    @app_commands.describe(canal="Canal donde se publicará el panel (por defecto el canal actual)")
    @app_commands.default_permissions(administrator=True)
    async def slash_panel_roles(self, interaction: discord.Interaction, canal: Optional[discord.TextChannel] = None):
        """Publica el panel interactivo de auto-asignación de roles."""
        target_channel = canal or interaction.channel
        if not isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message("❌ Debes especificar un canal de texto válido.", ephemeral=True)
            return

        embed = create_roles_panel_embed()
        view = RolesPanelView()

        try:
            await target_channel.send(embed=embed, view=view)
            await interaction.response.send_message(
                f"✅ ¡Panel interactivo de roles publicado con éxito en {target_channel.mention}!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"❌ No tengo permisos para enviar mensajes en {target_channel.mention}.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error al publicar panel: {e}", ephemeral=True)

    @app_commands.command(name="crear-roles-default", description="Crea automáticamente en el servidor los roles dev que falten")
    @app_commands.default_permissions(administrator=True)
    async def slash_create_default_roles(self, interaction: discord.Interaction):
        """Crea en Discord todos los roles gestionados si aún no existen."""
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            await interaction.followup.send("❌ Servidor no encontrado.", ephemeral=True)
            return

        existing_role_names = {r.name.lower() for r in guild.roles}
        created = []
        already_present = []

        # Configuración de colores para roles por categoría
        color_specialty = discord.Color(0x3498DB)     # Azul
        color_language = discord.Color(0xE67E22)      # Naranja dev
        color_notification = discord.Color(0x9B59B6)  # Púrpura

        role_configs = [
            (SPECIALTY_NAMES, color_specialty),
            (LANGUAGE_NAMES, color_language),
            (NOTIFICATION_NAMES, color_notification)
        ]

        for names, color in role_configs:
            for name in names:
                if name.lower() in existing_role_names:
                    already_present.append(name)
                else:
                    try:
                        await guild.create_role(
                            name=name,
                            color=color,
                            mentionable=False,
                            reason="MiniJefe: Creación automática de roles dev para la comunidad"
                        )
                        created.append(name)
                    except Exception as e:
                        logger.error(f"Error creando rol '{name}': {e}")

        created_str = ", ".join([f"`{n}`" for n in created]) if created else "Ninguno (todos ya existían)"
        await interaction.followup.send(
            f"✅ **Verificación y Creación de Roles Completada:**\n\n"
            f"🆕 **Roles creados ({len(created)}):** {created_str}\n"
            f"📌 **Roles existentes ({len(already_present)}):** Ya estaban listos.\n\n"
            f"💡 *Recuerda asegurarte de que el rol de MiniJefe esté por encima de estos roles en los Ajustes del Servidor.*",
            ephemeral=True
        )

        try:
            await log_to_reports(
                guild=guild,
                title="Creación y Verificación de Roles Dev",
                description=f"Se crearon **{len(created)} roles** nuevos en el servidor.",
                action_type="roles",
                user=interaction.user,
                fields=[
                    ("Roles creados", created_str, False),
                    ("Roles existentes", str(len(already_present)), True)
                ]
            )
        except Exception as e:
            logger.warning(f"Error al reportar creación de roles en #reportes: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(RolesCog(bot))
