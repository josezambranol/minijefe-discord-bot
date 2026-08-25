import re
from datetime import datetime, timedelta
import pytz
from dateutil import parser as dateutil_parser
from typing import Optional, Tuple

def get_now(tz_name: str = "America/Bogota") -> datetime:
    """Obtiene la fecha y hora actual en la zona horaria especificada (por defecto Colombia)."""
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.timezone("America/Bogota")
    return datetime.now(tz)

def parse_time_12_or_24(time_str: str) -> Optional[Tuple[int, int]]:
    """
    Parsea cadenas de hora en formato 12h o 24h:
    - '6:45 pm', '6:45pm', '6pm', '6 pm', '06:45 PM'
    - '18:45', '18:00', '9:30'
    Retorna (hour, minute) en formato 24h.
    """
    clean = time_str.strip().lower()
    
    # Patrón 12h: '6:45 pm', '6:45pm', '6 pm', '6pm'
    match_12 = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$", clean)
    if match_12:
        h = int(match_12.group(1))
        m = int(match_12.group(2)) if match_12.group(2) is not None else 0
        meridiem = match_12.group(3)
        if not (1 <= h <= 12 and 0 <= m <= 59):
            return None
        if meridiem == "pm" and h != 12:
            h += 12
        elif meridiem == "am" and h == 12:
            h = 0
        return (h, m)

    # Patrón 24h: '18:45', '8:30'
    match_24 = re.match(r"^(\d{1,2}):(\d{2})$", clean)
    if match_24:
        h, m = int(match_24.group(1)), int(match_24.group(2))
        if 0 <= h <= 23 and 0 <= m <= 59:
            return (h, m)

    return None

def parse_task_date(date_str: str, tz_name: str = "America/Bogota") -> Tuple[Optional[datetime], Optional[str]]:
    """
    Parsea una cadena de texto a un objeto datetime con zona horaria de Colombia.
    Soporta fechas lejanas (ensayos, talleres, parciales) sin conflicto:
    - 'mañana 6:30 pm', 'mañana 18:00', 'hoy 8 pm'
    - 'en 3 dias', 'en 5 horas', 'en 30 minutos', 'en 2 semanas', 'en 1 mes'
    - '2026-09-15 11:59 pm', '30/08/2026 6:45 pm', '15/10/2026 23:59'
    - '30/08 6:00 pm' (año actual)
    - '30/08/2026' (asume las 11:59 PM de ese día)
    """
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.timezone("America/Bogota")
        
    now = datetime.now(tz)
    clean_str = date_str.strip().lower()

    # 1. Patrón relativo: 'en X dias / horas / minutos / semanas / meses'
    rel_match = re.match(r"^en\s+(\d+)\s+(dia|dias|día|días|hora|horas|minuto|minutos|min|mins|semana|semanas|mes|meses)$", clean_str)
    if rel_match:
        qty = int(rel_match.group(1))
        unit = rel_match.group(2)
        if "dia" in unit or "día" in unit:
            target = now + timedelta(days=qty)
        elif "hora" in unit:
            target = now + timedelta(hours=qty)
        elif "min" in unit:
            target = now + timedelta(minutes=qty)
        elif "semana" in unit:
            target = now + timedelta(weeks=qty)
        elif "mes" in unit:
            target = now + timedelta(days=qty * 30)
        return target, None

    # 2. Patrón: 'mañana [hora]'
    if clean_str.startswith("mañana") or clean_str.startswith("manana"):
        target_day = now + timedelta(days=1)
        time_part = clean_str.replace("mañana", "").replace("manana", "").strip()
        if not time_part:
            time_part = "11:59 pm"
        
        parsed_time = parse_time_12_or_24(time_part)
        if parsed_time:
            h, m = parsed_time
            target = target_day.replace(hour=h, minute=m, second=0, microsecond=0)
            return target, None
        return None, "Formato de hora no válido para mañana. Ejemplos: `mañana 6:30 pm`, `mañana 18:00`"

    # 3. Patrón: 'hoy [hora]'
    if clean_str.startswith("hoy"):
        target_day = now
        time_part = clean_str.replace("hoy", "").strip()
        if not time_part:
            time_part = "11:59 pm"

        parsed_time = parse_time_12_or_24(time_part)
        if parsed_time:
            h, m = parsed_time
            target = target_day.replace(hour=h, minute=m, second=0, microsecond=0)
            if target <= now:
                return None, f"La hora indicada ({time_part}) ya pasó hoy. Por favor especifica una hora futura."
            return target, None
        return None, "Formato de hora no válido para hoy. Ejemplos: `hoy 8:00 pm`, `hoy 20:00`"

    # 4. Patrón: 'DD/MM [hora]' o 'DD-MM [hora]' (sin año explícito)
    day_month_match = re.match(r"^(\d{1,2})[/-](\d{1,2})(?:\s+(.*))?$", clean_str)
    if day_month_match:
        d = int(day_month_match.group(1))
        m = int(day_month_match.group(2))
        time_str = day_month_match.group(3)

        if 1 <= d <= 31 and 1 <= m <= 12:
            h, mi = (23, 59)
            if time_str:
                parsed_time = parse_time_12_or_24(time_str)
                if parsed_time:
                    h, mi = parsed_time
                else:
                    # Intento de parseo estándar si no fue directo
                    try:
                        temp_dt = dateutil_parser.parse(time_str)
                        h, mi = temp_dt.hour, temp_dt.minute
                    except Exception:
                        h, mi = (23, 59)

            try:
                target = tz.localize(datetime(now.year, m, d, h, mi, 0))
                if target < now:
                    target = tz.localize(datetime(now.year + 1, m, d, h, mi, 0))
                return target, None
            except ValueError as e:
                return None, f"Fecha no válida: {str(e)}"

    # 5. Parseo universal usando dateutil con dayfirst=True para formato hispano DD/MM/YYYY
    try:
        parsed_dt = dateutil_parser.parse(clean_str, dayfirst=True)
        if parsed_dt.tzinfo is None:
            if ":" not in clean_str and "pm" not in clean_str and "am" not in clean_str:
                parsed_dt = parsed_dt.replace(hour=23, minute=59, second=0)
            parsed_dt = tz.localize(parsed_dt)
        else:
            parsed_dt = parsed_dt.astimezone(tz)
        return parsed_dt, None
    except Exception:
        return None, "No se pudo interpretar la fecha. Ejemplos válidos:\n• `mañana 6:30 pm`\n• `30/08/2026 8:00 pm`\n• `15/09 11:59 pm`\n• `en 3 dias`\n• `hoy 9:00 pm`"

