from datetime import datetime, time
from typing import Dict, List, Any, Optional, Tuple
import pytz
from utils.date_parser import get_now


SCHEDULE_DATA: Dict[str, Dict[str, Any]] = {
    "lunes": {
        "name": "Lunes",
        "day_idx": 0,
        "emoji": "🔵",
        "color": 0x3498DB, # Azul
        "classes": [
            {
                "subject": "Visualización de Datos I",
                "code": "PROFESIO 10270C2T2 - 167",
                "start": "18:45",
                "end": "20:15",
                "location": "Edificio Cedesarrollo — LABSB_E403",
                "building": "Cedesarrollo",
                "room": "LABSB_E403",
                "teacher": "Diana Paola Beetar Baraja",
                "icon": "📊",
                "color": 0x3498DB
            },
            {
                "subject": "Electiva I",
                "code": "ELE_PROF 10272C2T2 - 167",
                "start": "20:15",
                "end": "21:45",
                "location": "Edificio Cedesarrollo — LABSB_E403",
                "building": "Cedesarrollo",
                "room": "LABSB_E403",
                "teacher": "Fabio García Ramírez",
                "icon": "⚡",
                "color": 0x9B59B6
            }
        ]
    },
    "martes": {
        "name": "Martes",
        "day_idx": 1,
        "emoji": "🟢",
        "color": 0x2ECC71, # Verde
        "classes": [
            {
                "subject": "Desarrollo de Software II",
                "code": "PROFESIO 4007C4T4 - 167",
                "start": "18:45",
                "end": "21:45",
                "location": "Edificio Cedesarrollo — LABSB_E104",
                "building": "Cedesarrollo",
                "room": "LABSB_E104",
                "teacher": "Ronald Carrascal Carreazo",
                "icon": "💻",
                "color": 0x2ECC71
            }
        ]
    },
    "miercoles": {
        "name": "Miércoles",
        "day_idx": 2,
        "emoji": "🟡",
        "color": 0xF1C40F, # Amarillo
        "classes": [
            {
                "subject": "Bases de Datos II",
                "code": "PROFESIO 10282C3T3 - 167",
                "start": "18:45",
                "end": "21:00",
                "location": "Edificio Cedesarrollo — LABSB_F501",
                "building": "Cedesarrollo",
                "room": "LABSB_F501",
                "teacher": "Jorge Luis Chavarriaga Vargas",
                "icon": "🗄️",
                "color": 0xF39C12
            }
        ]
    },
    "jueves": {
        "name": "Jueves",
        "day_idx": 3,
        "emoji": "🟠",
        "color": 0xE67E22, # Naranja
        "classes": [
            {
                "subject": "Inglés III",
                "code": "INTEGRAL 10278C2T2 - 167",
                "start": "18:45",
                "end": "20:15",
                "location": "Edificio Cedesarrollo — AULSB_D102",
                "building": "Cedesarrollo",
                "room": "AULSB_D102",
                "teacher": "Jeimmy Victoria Devoz Díaz",
                "icon": "🇬🇧",
                "color": 0x3498DB
            },
            {
                "subject": "Redes de Computadoras",
                "code": "PROFESIO 10271C2T2 - 167",
                "start": "20:15",
                "end": "21:45",
                "location": "Edificio Cedesarrollo — LABSB_E403",
                "building": "Cedesarrollo",
                "room": "LABSB_E403",
                "teacher": "Heybertt Moreno Díaz",
                "icon": "🌐",
                "color": 0x1ABC9C
            }
        ]
    },
    "viernes": {
        "name": "Viernes",
        "day_idx": 4,
        "emoji": "🟣",
        "color": 0xE74C3C, # Rojo / Carmesí
        "classes": [
            {
                "subject": "Ecuaciones Diferenciales",
                "code": "BAS_CIEN 5799C3HT3 - 167",
                "start": "19:30",
                "end": "21:45",
                "location": "Edificio Cedesarrollo — AULSB_C304",
                "building": "Cedesarrollo",
                "room": "AULSB_C304",
                "teacher": "Javier Mendoza Beltrán",
                "icon": "📐",
                "color": 0xE74C3C
            }
        ]
    }
}

DAY_KEYS = ["lunes", "martes", "miercoles", "jueves", "viernes"]
DAY_NAMES_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

def get_day_key_from_datetime(dt: datetime) -> Optional[str]:
    """Obtiene la clave del día (lunes, martes...) a partir de un datetime."""
    weekday = dt.weekday()
    if 0 <= weekday <= 4:
        return DAY_KEYS[weekday]
    return None

def parse_time_str(time_str: str) -> time:
    """Convierte '18:45' a objeto datetime.time."""
    h, m = map(int, time_str.split(":"))
    return time(hour=h, minute=m)

def format_time_12h(time_str: str) -> str:
    """Convierte una hora en formato 24h ('18:45') a formato 12h colombiano ('06:45 PM' o '6:45 PM')."""
    try:
        h, m = map(int, time_str.split(":"))
        period = "AM" if h < 12 else "PM"
        h12 = h % 12
        if h12 == 0:
            h12 = 12
        return f"{h12}:{m:02d} {period}"
    except Exception:
        return time_str

def get_current_and_next_class(tz_name: str = "America/Bogota") -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], str]:

    """
    Retorna (clase_actual_en_curso, proxima_clase_de_hoy, dia_nombre).
    """
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.timezone("America/Bogota")

    now = datetime.now(tz)
    day_key = get_day_key_from_datetime(now)
    
    if not day_key:
        return None, None, DAY_NAMES_ES[now.weekday()]

    day_info = SCHEDULE_DATA[day_key]
    current_class = None
    next_class = None
    now_time = now.time()

    for cls in day_info["classes"]:
        t_start = parse_time_str(cls["start"])
        t_end = parse_time_str(cls["end"])

        if t_start <= now_time <= t_end:
            current_class = cls
        elif now_time < t_start and next_class is None:
            next_class = cls

    return current_class, next_class, day_info["name"]

def get_all_subjects_list() -> List[str]:
    """Retorna una lista limpia de todas las materias únicas para autocompletado."""
    subjects = []
    for day in SCHEDULE_DATA.values():
        for cls in day["classes"]:
            if cls["subject"] not in subjects:
                subjects.append(cls["subject"])
    return subjects
