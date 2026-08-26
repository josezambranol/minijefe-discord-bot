import discord
from typing import Dict, Any, List, Optional
from datetime import datetime
import pytz
from .date_parser import format_time_left, format_date_display

# Paleta de colores temáticos
COLOR_SUCCESS = 0x2ECC71  # Verde
COLOR_WARNING = 0xF39C12  # Naranja / Amarillo
COLOR_DANGER  = 0xE74C3C  # Rojo
COLOR_INFO    = 0x3498DB  # Azul
COLOR_PURPLE  = 0x9B59B6  # Morado (Completada)
COLOR_DARK    = 0x2C3E50  # Gris oscuro

def get_status_badge(status: str, urgency: str = "NORMAL") -> str:
    if status == "completed":
        return "✅ **COMPLETADA**"
    elif status == "overdue" or urgency == "OVERDUE":
        return "🔴 **VENCIDA**"
    elif urgency == "TODAY":
        return "🟠 **VENCE HOY**"
    elif urgency == "SOON":
        return "🟡 **PRÓXIMA A VENCER**"
    else:
        return "🔵 **EN PROGRESO**"

def get_discord_timestamp_str(date_iso: str, tz_name: str = "America/Bogota") -> str:
    """Convierte una fecha ISO a tag de timestamp de Discord (<t:UNIX:R>)."""
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

def task_detail_embed(task: Dict[str, Any], tz_name: str = "America/Bogota") -> discord.Embed:
    """Crea una tarjeta detallada para una tarea individual."""
    due_date_text = task.get("due_date_text")
    time_str, urgency, _ = format_time_left(task["due_date"], tz_name, due_date_text=due_date_text)
    status = task.get("status", "pending")
    
    if status == "completed":
        color = COLOR_PURPLE
    elif status == "overdue" or urgency == "OVERDUE":
        color = COLOR_DANGER
    elif urgency == "TODAY":
        color = COLOR_WARNING
    else:
        color = COLOR_INFO

    badge = get_status_badge(status, urgency)
    embed = discord.Embed(
        title=f"📌 #{task['id']} — {task['title']}",
        description=task.get("description") or "*Sin observaciones adicionales*",
        color=color
    )
    
    embed.add_field(name="📊 Estado", value=badge, inline=True)
    embed.add_field(name="👥 Destinatarios", value="Todo el equipo (5)", inline=True)
    embed.add_field(name="✍️ Agendada por", value=f"<@{task['creator_id']}>", inline=True)
    
    formatted_due = format_date_display(task["due_date"], tz_name, due_date_text=due_date_text)
    ts_tag = get_discord_timestamp_str(task["due_date"], tz_name)
    plazo_val = f"`{formatted_due}`" + (f" ({ts_tag})" if ts_tag else "")
    
    embed.add_field(name="📅 Plazo / Fecha Límite", value=plazo_val, inline=True)
    embed.add_field(name="⏳ Estado del Plazo", value=time_str, inline=True)
    embed.add_field(name="⏰ Recordatorio Diario", value=f"`{task.get('reminder_time', '09:00')}`", inline=True)

    if task.get("completed_at"):
        completed_fmt = format_date_display(task["completed_at"], tz_name)
        comp_by = f"<@{task['completed_by_id']}>" if task.get("completed_by_id") else "Un integrante"
        comp_ts = get_discord_timestamp_str(task["completed_at"], tz_name)
        comp_text = f"Por {comp_by} el `{completed_fmt}`" + (f" ({comp_ts})" if comp_ts else "")
        embed.add_field(name="✅ Tarea Completada", value=comp_text, inline=False)

    embed.set_footer(text=f"MiniJefe • ID de tarea: #{task['id']} • Zona: {tz_name}")
    return embed