def format_time_left(due_date_iso: str, tz_name: str = "America/Bogota") -> Tuple[str, str, int]:
    """
    Calcula el tiempo restante o transcurrido y devuelve:
    - (texto_descriptivo_en_formato_12h, nivel_urgencia, minutos_restantes)
    """
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.timezone("America/Bogota")

    now = datetime.now(tz)
    due_dt = datetime.fromisoformat(due_date_iso)
    if due_dt.tzinfo is None:
        due_dt = tz.localize(due_dt)
    else:
        due_dt = due_dt.astimezone(tz)

    diff = due_dt - now
    total_seconds = int(diff.total_seconds())
    total_minutes = total_seconds // 60
    due_time_12 = due_dt.strftime("%I:%M %p").lstrip("0")

    if total_seconds < 0:
        # Vencida
        past_diff = now - due_dt
        days = past_diff.days
        hours = (past_diff.seconds // 3600)
        mins = (past_diff.seconds % 3600) // 60

        if days > 0:
            msg = f"🔴 **Vencida hace {days}d {hours}h** ({due_dt.strftime('%d/%m/%Y')} a las {due_time_12})"
        elif hours > 0:
            msg = f"🔴 **Vencida hace {hours}h {mins}m**"
        else:
            msg = f"🔴 **Vencida hace {mins} minutos**"
        return msg, "OVERDUE", total_minutes

    days = diff.days
    hours = diff.seconds // 3600
    mins = (diff.seconds % 3600) // 60

    if days == 0:
        if hours > 0:
            msg = f"🟠 **Vence hoy en {hours}h {mins}m** (a las {due_time_12})"
        else:
            msg = f"🚨 **¡Vence en {mins} minutos!** (a las {due_time_12})"
        return msg, "TODAY", total_minutes
    elif days == 1:
        msg = f"🟡 **Vence mañana a las {due_time_12}** (en {hours + 24}h)"
        return msg, "SOON", total_minutes
    elif days <= 3:
        msg = f"🟡 **Vence en {days} días y {hours}h** ({due_dt.strftime('%d/%m/%Y')} {due_time_12})"
        return msg, "SOON", total_minutes
    else:
        msg = f"🟢 **Vence en {days} días** ({due_dt.strftime('%d/%m/%Y')} a las {due_time_12})"
        return msg, "NORMAL", total_minutes

def format_date_display(date_iso: str, tz_name: str = "America/Bogota") -> str:
    """Devuelve la fecha en formato 12 horas con AM/PM (Colombia)."""
    try:
        tz = pytz.timezone(tz_name)
        dt = datetime.fromisoformat(date_iso)
        if dt.tzinfo is None:
            dt = tz.localize(dt)
        else:
            dt = dt.astimezone(tz)
        return dt.strftime("%d/%m/%Y %I:%M %p")
    except Exception:
        return date_iso
