import discord
from typing import Dict, Any, List, Optional
from datetime import datetime
import pytz

# Paleta de colores temáticos para MiniJefe
COLOR_SUCCESS = 0x2ECC71  # Verde éxito
COLOR_WARNING = 0xF39C12  # Naranja / Amarillo
COLOR_DANGER  = 0xE74C3C  # Rojo alerta / peligro
COLOR_INFO    = 0x3498DB  # Azul cielo
COLOR_PURPLE  = 0x9B59B6  # Morado / Violeta
COLOR_DARK    = 0x2C3E50  # Gris oscuro moderno
COLOR_PRIMARY = 0x5865F2  # Azul Discord Blurple
COLOR_CYAN    = 0x00E5FF  # Cyan Neón Dev

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
    """Crea los embeds completos y pulidos para la sección oficial de reglas del servidor."""
    embed1 = discord.Embed(
        title="📜 REGLAMENTO OFICIAL DE LA COMUNIDAD DEV",
        description=(
            "¡Bienvenido/a a la comunidad! Este espacio está creado para desarrolladores, diseñadores y apasionados de la tecnología. "
            "El objetivo es construir proyectos, compartir conocimiento, resolver dudas y crecer juntos.\n\n"
            "👑 **Autoridad del Servidor:**\n"
            "> El fundador y máxima autoridad de la comunidad es **Jordy (el Jefe)**, acompañado por el equipo de **Staff / Moderación**. "
            "Sus decisiones en materia de convivencia y proyectos son definitivas.\n\n"
            "Al participar en el servidor, aceptas cumplir las siguientes directrices obligatorias:"
        ),
        color=COLOR_PRIMARY
    )

    embed1.add_field(
        name="🤝 1. Convivencia, Respeto y Cero Toxicidad",
        value=(
            "• **Compañerismo:** Respeta a todos sin importar su nivel de experiencia (junior, senior o estudiante). Nadie nació sabiendo.\n"
            "• **Cero tolerancia:** Queda terminantemente prohibido el acoso, los discursos de odio, la discriminación, los insultos personales y el drama innecesario.\n"
            "• **Canal de debates:** Las discusiones sobre tecnologías ('X vs Y') deben ser siempre técnicas, objetivas y amigables."
        ),
        inline=False
    )

    embed1.add_field(
        name="💻 2. Código, Consultas Técnicas y Buenas Prácticas",
        value=(
            "• **Formato de código:** Usa siempre bloques de código Markdown con sintaxis resaltada (ej: ```` ```java ... ``` ````). **Prohibido subir fotos borrosas de pantallas tomadas con el teléfono celular**.\n"
            "• **Preguntas efectivas:** No hagas 'preguntas para preguntar' (ej: *'¿Alguien sabe de Java?'*). Explica directamente tu problema, qué esperabas, qué obtuviste y adjunta el mensaje de error o stack trace.\n"
            "• **Canal correcto:** Realiza tus preguntas en el canal correspondiente a la tecnología (#java, #python, #frontend, etc.)."
        ),
        inline=False
    )

    embed2 = discord.Embed(
        title="🛡️ SEGURIDAD, PROYECTOS Y SANCIONES",
        color=COLOR_PRIMARY
    )

    embed2.add_field(
        name="🚀 3. Proyectos y Colaboración",
        value=(
            "• **Publicación exclusiva:** Para buscar equipo, mostrar avances o reclutar compañeros, usa únicamente el foro **`#proyectos-colaboracion`** siguiendo la plantilla oficial.\n"
            "• **Transparencia:** Todo proyecto debe detallar stack tecnológico, roles requeridos y el propósito (aprendizaje, freelance, startup o portafolio).\n"
            "• **Ética:** Prohibido proponer proyectos ilegales, malware, phishing o herramientas que violen términos de servicio de terceros."
        ),
        inline=False
    )

    embed2.add_field(
        name="🚫 4. No Spam, No DMs Invasivos ni Publicidad",
        value=(
            "• **Mensajes directos (DMs):** Queda prohibido escribirle a miembros por privado para promocionar servicios, vender cursos o hacer ofertas no solicitadas sin su consentimiento previo.\n"
            "• **Autopromoción:** No enlaces a canales de YouTube, redes personales o servidores externos sin autorización del Jefe Jordy o Staff.\n"
            "• **Menciones:** Evita el uso injustificado de `@everyone` o `@here`."
        ),
        inline=False
    )

    embed2.add_field(
        name="🔒 5. Privacidad y Seguridad",
        value=(
            "• **Tokens y Llaves:** NUNCA compartas tokens de Discord, API Keys (.env), credenciales de bases de datos ni datos personales en el chat.\n"
            "• **Seguridad:** Prohibido compartir ejecutables sospechosos (.exe, .bat no verificados) o enlaces acortados dudosos."
        ),
        inline=False
    )

    embed2.add_field(
        name="⚖️ 6. Sistema de Sanciones Escalonadas",
        value=(
            "1️⃣ **Aviso / Warn:** Notificación de MiniJefe o Moderación para corregir la conducta.\n"
            "2️⃣ **Mute temporal (Time-out):** Silencio de 1 hora a 24 horas según la gravedad.\n"
            "3️⃣ **Expulsión (Kick):** Salida del servidor.\n"
            "🚨 **Ban Permanente Inmediato:** Raids, estafas, contenido malicioso o insultos graves hacia miembros o el Staff."
        ),
        inline=False
    )

    embed2.set_footer(text="MiniJefe • Mantengamos limpio el entorno de desarrollo | Servidor de Jordy")
    return [embed1, embed2]