def task_list_embed(
    tasks: List[Dict[str, Any]],
    title: str = "📋 Lista de Tareas del Equipo",
    filter_desc: str = "Mostrando todas las tareas pendientes del equipo",
    tz_name: str = "America/Bogota"
) -> discord.Embed:
    """Crea un embed con la lista de tareas formateada."""
    if not tasks:
        embed = discord.Embed(
            title=title,
            description="🎉 **¡No hay tareas en esta categoría! El equipo está al día.**",
            color=COLOR_SUCCESS
        )
        return embed

    if "Vencidas" in title:
        color = COLOR_DANGER
    elif "Completadas" in title:
        color = COLOR_PURPLE
    else:
        color = COLOR_INFO

    embed = discord.Embed(
        title=f"{title} ({len(tasks)})",
        description=f"{filter_desc}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        color=color
    )

    for task in tasks[:15]:
        due_text = task.get("due_date_text")
        time_str, urgency, _ = format_time_left(task["due_date"], tz_name, due_date_text=due_text)
        creator = f"<@{task['creator_id']}>"
        due_fmt = format_date_display(task["due_date"], tz_name, due_date_text=due_text)
        
        field_value = (
            f"**Agendada por:** {creator} | **Plazo:** `{due_fmt}`\n"
            f"{time_str}"
        )
        if task.get("description"):
            desc_preview = task["description"][:65] + ("..." if len(task["description"]) > 65 else "")
            field_value += f"\n*💬 {desc_preview}*"

        embed.add_field(
            name=f"#{task['id']} 🔹 {task['title']}",
            value=field_value,
            inline=False
        )

    if len(tasks) > 15:
        embed.set_footer(text=f"Mostrando 15 de {len(tasks)} tareas. Usa los filtros para refinar.")
    else:
        embed.set_footer(text=f"Total: {len(tasks)} tareas registradas en el equipo.")

    return embed

def daily_reminder_embed(task: Dict[str, Any], tz_name: str = "America/Bogota") -> discord.Embed:
    """Embed enviado en el recordatorio diario recurrente."""
    time_str, urgency, _ = format_time_left(task["due_date"], tz_name)
    due_fmt = format_date_display(task["due_date"], tz_name)
    ts_tag = get_discord_timestamp_str(task["due_date"], tz_name)

    if urgency == "TODAY":
        color = COLOR_WARNING
        header = "🚨 ¡RECORDATORIO URGENTE: VENCE HOY!"
    elif urgency == "SOON":
        color = COLOR_WARNING
        header = "⏰ RECORDATORIO DIARIO DE TAREA"
    else:
        color = COLOR_INFO
        header = "📅 RECORDATORIO DIARIO DE TAREA"

    embed = discord.Embed(
        title=f"{header} — #{task['id']}",
        description="Hola equipo, tenemos una entrega pendiente en agenda:",
        color=color
    )
    embed.add_field(name="📌 Asignatura / Tema", value=f"**{task['title']}**", inline=False)
    if task.get("description"):
        embed.add_field(name="📝 Descripción", value=task["description"], inline=False)
    
    plazo_txt = f"`{due_fmt}`" + (f" ({ts_tag})" if ts_tag else "")
    embed.add_field(name="📅 Fecha Límite", value=plazo_txt, inline=True)
    embed.add_field(name="⏳ Estado del Plazo", value=time_str, inline=True)
    embed.add_field(name="✍️ Agendada por", value=f"<@{task['creator_id']}>", inline=True)
    
    embed.set_footer(text="💡 Pulsa '✅ Completar' cuando el equipo termine para apagar los recordatorios.")
    return embed

