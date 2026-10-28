import discord
from typing import Dict, Any, List, Optional
from datetime import datetime
import pytz

# Paleta de colores sobria y profesional para MiniJefe
COLOR_SUCCESS = 0x2ECC71  # Verde confirmación
COLOR_WARNING = 0xF39C12  # Ámbar advertencia
COLOR_DANGER  = 0xE74C3C  # Rojo alerta
COLOR_INFO    = 0x3B82F6  # Azul técnico
COLOR_PURPLE  = 0x6366F1  # Índigo
COLOR_DARK    = 0x1E293B  # Gris pizarra oscuro (sobrio y sin ruido)
COLOR_PRIMARY = 0x1E293B  # Pizarra ejecutivo principal
COLOR_CYAN    = 0x0EA5E9  # Azul acero

def get_discord_timestamp_str(date_iso: str, tz_name: str = "America/Bogota") -> str:
    """Convierte una fecha ISO a tag de timestamp relativo de Discord (<t:UNIX:R>)."""
    try:
        tz = pytz.timezone(tz_name)
        dt = datetime.fromisoformat(date_iso)
        if dt.tzinfo is None:
            dt = tz.localize(dt)
        else:
            dt = dt.astimezone(tz)
        unix_ts = int(dt.timestamp())
        return f"<t:{unix_ts}:R>"
    except Exception:
        return ""

def create_server_rules_embeds() -> List[discord.Embed]:
    """Crea el reglamento oficial en un solo bloque conciso, con reglas de una sola línea fáciles de leer."""
    embed = discord.Embed(
        title="REGLAS DEL SERVIDOR",
        description=(
            "Comunidad enfocada en desarrollo de software, aprendizaje y creación de proyectos.\n\n"
            "**1. Respeto profesional:** Trato cordial con todos sin importar su nivel de experiencia; cero insultos, acoso o toxicidad.\n\n"
            "**2. Consultas directas:** Explica tu problema de código directamente usando bloques de texto o repositorios, sin subir fotos borrosas de celular.\n\n"
            "**3. Cero credenciales:** Nunca publiques claves de API, archivos `.env`, tokens ni contraseñas en ningún canal.\n\n"
            "**4. Orden de canales:** Publica cada tema en su canal correspondiente y mantén la prioridad en programación.\n\n"
            "**5. Proyectos:** Toda búsqueda de equipo o propuesta debe publicarse en el canal de proyectos indicando tecnologías y objetivo.\n\n"
            "**6. Cero spam:** Prohibido el spam, la autopromoción no autorizada y enviar mensajes privados (DM) con fines comerciales.\n\n"
            "**7. Ética y legalidad:** Prohibido compartir malware, piratería, exploits o contenido ilegal.\n\n"
            "**8. Sanciones:** El incumplimiento de estas reglas conlleva advertencia, silencio temporal o expulsión del servidor."
        ),
        color=COLOR_DARK
    )
    embed.set_footer(text="Normativa oficial • Lectura rápida y cumplimiento obligatorio")
    return [embed]

def create_project_template_embed() -> discord.Embed:
    """Plantilla limpia y estructurada para la publicación de proyectos."""
    raw_template = (
        "```markdown\n"
        "NOMBRE DEL PROYECTO: [Nombre o título provisional]\n"
        "MODALIDAD: [Aprendizaje / Open Source / Portafolio / Freelance / Startup]\n"
        "RESUMEN TÉCNICO: [Descripción clara del problema que resuelve y su alcance]\n\n"
        "ARQUITECTURA Y STACK:\n"
        "- Backend: [Ej: Java 21, Spring Boot, Python, Node.js]\n"
        "- Frontend: [Ej: React, Angular, Next.js, Flutter]\n"
        "- Datos e Infraestructura: [Ej: PostgreSQL, Docker, Linux, AWS]\n\n"
        "PERFILES REQUERIDOS:\n"
        "- [Ej: 1 Desarrollador Backend con conocimientos en APIs REST]\n"
        "- [Ej: 1 Desarrollador Frontend para integración de interfaz]\n\n"
        "DEDICACIÓN ESTIMADA: [Ej: 6 horas semanales]\n"
        "REPOSITORIO O DOCUMENTACIÓN: [Enlace opcional a GitHub o documento de diseño]\n"
        "CONTACTO: [Responder en este canal o abrir hilo de seguimiento]\n"
        "```"
    )
    embed = discord.Embed(
        title="ESTÁNDAR PARA PUBLICACIÓN Y BÚSQUEDA DE PROYECTOS",
        description=(
            "Este espacio está destinado a presentar propuestas de desarrollo, buscar colaboradores técnicos y "
            "compartir avances de proyectos de software.\n\n"
            "Para publicar una convocatoria, copia y completa la siguiente estructura:\n"
            f"{raw_template}"
        ),
        color=COLOR_DARK
    )
    embed.set_footer(text="Desarrollo de Proyectos • Estructura técnica obligatoria")
    return embed

