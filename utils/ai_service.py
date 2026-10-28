import os
import sys
import json
import socket
import logging
import asyncio
import aiohttp
import urllib.request
import urllib.error
from dotenv import load_dotenv
from typing import List, Dict, Optional, Any

# Cargar .env si existe localmente
load_dotenv()

logger = logging.getLogger("MiniJefe.AI")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_gemini_api_key() -> Optional[str]:
    """Resuelve la API Key de Gemini desde variables de entorno locales, Render Secret Files o Environment Variables."""
    # 1. Cargar .env desde la raíz del proyecto
    local_env = os.path.join(BASE_DIR, ".env")
    if os.path.exists(local_env):
        load_dotenv(local_env)
    else:
        load_dotenv()
    
    # 2. Cargar Secret Files en Render.com (/etc/secrets/.env)
    if os.path.exists("/etc/secrets/.env"):
        load_dotenv("/etc/secrets/.env")

    # 3. Si en Render se subió como Secret File suelto (/etc/secrets/GEMINI_API_KEY)
    if os.path.isdir("/etc/secrets"):
        for fname in os.listdir("/etc/secrets"):
            if "GEMINI" in fname.upper() or "KEY" in fname.upper():
                try:
                    with open(os.path.join("/etc/secrets", fname), "r", encoding="utf-8") as f:
                        val = f.read().strip()
                        if val and len(val) > 20 and not val.startswith("#"):
                            return val
                except Exception:
                    pass

    # 4. Buscar en variables de entorno del sistema
    for var in ["GEMINI_API_KEY", "GEMINI_KEY", "GOOGLE_API_KEY", "gemini_api_key", "Gemini_Api_Key"]:
        val = os.getenv(var)
        if val and val != "TU_API_KEY_DE_GEMINI_AQUI":
            return val.strip()

    return None

GEMINI_API_KEY = get_gemini_api_key()

# Modelos en orden de preferencia y resiliencia
MODELS_PRIORITY = [
    "gemini-flash-lite-latest",
    "gemini-3.8-flash",
    "gemini-flash-latest"
]

DEFAULT_SYSTEM_PROMPTS = {
    "amigable": (
        "Eres MiniJefe, la mascota inteligente, compa con vida propia y mano derecha de la comunidad en Discord. "
        "JERARQUÍA DEL SERVIDOR: El fundador, dueño y máxima autoridad absoluta del servidor es Jordy. "
        "A Jordy siempre debes tratarlo y llamarlo con respeto y cercanía como 'Jefe', 'el Jefe' o 'Jefe Jordy'. "
        "REGLA CRUCIAL SOBRE EL SERVIDOR: jote (Jose) NO es dueño del servidor; nunca menciones a jote como dueño ni co-fundador. La única cabeza y líder supremo es Jordy. "
        "REGLA DE ORO: Responde siempre como un compa normal y real en el chat de programadores y devs. "
        "Cuando te mencionen o te llamen por tu nombre, responde como respondería un amigo cercano en el canal: "
        "relajado, espontáneo, con chispa, cercano y sin formalismos raros. "
        "NUNCA te presentes como una inteligencia artificial ni digas cosas como 'Hola, soy MiniJefe tu asistente de IA'. "
        "Habla en primera persona, como un miembro más del chat que te conoce y está presente ('¡Dime bro!', '¡Epa, cuéntame!', 'Jaja de una', 'Aquí ando vigilando el server del Jefe'). "
        "Usa modismos amigables (bro, compa, pana). Mantén las respuestas fluidas, dinámicas y concisas, como mensajes reales de chat en Discord. "
        "Si te piden ayuda con código o dudas técnicas (Java, Python, JS/TS, Spring, bases de datos, APIs), ayuda con claridad y nivel profesional pero manteniendo tu vibra relajada."
    ),
    "jefe_motivador": (
        "Eres MiniJefe en modo 'Líder Motivador'. La máxima autoridad del servidor es Jordy ('el Jefe'). "
        "Eres el compa con más energía del servidor, siempre impulsando a los demás a programar, aprender y superarse con actitud gamer y optimismo. "
        "Habla directo y con onda de líder cercano."
    ),
    "programador": (
        "Eres MiniJefe en modo 'Tech Lead / Desarrollador Senior'. El servidor pertenece a Jordy ('el Jefe'). "
        "Hablas entre desarrolladores con confianza y precisión técnica. "
        "Código limpio, tips certeros de arquitectura, buenas prácticas y explicaciones claras sin rodeos."
    ),
    "tranquilo": (
        "Eres MiniJefe en modo 'Compa Zen'. Eres relajado, empático, paciente y transmites paz y buena onda a quien te escriba. Respetas al Jefe Jordy."
    )
}