def overdue_alert_embed(task: Dict[str, Any], tz_name: str = "America/Bogota") -> discord.Embed:
    """Embed de alerta máxima cuando una tarea acaba de vencerse."""
    time_str, _, _ = format_time_left(task["due_date"], tz_name)
    due_fmt = format_date_display(task["due_date"], tz_name)

    embed = discord.Embed(
        title=f"🚨 ¡ENTREGA VENCIDA DEL EQUIPO! — #{task['id']}",
        description="Atención equipo, el plazo límite para esta entrega ha expirado.",
        color=COLOR_DANGER
    )
    embed.add_field(name="📌 Asignatura / Tema", value=f"**{task['title']}**", inline=False)
    embed.add_field(name="📅 Plazo Original", value=f"`{due_fmt}`", inline=True)
    embed.add_field(name="⏳ Tiempo Transcurrido", value=time_str, inline=True)
    embed.add_field(name="✍️ Agendada por", value=f"<@{task['creator_id']}>", inline=True)
    
    if task.get("description"):
        embed.add_field(name="📝 Observaciones", value=task["description"], inline=False)
        
    embed.set_footer(text="⚠️ Esta tarea ha sido movida a la sección de Tareas Vencidas (/vencidas).")
    return embed

def stats_embed(stats: Dict[str, int], server_name: str) -> discord.Embed:
    """Embed de resumen del panel de estadísticas."""
    embed = discord.Embed(
        title=f"📊 Resumen de Tareas — {server_name}",
        description="Estado general de tareas asignadas al equipo:\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        color=COLOR_INFO
    )
    embed.add_field(name="📋 Total Registradas", value=f"**{stats['total']}**", inline=True)
    embed.add_field(name="🔵 Pendientes Activas", value=f"**{stats['pending']}**", inline=True)
    embed.add_field(name="🔴 Vencidas (Atrasadas)", value=f"**{stats['overdue']}**", inline=True)
    embed.add_field(name="✅ Completadas", value=f"**{stats['completed']}**", inline=True)
    
    if stats['total'] > 0:
        rate = (stats['completed'] / stats['total']) * 100
        embed.add_field(name="🎯 Tasa de Cumplimiento", value=f"**{rate:.1f}%**", inline=False)

    embed.set_footer(text="MiniJefe • Tablero de Seguimiento Académico")
    return embed

# =========================================================================
# EMBEDS DE HORARIO UNIVERSITARIO (MINIJEFE - FORMATO 12H COLOMBIA)
# =========================================================================

