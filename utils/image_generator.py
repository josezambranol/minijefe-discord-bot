import io
import aiohttp
import logging
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import Optional

logger = logging.getLogger("MiniJefe.ImageGenerator")

def get_font(font_name: str, size: int) -> ImageFont.ImageFont:
    """Intenta cargar una fuente truetype del sistema; si falla, recurre a la fuente por defecto."""
    font_candidates = [
        font_name,
        "consola.ttf",
        "consolas.ttf",
        "arial.ttf",
        "segoeui.ttf",
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for name in font_candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()

async def download_avatar_bytes(avatar_url: str) -> Optional[bytes]:
    """Descarga los bytes del avatar del usuario de Discord."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    return await response.read()
    except Exception as e:
        logger.warning(f"No se pudo descargar el avatar ({avatar_url}): {e}")
    return None

def generate_welcome_card_sync(
    username: str,
    member_count: int,
    avatar_bytes: Optional[bytes] = None
) -> io.BytesIO:
    """Genera síncronamente una tarjeta visual estética de bienvenida estilo Dev/Programación."""
    width, height = 960, 360
    
    # Base oscura con degradado de programación moderna
    img = Image.new("RGBA", (width, height), (13, 16, 26, 255))
    draw = ImageDraw.Draw(img)

    # Fondo degradado azul oscuro / violeta profundo
    for y in range(height):
        ratio = y / height
        r = int(14 * (1 - ratio) + 20 * ratio)
        g = int(17 * (1 - ratio) + 28 * ratio)
        b = int(28 * (1 - ratio) + 48 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # Líneas de código decorativas en el fondo
    code_lines = [
        "// Inicializando entorno de desarrollo...",
        "import { Developer, Team, Vision } from '@community/core';",
        "const member = new Developer({ status: 'ready_to_build' });",
        "await community.register(member, { mentor: 'Jordy (Jefe)' });",
        "console.log('[MiniJefe]: ¡Nuevo talento detectado!');",
        "const stack = ['Java', 'Python', 'TypeScript', 'Docker', 'PostgreSQL'];",
        "while (passion > 0) { learn(); build(); collaborate(); }",
        "return { code: 200, message: 'Welcome to the team!' };"
    ]
    code_font = get_font("consola.ttf", 15)

    y_pos = 28
    for line in code_lines:
        draw.text((320, y_pos), line, font=code_font, fill=(55, 75, 115, 120))
        y_pos += 36

    # Capa de sombra translúcida para hacer legible la tipografía principal
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    for x in range(240, width):
        alpha = int(215 * ((x - 240) / (width - 240)))
        ov_draw.line([(x, 0), (x, height)], fill=(11, 14, 23, min(alpha, 190)))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Borde de la tarjeta con esquinas redondeadas y detalles neón
    draw.rounded_rectangle(
        [10, 10, width - 11, height - 11],
        radius=20,
        outline=(88, 101, 242, 170),
        width=2
    )
    # Acentos neón cyan y violeta en las esquinas
    draw.line([(10, 10), (70, 10)], fill=(0, 229, 255, 255), width=3)
    draw.line([(10, 10), (10, 70)], fill=(0, 229, 255, 255), width=3)
    draw.line([(width - 71, height - 11), (width - 11, height - 11)], fill=(138, 43, 226, 255), width=3)
    draw.line([(width - 11, height - 71), (width - 11, height - 11)], fill=(138, 43, 226, 255), width=3)

    # Avatar circular
    avatar_size = 180
    av_x, av_y = 65, (height - avatar_size) // 2

    if avatar_bytes:
        try:
            av_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
            av_img = av_img.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
        except Exception:
            av_img = None
    else:
        av_img = None

    if av_img is None:
        av_img = Image.new("RGBA", (avatar_size, avatar_size), (88, 101, 242, 255))
        av_draw = ImageDraw.Draw(av_img)
        av_font = get_font("consola.ttf", 36)
        av_draw.text((avatar_size // 4, avatar_size // 3), "</>", fill=(255, 255, 255, 255), font=av_font)

    # Crear máscara circular perfecta para el avatar
    mask = Image.new("L", (avatar_size, avatar_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
    img.paste(av_img, (av_x, av_y), mask)

    # Anillo exterior brillante para el avatar
    draw.ellipse(
        (av_x - 5, av_y - 5, av_x + avatar_size + 5, av_y + avatar_size + 5),
        outline=(0, 229, 255, 240),
        width=4
    )

    # Tipografías para textos
    tag_font = get_font("consola.ttf", 15)
    name_font = get_font("segoeui.ttf", 38)
    sub_font = get_font("segoeui.ttf", 20)
    badge_font = get_font("consola.ttf", 15)

    # Textos
    text_x = 290
    draw.text((text_x, 60), "⚡ BIENVENIDO / NEW RECRUIT DETECTED", font=tag_font, fill=(0, 229, 255, 255))

    clean_name = username if len(username) <= 18 else username[:16] + "..."
    draw.text((text_x, 90), clean_name, font=name_font, fill=(255, 255, 255, 255))

    draw.text(
        (text_x, 155),
        f"Eres el miembro #{member_count} de la comunidad",
        font=sub_font,
        fill=(180, 195, 220, 255)
    )

    # Caja decorativa de comando / badge
    badge_width = 460
    badge_height = 42
    badge_y = 215
    draw.rounded_rectangle(
        [text_x, badge_y, text_x + badge_width, badge_y + badge_height],
        radius=9,
        fill=(25, 32, 50, 230),
        outline=(88, 101, 242, 180),
        width=1
    )
    draw.text(
        (text_x + 18, badge_y + 11),
        "> ./start_journey.sh --stack=fullstack 🚀",
        font=badge_font,
        fill=(114, 137, 218, 255)
    )

    # Punto verde "online / conectado"
    draw.ellipse((text_x + badge_width - 25, badge_y + 16, text_x + badge_width - 15, badge_y + 26), fill=(67, 181, 129, 255))

    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer

async def generate_welcome_card(
    username: str,
    member_count: int,
    avatar_url: Optional[str] = None
) -> io.BytesIO:
    """Genera asíncronamente la tarjeta de bienvenida descargando el avatar si está disponible."""
    avatar_bytes = None
    if avatar_url:
        avatar_bytes = await download_avatar_bytes(avatar_url)

    # Ejecutar el renderizado en un hilo para no bloquear el bucle de eventos de Discord
    import asyncio
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        generate_welcome_card_sync,
        username,
        member_count,
        avatar_bytes
    )
