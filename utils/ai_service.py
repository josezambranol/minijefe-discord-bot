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
from typing import List, Dict, Optional, Any, Tuple

# Cargar .env si existe localmente
load_dotenv()

logger = logging.getLogger("MiniJefe.AI")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_gemini_api_key() -> Optional[str]:
    """Resuelve la API Key de Gemini desde variables de entorno locales, Render Secret Files o Environment Variables."""
    local_env = os.path.join(BASE_DIR, ".env")
    if os.path.exists(local_env):
        load_dotenv(local_env)
    else:
        load_dotenv()
    
    if os.path.exists("/etc/secrets/.env"):
        load_dotenv("/etc/secrets/.env")

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

    for var in ["GEMINI_API_KEY", "GEMINI_KEY", "GOOGLE_API_KEY", "gemini_api_key", "Gemini_Api_Key"]:
        val = os.getenv(var)
        if val and val != "TU_API_KEY_DE_GEMINI_AQUI":
            return val.strip()

    return None

GEMINI_API_KEY = get_gemini_api_key()

MODELS_PRIORITY = [
    "gemini-flash-lite-latest",
    "gemini-3.8-flash",
    "gemini-flash-latest"
]

# Definición de herramientas (Function Calling) para que Gemini registre tareas en el sistema
TASK_TOOL_DECLARATION = {
    "functionDeclarations": [
        {
            "name": "crear_recordatorio",
            "description": "Registra una tarea o recordatorio periódico en el sistema para un miembro o para el equipo.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "tarea": {
                        "type": "STRING",
                        "description": "Descripción clara y concisa de la tarea a realizar"
                    },
                    "intervalo_minutos": {
                        "type": "INTEGER",
                        "description": "Frecuencia del recordatorio en minutos (ej: 30 para 30 min, 60 para 1 hora, 120 para 2 horas). Si el usuario no indica tiempo o dice 'recuérdame', usa 120."
                    },
                    "usuario": {
                        "type": "STRING",
                        "description": "Nombre, mención o ID del usuario a quien se le asigna la tarea. Si es para el autor del mensaje o no se menciona a nadie más, indicar 'autor'."
                    }
                },
                "required": ["tarea"]
            }
        }
    ]
}

DEFAULT_SYSTEM_PROMPTS = {
    "profesional": (
        "Eres MiniJefe, el asistente técnico y coordinador oficial de la comunidad del servidor {guild_name}. "
        "IDENTIDAD Y TONO: Comunícate de manera profesional, educada, clara y orientada a la colaboración en desarrollo de software. "
        "No uses jerga excesiva ni modismos informales (evita 'bro', 'pana', 'compa', 'qué hubo', 'recocha' o bromas pesadas). "
        "Sé conciso, cortés y técnicamente riguroso. "
        "JERARQUÍA: Habla siempre en nombre del servidor y de la comunidad. No menciones dueños ni jefes individuales. "
        "GESTIÓN DE TAREAS: Si el usuario te solicita agendar, anotar, registrar o recordar una tarea o pendiente, utiliza obligatoriamente la función 'crear_recordatorio' para registrarla en la base de datos."
    ),
    "amigable": (
        "Eres MiniJefe, el asistente técnico y coordinador de la comunidad del servidor {guild_name}. "
        "Comunícate de manera profesional, atenta, clara y colaborativa. "
        "No menciones jefes ni dueños individuales; habla en beneficio del servidor. "
        "Si te piden registrar una tarea o recordatorio, usa la función 'crear_recordatorio'."
    ),
    "programador": (
        "Eres MiniJefe en rol de Desarrollador Senior / Tech Lead para el servidor {guild_name}. "
        "Enfoque técnico de alto nivel, explicaciones concisas, código limpio y buenas prácticas de ingeniería de software. "
        "Si te piden anotar una tarea, usa 'crear_recordatorio'."
    ),
    "tranquilo": (
        "Eres MiniJefe, asistente técnico del servidor {guild_name}. Tono pausado, formal, claro y constructivo."
    )
}