def create_project_template_embed() -> discord.Embed:
    """Plantilla oficial para la publicación de proyectos en el canal de Foro."""
    raw_template = (
        "```markdown\n"
        "📌 NOMBRE DEL PROYECTO: [Nombre aquí]\n"
        "🎯 OBJETIVO: [Aprendizaje / Freelance / Startup / Open Source]\n"
        "📝 DESCRIPCIÓN: [¿En qué consiste el proyecto y qué problema resuelve?]\n"
        "🛠️ STACK TECNOLÓGICO:\n"
        "  • Frontend: [Ej: React / Vue / Flutter / Next.js]\n"
        "  • Backend: [Ej: Java Spring Boot / Python FastAPI / Node]\n"
        "  • Base de datos: [Ej: PostgreSQL / Supabase / MySQL]\n"
        "  • DevOps / Deploy: [Ej: Docker, Render, AWS]\n"
        "👥 PERFILES BUSCADOS:\n"
        "  • [Ej: 1x Frontend Developer (React)]\n"
        "  • [Ej: 1x Backend Developer (Java / Spring)]\n"
        "  • [Ej: 1x Diseñador UI/UX (Figma)]\n"
        "⏱️ DEDICACIÓN ESTIMADA: [Ej: 5 a 10 horas semanales / Fines de semana]\n"
        "📬 CONTACTO / CÓMO UNIRSE: Comenta en este hilo o contacta al creador\n"
        "```"
    )
    embed = discord.Embed(
        title="📋 PLANTILLA OFICIAL PARA PUBLICAR PROYECTOS",
        description=(
            "Usa esta plantilla estándar al crear una nueva publicación en el foro **`#proyectos-colaboracion`**. "
            "Así todos sabrán exactamente qué buscas y cómo pueden sumarse.\n\n"
            f"{raw_template}\n"
            "💡 *Tip: Puedes copiar el bloque de código de arriba y reemplazar los datos entre corchetes.*"
        ),
        color=COLOR_CYAN
    )
    embed.set_footer(text="MiniJefe • Impulsando proyectos y colaboración de la comunidad")
    return embed

def create_roadmap_template_embed() -> discord.Embed:
    """Plantilla oficial para compartir rutas de aprendizaje en la categoría Estudio."""
    raw_template = (
        "```markdown\n"
        "🗺️ MI RUTA DE APRENDIZAJE / ROADMAP PERSONAL\n"
        "👤 Autor: @tu_usuario\n"
        "🎯 Meta Principal: [Ej: Convertirme en Backend Developer con Java]\n"
        "📍 Nivel Actual: [Principiante / Intermedio / Avanzado]\n\n"
        "📚 ETAPAS Y TECNOLOGÍAS:\n"
        "  1. [x] Fundamentos del Lenguaje & POO\n"
        "  2. [ ] Framework Principal (Spring Boot / FastAPI / Express)\n"
        "  3. [ ] Bases de Datos Relacionales (PostgreSQL) y JPA/ORM\n"
        "  4. [ ] Contenedores con Docker y Despliegue en Cloud\n\n"
        "📖 RECURSOS Y CURSOS EN USO:\n"
        "  • [Documentación oficial, cursos en Udemy, libros o roadmap.sh]\n\n"
        "⏱️ RITMO DE ESTUDIO: [Ej: 1.5 horas al día de lunes a viernes]\n"
        "💡 LOGRO O RETO RECIENTE: [¿Qué lograste o en qué te has atascado esta semana?]\n"
        "```"
    )
    embed = discord.Embed(
        title="🗺️ PLANTILLA: COMPARTE TU ROADMAP PERSONAL",
        description=(
            "El canal **`#roadmaps-aprendizaje`** en la categoría **Estudio** es para trazar tus metas, "
            "compartir tus avances y recibir retroalimentación de la comunidad.\n\n"
            f"{raw_template}\n"
            "💡 *Tip: Puedes actualizar tu propio mensaje conforme vayas completando casillas de verificación!*"
        ),
        color=COLOR_PURPLE
    )
    embed.set_footer(text="MiniJefe • Categoría Estudio • El aprendizaje es mejor en comunidad")
    return embed