def create_roadmap_template_embed() -> discord.Embed:
    """Plantilla sobria para compartir rutas de aprendizaje en la categoría Estudio."""
    raw_template = (
        "```markdown\n"
        "OBJETIVO PROFESIONAL: [Ej: Backend Developer con Java y Spring Boot]\n"
        "NIVEL ACTUAL: [Inicial / Intermedio / Avanzado]\n\n"
        "ETAPAS DEL PLAN DE ESTUDIO:\n"
        "1. [Completado] Fundamentos del lenguaje, estructuras de datos y POO\n"
        "2. [En curso] Desarrollo de servicios REST, Spring Boot y seguridad\n"
        "3. [Pendiente] Modelado de bases de datos SQL, optimización y ORM\n"
        "4. [Pendiente] Pruebas unitarias, contenedores Docker y despliegue\n\n"
        "FUENTES Y DOCUMENTACIÓN:\n"
        "- [Libros, documentación oficial o cursos técnicos que estás utilizando]\n\n"
        "PROYECTO DE PRÁCTICA ACTUAL:\n"
        "- [Qué estás construyendo para aplicar lo estudiado]\n"
        "```"
    )
    embed = discord.Embed(
        title="GUÍA Y FORMATO DE ROADMAPS DE ESTUDIO",
        description=(
            "Utiliza este canal para documentar tu plan de formación técnica, compartir tu progreso y recibir "
            "recomendaciones de arquitectura o bibliografía por parte de otros desarrolladores.\n\n"
            "Formato de referencia sugerido:\n"
            f"{raw_template}"
        ),
        color=COLOR_DARK
    )
    embed.set_footer(text="Área de Estudio • Planificación y formación continua")
    return embed

def create_presentation_template_embed() -> discord.Embed:
    """Plantilla formal y directa para el canal de presentaciones."""
    raw_template = (
        "```markdown\n"
        "Nombre o alias: [Cómo prefieres que te llamen]\n"
        "Perfil actual: [Ej: Estudiante de Ingeniería / Backend Developer / Autodidacta]\n"
        "Tecnologías principales: [Ej: Java, Python, TypeScript, SQL, Git]\n"
        "Enfoque actual: [Qué tecnología o arquitectura estás profundizando]\n"
        "Interés en la comunidad: [Ej: Colaborar en proyectos, estudio técnico, código abierto]\n"
        "GitHub o Portafolio: [Enlace opcional]\n"
        "```"
    )
    embed = discord.Embed(
        title="PRESENTACIÓN DE INTEGRANTES",
        description=(
            "Espacio para que los miembros se presenten ante la comunidad técnica y den a conocer las tecnologías "
            "con las que trabajan.\n\n"
            "Estructura de referencia:\n"
            f"{raw_template}\n"
            "**Ejemplo de presentación:**\n"
            "> Nombre: Carlos\n"
            "> Perfil actual: Desarrollador Backend\n"
            "> Tecnologías principales: Java, Spring Boot, PostgreSQL y Docker.\n"
            "> Enfoque actual: Arquitectura de microservicios y pruebas automatizadas.\n"
            "> Interés en la comunidad: Participar en proyectos colaborativos y compartir recursos técnicos."
        ),
        color=COLOR_DARK
    )
    embed.set_footer(text="Comunidad de Desarrollo • Presentaciones")
    return embed

def create_roles_panel_embed() -> discord.Embed:
    """Embed limpio y directo para el panel de asignación de roles."""
    embed = discord.Embed(
        title="CONFIGURACIÓN DE PERFIL Y ROLES TÉCNICOS",
        description=(
            "Selecciona tus áreas de desarrollo, lenguajes principales y preferencias de notificación para identificar "
            "tu perfil técnico dentro del servidor.\n\n"
            "**Instrucciones de uso:**\n"
            "1. Abre cualquiera de los menús desplegables inferiores y elige las opciones que correspondan a tu perfil.\n"
            "2. **Asignar o retirar un rol:** Si seleccionas un rol que no tienes, se te asignará de inmediato. "
            "Si seleccionas un rol que ya posees, se te retirará automáticamente.\n"
            "3. **Restablecer perfil:** Si deseas retirar todos tus roles técnicos de una sola vez, utiliza el botón **Retirar todos mis roles**."
        ),
        color=COLOR_DARK
    )
    embed.add_field(
        name="1. Especialidades de Ingeniería",
        value="Frontend, Backend, Fullstack, Mobile, DevOps & Cloud, UI/UX, Data & IA, QA & Testing.",
        inline=False
    )
    embed.add_field(
        name="2. Lenguajes y Tecnologías",
        value="Java, Spring Boot, Python, JavaScript / TypeScript, C / C++, C# / .NET, Go, SQL.",
        inline=False
    )
    embed.add_field(
        name="3. Avisos de Actividad",
        value="Notificaciones Anuncios, Notificaciones Proyectos, Notificaciones Eventos.",
        inline=False
    )
    embed.set_footer(text="Gestión de Perfil • Actualización instantánea")
    return embed

def create_anniversary_embed(member: discord.Member, years: int, joined_date: datetime) -> discord.Embed:
    """Crea un embed sobrio y conmemorativo para el aniversario de un miembro en la comunidad."""
    guild = member.guild
    plural = "año" if years == 1 else "años"
    formatted_date = f"{joined_date.day:02d}/{joined_date.month:02d}/{joined_date.year}"

    embed = discord.Embed(
        title=f"Reconocimiento de Aniversario — {member.display_name}",
        description=(
            f"Hoy celebramos el aniversario de {member.mention} en **{guild.name}**.\n\n"
            f"Cumple **{years} {plural}** formando parte de esta familia y comunidad de desarrollo.\n\n"
            f"> *Agradecemos tu permanencia, constancia y contribución al crecimiento de este espacio.*"
        ),
        color=0xD4AF37
    )
    embed.add_field(
        name="Trayectoria",
        value=f"**{years} {plural}** en la comunidad",
        inline=True
    )
    embed.add_field(
        name="Fecha de ingreso",
        value=f"`{formatted_date}`",
        inline=True
    )
    if member.display_avatar:
        embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(
        text=f"{guild.name} • Mérito y Agradecimiento",
        icon_url=guild.icon.url if guild.icon else None
    )
    return embed
