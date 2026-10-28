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
    """Crea el reglamento oficial extenso, formal y libre de ruido visual para la comunidad de programación."""
    embed1 = discord.Embed(
        title="REGLAMENTO OFICIAL DE LA COMUNIDAD",
        description=(
            "Este servidor es una comunidad técnica enfocada en un 95% al desarrollo de software, ingeniería de sistemas, "
            "arquitectura, aprendizaje continuo y construcción de proyectos colaborativos, con un espacio secundario y "
            "delimitado para la recreación.\n\n"
            "La permanencia y participación en el servidor implican la aceptación y el cumplimiento estricto de las "
            "siguientes disposiciones."
        ),
        color=COLOR_DARK
    )

    embed1.add_field(
        name="1. Convivencia Profesional y Respeto Mutuo",
        value=(
            "Se exige un trato cordial, respetuoso y constructivo entre todos los integrantes, sin importar su nivel "
            "de experiencia (estudiante, autodidacta, junior o senior). Queda estrictamente prohibido el acoso, las "
            "descalificaciones personales, las burlas hacia consultas básicas, la discriminación o cualquier conducta "
            "que genere un ambiente hostil. Los debates sobre lenguajes, frameworks o herramientas deben basarse "
            "exclusivamente en argumentos técnicos y objetivos."
        ),
        inline=False
    )

    embed1.add_field(
        name="2. Estándares para Consultas Técnicas y Depuración",
        value=(
            "Para mantener la calidad técnica de los canales de ayuda, evita publicar mensajes sin contenido como "
            "'¿alguien sabe Java?' o '¿quién me ayuda con un error?'. Redacta tu consulta directamente incluyendo:\n"
            "- El contexto de lo que estás desarrollando.\n"
            "- Qué solución intentaste aplicar y qué resultado esperabas obtener.\n"
            "- El mensaje de error completo (stack trace) y el fragmento de código relevante.\n"
            "El código debe compartirse utilizando bloques de formato Markdown o enlaces a repositorios (GitHub, GitLab, Pastebin). "
            "No se permite subir fotografías de pantallas tomadas con teléfono móvil."
        ),
        inline=False
    )

    embed1.add_field(
        name="3. Orden Temático y Uso Correcto de Canales",
        value=(
            "Cada canal cuenta con un propósito definido. Las consultas de programación, revisiones de arquitectura, "
            "publicación de proyectos y recursos de estudio deben realizarse en su canal correspondiente. El contenido "
            "recreativo o de videojuegos debe mantenerse exclusivamente en el área asignada para ello, evitando desviar "
            "las conversaciones técnicas en los canales de desarrollo."
        ),
        inline=False
    )

    embed1.add_field(
        name="4. Integridad Académica y Aprendizaje Activo",
        value=(
            "Los canales de asistencia técnica existen para orientar, explicar conceptos y apoyar en la resolución de "
            "bloqueos, no para resolver tareas universitarias, exámenes o pruebas técnicas laborales completas por encargo. "
            "Quien solicita ayuda debe demostrar interés en comprender la solución y presentar su avance previo."
        ),
        inline=False
    )

    embed1.add_field(
        name="5. Seguridad de la Información y Manejo de Credenciales",
        value=(
            "Por seguridad propia y de la comunidad, nunca publiques archivos de configuración (.env), claves de API, "
            "tokens de autenticación, contraseñas, direcciones IP privadas ni credenciales de bases de datos. Antes de "
            "compartir un fragmento de código o repositorio, verifica que toda información sensible haya sido reemplazada "
            "por variables de entorno de ejemplo."
        ),
        inline=False
    )

    embed2 = discord.Embed(
        title="NORMATIVA DE PROYECTOS, SEGURIDAD Y MODERACIÓN",
        color=COLOR_DARK
    )

    embed2.add_field(
        name="6. Ética Profesional y Legalidad",
        value=(
            "Queda terminantemente prohibido solicitar, desarrollar, compartir o promover software malicioso (malware), "
            "scripts de intrusión o explotación no autorizada, ataques de denegación de servicio, phishing, evasión de "
            "controles de seguridad, distribución de material sujeto a derechos de autor sin licencia o cualquier "
            "actividad que infrinja la ley o los términos de servicio de Discord."
        ),
        inline=False
    )

    embed2.add_field(
        name="7. Colaboración en Proyectos y Transparencia",
        value=(
            "Las convocatorias para iniciar o integrarse a proyectos de desarrollo deben publicarse en el canal de "
            "proyectos utilizando el formato estándar del servidor. Es obligatorio especificar con claridad el alcance "
            "del proyecto, el stack tecnológico, los perfiles requeridos y la naturaleza de la iniciativa (proyecto de "
            "estudio, código abierto, portafolio o comercial)."
        ),
        inline=False
    )

    embed2.add_field(
        name="8. Política contra Spam, Autopromoción y Mensajes Directos",
        value=(
            "No se permite el envío repetitivo de mensajes (flood), cadenas de texto, enlaces de referidos, promoción "
            "de canales personales, venta de cursos ni invitaciones a otros servidores sin autorización previa de la "
            "administración. Asimismo, está prohibido enviar mensajes privados (DM) no solicitados a miembros del "
            "servidor con fines comerciales, de reclutamiento o spam."
        ),
        inline=False
    )

    embed2.add_field(
        name="9. Uso de Canales de Voz y Sesiones de Trabajo",
        value=(
            "En las salas de voz destinadas a programación en pareja (Pair Programming) y estudio se debe mantener un "
            "entorno ordenado y libre de ruidos molestos. Si tu entorno presenta ruido constante, utiliza la opción de "
            "pulsar para hablar (Push-to-Talk) o silencia el micrófono cuando no estés interviniendo."
        ),
        inline=False
    )

    embed2.add_field(
        name="10. Moderación y Régimen de Sanciones",
        value=(
            "El equipo de administración vela por el cumplimiento de este reglamento. El incumplimiento de las normas "
            "dará lugar a medidas correctivas proporcionales a la falta:\n"
            "1. Advertencia formal e indicación de corrección.\n"
            "2. Restricción temporal de escritura o acceso a canales de voz (Timeout).\n"
            "3. Expulsión del servidor en caso de reincidencia.\n"
            "4. Bloqueo definitivo inmediato ante difusión de malware, estafas, ataques al servidor o faltas graves de respeto."
        ),
        inline=False
    )

    embed2.set_footer(text="Normativa oficial del servidor • Enfoque en ingeniería de software y colaboración")
    return [embed1, embed2]

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
