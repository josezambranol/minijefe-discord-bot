import re
from datetime import datetime, timedelta
import pytz
from dateutil import parser as dateutil_parser
from typing import Optional, Tuple

MONTHS_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12
}

DAYS_ES = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6
}

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

    match_24 = re.match(r"^(\d{1,2}):(\d{2})$", clean)
    if match_24:
        h, m = int(match_24.group(1)), int(match_24.group(2))
        if 0 <= h <= 23 and 0 <= m <= 59:
            return (h, m)

    return None

def parse_task_date(date_str: str, tz_name: str = "America/Bogota") -> Tuple[datetime, Optional[str], str]:
    """
    Parsea fechas en LETRAS, NÚMEROS o TEXTO LIBRE APROXIMADO.
    Nunca falla: si el usuario no sabe la fecha exacta (ej: 'a finales de mes', 'por definir'),
    asigna un plazo prudente de respaldo y conserva el texto exacto.
    
    Retorna: (datetime_objeto, error_si_aplica, texto_mostrable)
    """
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.timezone("America/Bogota")
        
    now = datetime.now(tz)
    raw_input = date_str.strip()
    clean_str = raw_input.lower()

    # 1. Casos de texto totalmente libre / por definir
    if any(k in clean_str for k in ["por definir", "sin fecha", "pendiente", "el profe avisa", "a convenir", "tba"]):
        target = now + timedelta(days=45)
        return target, None, f"{raw_input} (Plazo Flexible)"

    # 2. 'a fin de mes' / 'a finales de mes'
    if "fin de mes" in clean_str or "finales de mes" in clean_str:
        # Último día del mes actual
        next_month = now.replace(day=28) + timedelta(days=4)
        last_day = next_month - timedelta(days=next_month.day)
        target = last_day.replace(hour=23, minute=59, second=0, microsecond=0)
        return target, None, f"Fin de mes ({target.strftime('%d/%m/%Y')})"

    # 3. 'a finales de [mes]' (ej: 'a finales de septiembre')
    for m_name, m_num in MONTHS_ES.items():
        if f"finales de {m_name}" in clean_str or f"fin de {m_name}" in clean_str:
            year = now.year if m_num >= now.month else now.year + 1
            # Último día de ese mes
            next_m = datetime(year, m_num, 28, tzinfo=tz) + timedelta(days=4)
            last_d = next_m - timedelta(days=next_m.day)
            target = last_d.replace(hour=23, minute=59, second=0, microsecond=0)
            return target, None, f"Finales de {m_name.capitalize()} ({target.strftime('%d/%m/%Y')})"

    # 4. Formato: '15 de septiembre [hora]' o '15 de octubre'
    month_match = re.match(r"^(\d{1,2})\s+de\s+([a-záéíóú]+)(?:\s+(?:a\s+las\s+)?(.*))?$", clean_str)
    if month_match:
        day = int(month_match.group(1))
        m_str = month_match.group(2)
        time_part = month_match.group(3)

        if m_str in MONTHS_ES and 1 <= day <= 31:
            m_num = MONTHS_ES[m_str]
            year = now.year if (m_num > now.month or (m_num == now.month and day >= now.day)) else now.year + 1
            
            h, mi = 23, 59
            if time_part:
                p_time = parse_time_12_or_24(time_part)
                if p_time:
                    h, mi = p_time

            try:
                target = tz.localize(datetime(year, m_num, day, h, mi, 0))
                time_disp = f" a las {target.strftime('%I:%M %p').lstrip('0')}" if time_part else ""
                return target, None, f"{day} de {m_str.capitalize()}{time_disp}"
            except ValueError:
                pass

    # 5. Días de la semana en letras: 'el viernes', 'proximo lunes', 'el jueves 6 pm'
    for d_name, d_idx in DAYS_ES.items():
        if d_name in clean_str:
            days_ahead = (d_idx - now.weekday() + 7) % 7
            if days_ahead == 0 and ("proximo" in clean_str or "próximo" in clean_str or "que viene" in clean_str):
                days_ahead = 7
            elif days_ahead == 0:
                days_ahead = 7  # Si es el mismo día, asumir siguiente semana
            
            target_day = now + timedelta(days=days_ahead)
            time_part = re.sub(r"(el|este|próximo|proximo|que viene|del|de la semana)\s*", "", clean_str).replace(d_name, "").strip()
            
            h, mi = 23, 59
            if time_part:
                p_time = parse_time_12_or_24(time_part)
                if p_time:
                    h, mi = p_time

            target = target_day.replace(hour=h, minute=m, second=0, microsecond=0) if 'm' in locals() else target_day.replace(hour=h, minute=mi, second=0, microsecond=0)
            return target, None, f"{d_name.capitalize()} {target.strftime('%d/%m')} ({target.strftime('%I:%M %p').lstrip('0')})"

    # 6. Patrón relativo: 'en X dias / horas / minutos / semanas / meses'
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
        return target, None, raw_input

    # 7. 'mañana [hora]' o 'hoy [hora]'
    if clean_str.startswith("mañana") or clean_str.startswith("manana"):
        target_day = now + timedelta(days=1)
        time_part = clean_str.replace("mañana", "").replace("manana", "").strip() or "11:59 pm"
        parsed_time = parse_time_12_or_24(time_part)
        h, mi = parsed_time if parsed_time else (23, 59)
        target = target_day.replace(hour=h, minute=mi, second=0, microsecond=0)
        return target, None, f"Mañana a las {target.strftime('%I:%M %p').lstrip('0')}"

    if clean_str.startswith("hoy"):
        target_day = now
        time_part = clean_str.replace("hoy", "").strip() or "11:59 pm"
        parsed_time = parse_time_12_or_24(time_part)
        h, mi = parsed_time if parsed_time else (23, 59)
        target = target_day.replace(hour=h, minute=mi, second=0, microsecond=0)
        return target, None, f"Hoy a las {target.strftime('%I:%M %p').lstrip('0')}"

    # 8. Patrón estándar con dateutil (DD/MM/YYYY o DD/MM)
    try:
        parsed_dt = dateutil_parser.parse(clean_str, dayfirst=True)
        if parsed_dt.tzinfo is None:
            if ":" not in clean_str and "pm" not in clean_str and "am" not in clean_str:
                parsed_dt = parsed_dt.replace(hour=23, minute=59, second=0)
            parsed_dt = tz.localize(parsed_dt)
        else:
            parsed_dt = parsed_dt.astimezone(tz)
        return parsed_dt, None, raw_input
    except Exception:
        pass

    # 9. Fallback flexible universal: NUNCA rechazar la tarea
    # Si el usuario escribió cualquier texto (ej. 'segunda entrega de proyecto'), se guarda con plazo de 30 días
    target = now + timedelta(days=30)
    return target, None, f"{raw_input} (~30 días)"

def format_time_left(due_date_iso: str, tz_name: str = "America/Bogota", due_date_text: Optional[str] = None) -> Tuple[str, str, int]:
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
        custom_note = f" *(«{due_date_text}»)*" if due_date_text and "Flexible" in due_date_text else ""
        msg = f"🟢 **Vence en {days} días** ({due_dt.strftime('%d/%m/%Y')}){custom_note}"
        return msg, "NORMAL", total_minutes

def format_date_display(date_iso: str, tz_name: str = "America/Bogota", due_date_text: Optional[str] = None) -> str:
    """Devuelve la fecha legible o el texto flexible personalizado."""
    if due_date_text and ("Flexible" in due_date_text or "Fin de mes" in due_date_text or "Finales" in due_date_text):
        return due_date_text
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