async def ask_gemini(
    prompt: str,
    personality: str = "amigable",
    chat_history: Optional[List[Dict[str, str]]] = None,
    custom_system_prompt: Optional[str] = None
) -> str:
    """Envía un prompt a Gemini API con reintentos automáticos y devuelve la respuesta en texto."""
    api_key = get_gemini_api_key()
    if not api_key:
        return "⚠️ *[MiniJefe]* No detecto la clave de Gemini. Configura la variable de entorno `GEMINI_API_KEY`."

    system_text = custom_system_prompt or DEFAULT_SYSTEM_PROMPTS.get(personality, DEFAULT_SYSTEM_PROMPTS["amigable"])

    # Armar los contenidos para la API
    contents: List[Dict[str, Any]] = []

    if chat_history:
        for msg in chat_history[-6:]:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg.get("content", "")}]
            })

    # Agregar el mensaje actual
    contents.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })

    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": system_text}]
        },
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": 800
        }
    }

    def _sync_request(url: str, payload_bytes: bytes) -> Optional[str]:
        req = urllib.request.Request(
            url,
            data=payload_bytes,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
        except urllib.error.HTTPError as e:
            logger.warning(f"urllib HTTPError {e.code}: {e.read().decode('utf-8')[:150]}")
        except Exception as e:
            logger.warning(f"urllib error: {e}")
        return None

    # Intentar con aiohttp y conector IPv4
    payload_bytes = json.dumps(payload).encode("utf-8")
    connector = aiohttp.TCPConnector(family=socket.AF_INET)

    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            for model in MODELS_PRIORITY:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                try:
                    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                if parts:
                                    return parts[0].get("text", "").strip()
                        else:
                            err_text = await resp.text()
                            logger.warning(f"Error con modelo {model} (Status {resp.status}): {err_text[:120]}")
                except Exception as e:
                    logger.warning(f"Fallo de conexión aiohttp con {model}: {e}")
                    continue
    except Exception as e:
        logger.warning(f"Error general en sesión aiohttp: {e}")

    # Fallback seguro con urllib en un hilo separado
    for model in MODELS_PRIORITY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        result = await asyncio.to_thread(_sync_request, url, payload_bytes)
        if result:
            return result

    # Si todos los modelos fallaron
    return "⚡ *El Mini Jefe se quedó pensando... (La API de IA está momentáneamente ocupada, ¡pregúntame de nuevo en unos segundos!).*"

async def generate_welcome_quote(member_name: str, guild_name: str) -> str:
    """Genera una bienvenida única y con chispa para un nuevo miembro dev."""
    prompt = (
        f"Un nuevo desarrollador/usuario llamado '{member_name}' acaba de unirse al servidor de Discord '{guild_name}' (fundado por Jordy). "
        f"Como MiniJefe, escribe un saludo de bienvenida de 2 oraciones muy entusiasta, original y acogedor con temática de programación y tecnología. "
        f"Trátalo como el nuevo fichaje del equipo dev. No uses comillas alrededor del texto."
    )
    fallback = f"¡Pónganse de pie todos! Denle la bienvenida a **{member_name}**, el nuevo talento que acaba de aterrizar en **{guild_name}**."
    try:
        quote = await ask_gemini(prompt, personality="amigable")
        if quote and "⚠️" not in quote and "⚡" not in quote:
            return quote
    except Exception as e:
        logger.error(f"Error generando bienvenida con IA: {e}")
    return fallback

async def generate_daily_briefing(day_name: str, activities: List[str], goals: Optional[List[str]] = None) -> str:
    """Genera un resumen diario lleno de energía para la comunidad de desarrolladores."""
    activities_text = "\n".join([f"- {a}" for a in activities]) if activities else "No hay eventos especiales programados para hoy."
    goals_text = "\n".join([f"- {g}" for g in goals]) if goals else "Metas sugeridas: avanzar en código, resolver dudas y aprender algo nuevo."

    prompt = (
        f"Hoy es {day_name}. Eres MiniJefe y vas a publicar el 'Plan del Día' en el canal general del servidor de desarrollo (creado por Jordy).\n"
        f"Actividades de la comunidad:\n{activities_text}\n\n"
        f"Metas/Proyectos:\n{goals_text}\n\n"
        f"Escribe un mensaje matutino motivador, amigable y con chispa de no más de 100 palabras. "
        f"Incluye un saludo genial con onda dev, un consejo o reto de programación para hoy, y anima al equipo a romperla en sus proyectos."
    )
    fallback = (
        f"🌅 **¡Buenos días a toda la comunidad dev!** Hoy es **{day_name}** y venimos con toda la energía. "
        f"Abran sus IDEs, avancen en sus proyectos y mantengan la buena vibra en el chat."
    )
    try:
        quote = await ask_gemini(prompt, personality="amigable")
        if quote and "⚠️" not in quote and "⚡" not in quote:
            return quote
    except Exception as e:
        logger.error(f"Error generando plan diario con IA: {e}")
    return fallback