def day_schedule_embed(day_key: str, tz_name: str = "America/Bogota") -> discord.Embed:
    """Genera un embed elegante y detallado para un día de clases específico en formato 12h."""
    from .schedule_data import SCHEDULE_DATA, parse_time_str, format_time_12h, get_now
    
    if day_key not in SCHEDULE_DATA:
        embed = discord.Embed(
            title="🏖️ Sin Clases Programadas",
            description="¡Fin de semana libre! No hay clases registradas para este día.",
            color=COLOR_SUCCESS
        )
        return embed

    day_info = SCHEDULE_DATA[day_key]
    classes = day_info["classes"]
    now = get_now(tz_name)
    is_today = (now.weekday() == day_info["day_idx"])
    now_time = now.time()

    total_classes = len(classes)
    first_start = format_time_12h(classes[0]["start"])
    last_end = format_time_12h(classes[-1]["end"])

    header_tag = "📍 [HOY]" if is_today else ""
    embed = discord.Embed(
        title=f"{day_info['emoji']} Horario de Clases — {day_info['name']} {header_tag}",
        description=(
            f"**Jornada:** `{first_start}` a `{last_end}` • **Materias:** `{total_classes}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=day_info["color"]
    )

    for cls in classes:
        t_start = parse_time_str(cls["start"])
        t_end = parse_time_str(cls["end"])
        start_12 = format_time_12h(cls["start"])
        end_12 = format_time_12h(cls["end"])

        live_badge = ""
        if is_today:
            if t_start <= now_time <= t_end:
                live_badge = " 🔥 **[EN CURSO AHORA]**"
            elif now_time < t_start:
                mins_left = (t_start.hour * 60 + t_start.minute) - (now_time.hour * 60 + now_time.minute)
                hours_left = mins_left // 60
                mins_rem = mins_left % 60
                if hours_left > 0:
                    live_badge = f" ⏳ *(Comienza en {hours_left}h {mins_rem}m)*"
                else:
                    live_badge = f" ⏳ *(Comienza en {mins_left} min)*"
            else:
                live_badge = " ✔️ *(Finalizada)*"

        field_name = f"{cls['icon']} {cls['subject']}{live_badge}"
        field_value = (
            f"⏰ **Horario:** `{start_12} - {end_12}`\n"
            f"📍 **Salón:** `{cls['location']}`\n"
            f"👨‍🏫 **Docente:** `{cls['teacher']}`\n"
            f"🏷️ **Código:** `{cls['code']}`"
        )
        embed.add_field(name=field_name, value=field_value, inline=False)

    embed.set_footer(text=f"MiniJefe • Cedesarrollo • Hora Colombia ({tz_name})")
    return embed

def full_week_schedule_embed(tz_name: str = "America/Bogota") -> discord.Embed:
    """Genera una vista panorámica semanal completa del horario en formato 12h."""
    from .schedule_data import SCHEDULE_DATA, format_time_12h
    
    embed = discord.Embed(
        title="🗓️ Horario Académico Semanal Completo",
        description="Distribución de materias de Lunes a Viernes en Cedesarrollo:\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        color=COLOR_INFO
    )

    for key, day in SCHEDULE_DATA.items():
        classes_text = []
        for cls in day["classes"]:
            start_12 = format_time_12h(cls['start'])
            end_12 = format_time_12h(cls['end'])
            classes_text.append(f"• **`{start_12} - {end_12}`** {cls['icon']} **{cls['subject']}**\n  ↳ 📍 `{cls['location']}` | 👨‍🏫 *{cls['teacher']}*")
        
        embed.add_field(
            name=f"{day['emoji']} {day['name'].upper()}",
            value="\n".join(classes_text) + "\n",
            inline=False
        )

    embed.set_footer(text="MiniJefe • Horario de Ingeniería • Hora Colombia")
    return embed

def today_live_class_embed(tz_name: str = "America/Bogota") -> discord.Embed:
    """Genera una tarjeta en vivo mostrando qué clase toca hoy en formato 12h."""
    from .schedule_data import get_current_and_next_class, get_now, SCHEDULE_DATA, get_day_key_from_datetime, format_time_12h, parse_time_str
    
    now = get_now(tz_name)
    current_cls, next_cls, day_name = get_current_and_next_class(tz_name)
    day_key = get_day_key_from_datetime(now)

    if not day_key:
        embed = discord.Embed(
            title=f"🏖️ ¡Hoy es {day_name}!",
            description="No tienes clases programadas para el fin de semana. ¡A descansar!",
            color=COLOR_SUCCESS
        )
        return embed

    time_now_12 = now.strftime('%I:%M %p').lstrip('0')
    embed = discord.Embed(
        title=f"🎓 Estado Académico de Hoy — {day_name}",
        description=f"🕒 Hora actual en Colombia: `{time_now_12}`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        color=COLOR_INFO
    )

    if current_cls:
        embed.color = COLOR_WARNING
        start_12 = format_time_12h(current_cls["start"])
        end_12 = format_time_12h(current_cls["end"])
        embed.add_field(
            name=f"🔥 CLASE EN CURSO: {current_cls['icon']} {current_cls['subject']}",
            value=(
                f"⏰ **Horario:** `{start_12} - {end_12}`\n"
                f"📍 **Salón:** `{current_cls['location']}`\n"
                f"👨‍🏫 **Docente:** `{current_cls['teacher']}`"
            ),
            inline=False
        )

    if next_cls:
        start_12 = format_time_12h(next_cls["start"])
        end_12 = format_time_12h(next_cls["end"])
        t_start = parse_time_str(next_cls["start"])
        now_mins = now.hour * 60 + now.minute
        start_mins = t_start.hour * 60 + t_start.minute
        diff = start_mins - now_mins
        h_diff = diff // 60
        m_diff = diff % 60
        time_desc = f"en {h_diff}h {m_diff}m" if h_diff > 0 else f"en {m_diff} minutos"

        embed.add_field(
            name=f"⏳ Siguiente Clase: {next_cls['icon']} {next_cls['subject']} *(Inicia {time_desc})*",
            value=(
                f"⏰ **Hora:** `{start_12}` a `{end_12}`\n"
                f"📍 **Salón:** `{next_cls['location']}`\n"
                f"👨‍🏫 **Docente:** `{next_cls['teacher']}`\n"
                f"🏷️ **Código:** `{next_cls['code']}`"
            ),
            inline=False
        )

    if not current_cls and not next_cls:
        embed.color = COLOR_SUCCESS
        embed.add_field(
            name="🎉 Jornada Finalizada",
            value="¡Ya terminaron todas las clases del día de hoy!",
            inline=False
        )

    day_info = SCHEDULE_DATA[day_key]
    summary = " • ".join([f"{c['icon']} {c['subject']} (`{format_time_12h(c['start'])}`)" for c in day_info["classes"]])
    embed.add_field(name="📋 Materias de Hoy", value=summary, inline=False)
    embed.set_footer(text="MiniJefe • Consulta cualquier día con /horario")
    return embed

def class_reminder_alert_embed(cls: Dict[str, Any], minutes_before: int, tz_name: str = "America/Bogota") -> discord.Embed:
    """Embed de alerta previa a que empiece una clase en formato 12h."""
    from .schedule_data import format_time_12h
    start_12 = format_time_12h(cls["start"])
    end_12 = format_time_12h(cls["end"])

    embed = discord.Embed(
        title=f"🔔 ¡RECORDATORIO: CLASE EN {minutes_before} MINUTOS!",
        description=f"Atención equipo, en breve comienza la clase de **{cls['subject']}**.",
        color=COLOR_WARNING
    )
    embed.add_field(name="📚 Asignatura", value=f"{cls['icon']} **{cls['subject']}**", inline=False)
    embed.add_field(name="⏰ Horario", value=f"`{start_12} - {end_12}`", inline=True)
    embed.add_field(name="📍 Salón", value=f"`{cls['location']}`", inline=True)
    embed.add_field(name="👨‍🏫 Docente", value=f"`{cls['teacher']}`", inline=False)
    embed.add_field(name="🏷️ Código", value=f"`{cls['code']}`", inline=True)
    embed.set_footer(text="MiniJefe • Aviso de Horario • Cedesarrollo")
    return embed

def today_briefing_embed(tasks: List[Dict[str, Any]], tz_name: str = "America/Bogota") -> discord.Embed:
    """Embed de resumen general del día (Clases + Tareas pendientes)."""
    from .schedule_data import SCHEDULE_DATA, get_now, get_day_key_from_datetime, format_time_12h
    
    now = get_now(tz_name)
    day_key = get_day_key_from_datetime(now)
    time_now_12 = now.strftime('%I:%M %p').lstrip('0')
    date_now_str = now.strftime('%d/%m/%Y')

    embed = discord.Embed(
        title=f"📋 Resumen Académico del Día — {now.strftime('%A').capitalize()} {date_now_str}",
        description=f"🕒 **Hora actual en Colombia:** `{time_now_12}`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        color=COLOR_INFO
    )

    # 1. Clases de hoy
    if day_key and day_key in SCHEDULE_DATA:
        day_info = SCHEDULE_DATA[day_key]
        classes_lines = []
        for cls in day_info["classes"]:
            s12 = format_time_12h(cls["start"])
            e12 = format_time_12h(cls["end"])
            classes_lines.append(f"{cls['icon']} **{cls['subject']}**\n↳ ⏰ `{s12} - {e12}` | 📍 `{cls['location']}` | 👨‍🏫 *{cls['teacher']}*")
        embed.add_field(
            name="🎓 Clases de Hoy (Cedesarrollo)",
            value="\n\n".join(classes_lines),
            inline=False
        )
    else:
        embed.add_field(
            name="🎓 Clases de Hoy",
            value="🎉 ¡Hoy no hay clases programadas! Descanso.",
            inline=False
        )

    # 2. Tareas pendientes
    if tasks:
        task_lines = []
        for t in tasks[:6]:
            due_fmt = format_date_display(t["due_date"], tz_name)
            ts_tag = get_discord_timestamp_str(t["due_date"], tz_name)
            task_lines.append(f"• **#{t['id']} {t['title']}** — `{due_fmt}` {ts_tag} (<@{t['assigned_user_id']}>)")
        embed.add_field(
            name=f"📝 Entregas Pendientes Activas ({len(tasks)})",
            value="\n".join(task_lines),
            inline=False
        )
    else:
        embed.add_field(
            name="📝 Entregas Pendientes",
            value="✨ **¡No hay entregas pendientes en este momento! Todo al día.**",
            inline=False
        )

    embed.set_footer(text="MiniJefe • Asistente Académico del Equipo")
    return embed

def team_directory_embed(guild: Optional[discord.Guild], member_task_counts: Optional[Dict[int, int]] = None) -> discord.Embed:
    """Embed que presenta a los 5 integrantes del equipo oficial de MiniJefe."""
    from .team_data import get_team_directory_info

    embed = discord.Embed(
        title="👥 Equipo Oficial de MiniJefe (The Squad)",
        description=(
            "Este bot está configurado y optimizado específicamente para los **5 integrantes del grupo**:\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=COLOR_INFO
    )

    directory = get_team_directory_info(guild)
    for entry in directory:
        info = entry["info"]
        member = entry["member"]
        mention = entry["mention"]
        
        status_str = "🟢 En el servidor" if member else "⚪ Fuera de línea"
        pending_txt = ""
        if member and member_task_counts and member.id in member_task_counts:
            cnt = member_task_counts[member.id]
            pending_txt = f" • **{cnt}** pendientes"

        field_name = f"{info['emoji']} {info['display_name']} (`{info['role']}`)"
        field_value = f"• **Usuario:** {mention}\n• **Estado:** {status_str}{pending_txt}"
        embed.add_field(name=field_name, value=field_value, inline=False)

    embed.set_footer(text="MiniJefe • Alertas y tareas personalizadas sin spam de @everyone")
    return embed

def welcome_introduction_embed() -> discord.Embed:
    """Embed oficial de presentación de MiniJefe para el servidor."""
    embed = discord.Embed(
        title="👋 ¡Hola a todos! Soy MiniJefe 🤖",
        description=(
            "Soy el **Asistente Informativo de Tareas & Horario Académico** del equipo.\n"
            "Mi propósito es mantenernos al día con las clases de Cedesarrollo y el seguimiento de entregas pendientes.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=COLOR_INFO
    )

    embed.add_field(
        name="👥 1. Equipo Oficial (5 Integrantes)",
        value="Configurado especialmente para: **jote**, **jordy** (dev), **rafxzz**, **ByLogan** y **SEVINHO**.\n*(No usamos menciones globales `@everyone` ni `@here`)*.",
        inline=False
    )

    embed.add_field(
        name="📝 2. Gestión Rápida de Entregas",
        value=(
            "• `/tarea crear` — Agenda una entrega con autocompletado de materias y lenguaje natural.\n"
            "• `/tareas` — Panel interactivo de tareas (Pendientes, Vencidas, Completadas).\n"
            "• **1 Clic:** Botón directo **`✅ Completar`** para marcar tareas finalizadas al instante."
        ),
        inline=False
    )

    embed.add_field(
        name="⏰ 3. Avisos Inteligentes & Horario (12h)",
        value=(
            "• `/horario` — Horario semanal interactivo por días con salones y profesores.\n"
            "• `/clase` — Vista en vivo de qué clase está en curso y la que sigue.\n"
            "• **Avisos automáticos:** Notificación del bot 30 minutos antes del inicio de clase."
        ),
        inline=False
    )

    embed.set_footer(text="MiniJefe • Escribe /horario, /hoy o /tarea crear para comenzar.")
    return embed