async def ask_gemini_smart(
    prompt: str,
    personality: str = "profesional",
    chat_history: Optional[List[Dict[str, str]]] = None,
    guild_name: str = "el servidor",
    enable_tools: bool = True
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Envía un prompt a Gemini API.
    Devuelve (texto_respuesta, None) si respondió con texto.
    Devuelve (None, {"name": ..., "args": ...}) si detectó la intención de ejecutar una herramienta como crear_recordatorio.
    """
    api_key = get_gemini_api_key()
    if not api_key:
        return ("⚠️ *[MiniJefe]* Clave de Gemini API no configurada.", None)

    template = DEFAULT_SYSTEM_PROMPTS.get(personality, DEFAULT_SYSTEM_PROMPTS["profesional"])
    system_text = template.replace("{guild_name}", guild_name)

    contents: List[Dict[str, Any]] = []

    if chat_history:
        for msg in chat_history[-6:]:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg.get("content", "")}]
            })

    contents.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })

    payload: Dict[str, Any] = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": system_text}]
        },
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 800
        }
    }

    if enable_tools:
        payload["tools"] = [TASK_TOOL_DECLARATION]

    def _extract_response(data: dict) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        candidates = data.get("candidates", [])
        if not candidates:
            return (None, None)
        first = candidates[0]
        if first.get("finishReason") == "SAFETY":
            return ("⚠️ *[MiniJefe]* El mensaje activó los filtros de seguridad de la IA. Por favor realiza una consulta técnica o sobre tareas.", None)
        parts = first.get("content", {}).get("parts", [])
        for part in parts:
            if "functionCall" in part:
                fc = part["functionCall"]
                return (None, {"name": fc.get("name"), "args": fc.get("args", {})})
            if "text" in part:
                return (part["text"].strip(), None)
        return (None, None)

    def _sync_request(url: str, payload_bytes: bytes) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        req = urllib.request.Request(
            url,
            data=payload_bytes,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return _extract_response(res_data)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                logger.warning(f"urllib Rate limit (429) alcanzado en Gemini.")
            else:
                logger.warning(f"urllib HTTPError {e.code}: {e.read().decode('utf-8')[:120]}")
        except Exception as e:
            logger.warning(f"urllib error: {e}")
        return (None, None)

    payload_bytes = json.dumps(payload).encode("utf-8")
    connector = aiohttp.TCPConnector(family=socket.AF_INET)

    # 1. Intentar con aiohttp
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            for model in MODELS_PRIORITY:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                try:
                    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            text_res, tool_res = _extract_response(data)
                            if text_res or tool_res:
                                return (text_res, tool_res)
                        elif resp.status == 429:
                            logger.warning(f"Rate limit / Cuota (429) con modelo {model}. Probando siguiente...")
                            continue
                        else:
                            err_text = await resp.text()
                            logger.warning(f"Error con modelo {model} (Status {resp.status}): {err_text[:120]}")
                except Exception as e:
                    logger.warning(f"Fallo aiohttp con {model}: {e}")
                    continue
    except Exception as e:
        logger.warning(f"Error general en sesión aiohttp: {e}")

    # 2. Fallback síncrono en hilo
    for model in MODELS_PRIORITY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        text_res, tool_res = await asyncio.to_thread(_sync_request, url, payload_bytes)
        if text_res or tool_res:
            return (text_res, tool_res)

    return ("⚡ *El servicio de IA se encuentra momentáneamente ocupado. Por favor intenta de nuevo en unos segundos.*", None)

async def ask_gemini(
    prompt: str,
    personality: str = "profesional",
    chat_history: Optional[List[Dict[str, str]]] = None,
    custom_system_prompt: Optional[str] = None,
    guild_name: str = "el servidor"
) -> str:
    """Envía un prompt a Gemini y devuelve solo el texto de respuesta (compatibilidad)."""
    text_res, _ = await ask_gemini_smart(
        prompt=prompt,
        personality=personality,
        chat_history=chat_history,
        guild_name=guild_name,
        enable_tools=False
    )
    return text_res or "No se pudo obtener respuesta."

async def generate_welcome_quote(member_name: str, guild_name: str) -> str:
    """Genera una bienvenida profesional para un nuevo miembro."""
    prompt = (
        f"Un nuevo desarrollador llamado '{member_name}' se ha unido al servidor '{guild_name}'. "
        f"Escribe un breve mensaje de bienvenida (1 o 2 oraciones) con un tono profesional, cordial y motivador. "
        f"Invítalo a colaborar, presentarse y participar en los canales del servidor. No uses comillas."
    )
    fallback = f"Le damos una cordial bienvenida a **{member_name}** a la comunidad de **{guild_name}**. ¡Mucho éxito en tus proyectos y aprendizaje!"
    try:
        quote = await ask_gemini(prompt, personality="profesional", guild_name=guild_name)
        if quote and "⚠️" not in quote and "⚡" not in quote:
            return quote
    except Exception as e:
        logger.error(f"Error generando bienvenida con IA: {e}")
    return fallback

async def generate_daily_briefing(day_name: str, activities: List[str], goals: Optional[List[str]] = None, guild_name: str = "el servidor") -> str:
    """Genera un resumen diario profesional para la comunidad."""
    activities_text = "\n".join([f"- {a}" for a in activities]) if activities else "No hay eventos especiales programados para hoy."
    goals_text = "\n".join([f"- {g}" for g in goals]) if goals else "Metas sugeridas: avanzar en código, resolver dudas técnicas y colaborar en proyectos."

    prompt = (
        f"Hoy es {day_name}. Eres MiniJefe y vas a publicar el resumen matutino en el canal general de '{guild_name}'.\n"
        f"Actividades registradas:\n{activities_text}\n\n"
        f"Metas de la comunidad:\n{goals_text}\n\n"
        f"Escribe un mensaje breve (máximo 80 palabras), profesional, positivo y enfocado en la productividad y el aprendizaje en equipo."
    )
    fallback = (
        f"🌅 **Buenos días a la comunidad de {guild_name}.** Hoy es **{day_name}**. "
        f"Los invitamos a avanzar en sus proyectos, plantear dudas en los canales temáticos y mantener un día muy productivo."
    )
    try:
        quote = await ask_gemini(prompt, personality="profesional", guild_name=guild_name)
        if quote and "⚠️" not in quote and "⚡" not in quote:
            return quote
    except Exception as e:
        logger.error(f"Error generando plan diario con IA: {e}")
    return fallback

async def generate_daily_system_report(
    guild_name: str,
    stats: Dict[str, Any],
    recent_activities: List[str]
) -> str:
    """Genera una síntesis ejecutiva profesional del día sobre las actividades y operaciones autónomas de MiniJefe."""
    activities_text = "\n".join([f"- {a}" for a in recent_activities[:10]]) if recent_activities else "Operaciones nominales sin incidencias."
    prompt = (
        f"Eres MiniJefe, el asistente técnico oficial del servidor '{guild_name}'. "
        f"Vas a redactar el balance ejecutivo diario para el canal oficial de #reportes. "
        f"Datos operacionales de las últimas 24 horas:\n"
        f"• Recordatorios autónomos ejecutados: {stats.get('reminders_sent', 0)}\n"
        f"• Tareas activas en seguimiento: {stats.get('active_reminders', 0)}\n"
        f"• Acciones de moderación / purga: {stats.get('moderation_actions', 0)}\n"
        f"• Nuevos miembros recibidos: {stats.get('welcomes_count', 0)}\n"
        f"• Tareas/consultas registradas: {stats.get('tasks_created', 0)}\n\n"
        f"Actividades destacadas:\n{activities_text}\n\n"
        f"Redacta un informe ejecutivo conciso (máximo 80 palabras), formal y constructivo, destacando la estabilidad del servidor, el soporte continuo y la colaboración en equipo. No uses comillas."
    )
    fallback = (
        f"📊 **Balance Operativo del Servidor — {guild_name}:** Durante la jornada se mantuvieron activas las automatizaciones de recordatorios y soporte de comunidad. "
        f"Los servicios de moderación, bienvenida e inteligencia artificial operan de manera nominal para mantener el espacio ordenado y productivo."
    )
    try:
        quote = await ask_gemini(prompt, personality="profesional", guild_name=guild_name)
        if quote and "⚠️" not in quote and "⚡" not in quote:
            return quote
    except Exception as e:
        logger.error(f"Error generando reporte diario con IA: {e}")
    return fallback