def create_presentation_template_embed() -> discord.Embed:
    """Plantilla y ejemplo para el canal #presentaciones en la categoría Inicio."""
    raw_template = (
        "```markdown\n"
        "👋 ¡HOLA COMUNIDAD! ME PRESENTO:\n\n"
        "👤 Nombre / Alias: [Tu nombre o cómo te gusta que te llamen]\n"
        "💼 Rol o Área: [Ej: Backend Dev / Frontend / Estudiante / Curioso del código]\n"
        "🛠️ Tecnologías que manejo: [Ej: Java, Python, SQL, Git]\n"
        "🚀 ¿Qué estoy aprendiendo actualmente?: [Ej: Spring Boot y Microservicios]\n"
        "🎯 ¿Qué busco en la comunidad?: [Ej: Colaborar en proyectos, aprender y hacer amigos]\n"
        "🔗 Enlaces (Opcional): [GitHub / Portafolio / LinkedIn]\n"
        "```"
    )
    embed = discord.Embed(
        title="👋 FORMATO DE PRESENTACIÓN OFICIAL",
        description=(
            "¡Queremos conocerte! Copia y pega esta plantilla en el canal **`#presentaciones`** (categoría **Inicio**):\n\n"
            f"{raw_template}\n"
            "✨ **Ejemplo de referencia:**\n"
            "> *\"¡Hola a todos! Soy Carlos, enfocado en backend con Java y Spring Boot. Me encanta optimizar APIs y aprender sobre arquitectura limpia. Actualmente estoy practicando con Docker y PostgreSQL. Me gustaría colaborar en algún proyecto del servidor para ganar experiencia. ¡Un gusto estar aquí!\"*"
        ),
        color=COLOR_SUCCESS
    )
    embed.set_footer(text="MiniJefe • Categoría Inicio • ¡Bienvenido/a a bordo!")
    return embed

def create_roles_panel_embed() -> discord.Embed:
    """Embed principal para el canal de asignación interactiva de roles."""
    embed = discord.Embed(
        title="🎭 PANEL DE ROLES DE LA COMUNIDAD",
        description=(
            "Personaliza tu perfil seleccionando tus áreas de experiencia, lenguajes favoritos y notificaciones.\n\n"
            "⚡ **¿Cómo funciona?**\n"
            "1. Despliega los menús de abajo para elegir los roles que deseas.\n"
            "2. **Añadir o Quitar:** Para quitarte un rol, simplemente desmárcalo en el menú o pulsa el botón correspondiente.\n"
            "3. **Sin latencia:** Los cambios se aplican de forma instantánea y en lote en menos de un segundo.\n\n"
            "📌 *Elige tus categorías a continuación:*",
        ),
        color=0x5865F2
    )
    embed.add_field(
        name="💼 1. Áreas y Especialidades",
        value="Frontend, Backend, Fullstack, Mobile, DevOps, UI/UX, Data & IA, QA.",
        inline=False
    )
    embed.add_field(
        name="💻 2. Lenguajes de Programación",
        value="Java, Python, JavaScript/TypeScript, C/C++, C#, Rust, Go, PHP.",
        inline=False
    )
    embed.add_field(
        name="🔔 3. Notificaciones y Pings",
        value="Anuncios Generales, Proyectos & Colaboración, Eventos & Talleres.",
        inline=False
    )
    embed.set_footer(text="MiniJefe • Sistema de Roles de Alta Velocidad • Sin latencia")
    return embed
