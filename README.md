# 🤖 MiniJefe — Bot de Tareas, Recordatorios & Horario Académico (24/7)

![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.14-blue?logo=python)
![Discord.py](https://img.shields.io/badge/Discord.py-v2.7-5865F2?logo=discord)
![Cloud Hosted](https://img.shields.io/badge/Hosted%20on-Render-46E3B7?logo=render)
![Uptime](https://img.shields.io/badge/Uptime-24%2F7%20Monitored-success?logo=uptimerobot)
![Timezone](https://img.shields.io/badge/Timezone-America%2FBogota%20(12h)-orange)

**MiniJefe** es un bot informativo e interactivo de Discord diseñado específicamente para la gestión académica universitaria, seguimiento ágil de entregas compartidas y control del horario de clases de Cedesarrollo con alertas inteligentes.

---

## 👥 Equipo Oficial (The Squad)

El bot está optimizado y dirigido exclusivamente a los 5 integrantes del equipo con sus Discord IDs registrados:
1. 👑 **jote** (`<@644124012871548958>`) — Líder / Usuario
2. 💻 **jordy** (`<@710931815271235645>`) — Desarrollador
3. ⚡ **Rafxzz"** (`<@1186725307475042395>`) — Miembro
4. 🔥 **ByLogan** (`<@740298769857380435>`) — Miembro
5. 🎯 **SEVINHO** (`<@753613232870260846>`) — Miembro

> [!NOTE]
> **Cero Spam Global:** MiniJefe **NO** utiliza `@everyone` ni `@here`. Todas las alertas y recordatorios están dirigidos directamente a los 5 miembros en el canal oficial **`#private`**.

---

## 🌟 Características Principales

### 🧹 1. Auto-Limpieza Inteligente de Consultas y Paneles Viejos
- **Canal siempre impecable:** Cuando cualquiera de los 5 consulta `/tareas`, `/horario`, `/clase`, `/hoy`, `/materias` o se emite un nuevo aviso automático, el bot **elimina automáticamente los mensajes obsoletos anteriores** de esa categoría, conservando únicamente la versión más reciente.

### 🤝 2. Tablero de Entregas 100% Compartido del Equipo
- **Todas las tareas son del grupo:** Cualquier entrega agregada por cualquiera de los 5 con `/tarea crear` queda visible para todo el equipo en `/tareas` y `/hoy`.
- **Autocompletado de materias:** Al escribir `/tarea crear`, sugiere las materias oficiales de Cedesarrollo.
- **Lenguaje natural en español:** Entiende `mañana 6:30 pm`, `en 3 dias`, `hoy 8:00 pm`, `30/08 2:00 pm`, `15 de septiembre 6 pm`, `a fin de mes`, `por definir`.
- **Completado instantáneo en 1 Clic (`✅ Completar`):** Sin ventanas molestas ni notas de calificación innecesarias; marca como completada y cancela recordatorios de inmediato.

### 🎓 3. Horario Universitario de Clases (Formato 12h Colombia)
- Programación oficial de clases (Lunes a Viernes) en **Edificio Cedesarrollo**.
- Formato estándar de 12 horas (`06:45 PM - 09:45 PM`).
- **🔔 Avisos automáticos 30 minutos antes:** Notifica al equipo qué clase inicia, en qué salón y con qué docente en `#private`.
- **Tarjetas en vivo:** Indica qué clase está en curso y cuenta regresiva para la siguiente.

### ☁️ 4. Arquitectura 24/7 en la Nube
- Desplegado en **Render.com** como servicio web continuo.
- Servidor web interno de salud (`/health`) monitoreado cada 5 minutos por **UptimeRobot** para evitar la suspensión por inactividad.

---

## 📖 Lista de Comandos Slash (`/`)

| Comando | Descripción |
|---|---|
| `/hoy` | 📋 Resumen completo del día: Clases de hoy con salones y lista de tareas pendientes del equipo. |
| `/clase` | 🎓 Tarjeta en vivo que indica qué clase está en curso o cuál es la siguiente con cuenta regresiva. |
| `/horario [dia]` | 🗓️ Panel interactivo del horario con botones rápidos (`Lunes` a `Viernes`) y vista semanal. |
| `/materias` | 📚 Directorio completo con códigos de materia, salones de Cedesarrollo y profesores (12h). |
| `/equipo` | 👥 Directorio de los 5 integrantes del equipo con roles y estado de tareas pendientes. |
| `/tarea crear` | 📝 Agenda una entrega compartida para el equipo vinculada a una materia (con autocompletado). |
| `/tareas [filtro]` | 🗂️ Gestor interactivo con filtros: *Pendientes*, *Vencidas*, *Completadas* y *Todas*. |
| `/vencidas` | 🚨 Acceso directo exclusivo al apartado de tareas retrasadas del equipo. |
| `/tarea ver [id]` | 🔍 Consulta la ficha técnica completa de una tarea. |
| `/tarea completar [id]` | ✅ Marca una tarea como completada directamente. |
| `/tarea posponer [id]` | ⏰ Reprograma la fecha y hora límite de una entrega. |
| `/tarea eliminar [id]` | 🗑️ Elimina una tarea del sistema. |
| `/estadisticas` | 📊 Tablero de rendimiento con porcentaje de cumplimiento y resumen total. |
| `/config canal-recordatorios` | 📢 Configura el canal oficial donde se publicarán los avisos diarios y alertas de clase. |
| `/presentar` | 👋 Muestra la tarjeta oficial de bienvenida y guía de uso para el equipo. |

---

## 📅 Distribución Semanal de Clases (Cedesarrollo - 12h Colombia)

| Día | Horario (12h) | Asignatura & Código | Salón | Docente |
|---|---|---|---|---|
| **🔵 Lunes** | `06:45 PM - 08:15 PM`<br>`08:15 PM - 09:45 PM` | **Visualización de Datos I** (`PROFESIO 10270C2T2`)<br>**Electiva I** (`ELE_PROF 10272C2T2`) | `LABSB_E403`<br>`LABSB_E403` | Diana Paola Beetar Baraja<br>Fabio García Ramírez |
| **🟢 Martes** | `06:45 PM - 09:45 PM` | **Desarrollo de Software II** (`PROFESIO 4007C4T4`) | `LABSB_E104` | Ronald Carrascal Carreazo |
| **🟡 Miércoles** | `06:45 PM - 09:00 PM` | **Bases de Datos II** (`PROFESIO 10282C3T3`) | `LABSB_F501` | Jorge Luis Chavarriaga Vargas |
| **🟠 Jueves** | `06:45 PM - 08:15 PM`<br>`08:15 PM - 09:45 PM` | **Inglés III** (`INTEGRAL 10278C2T2`)<br>**Redes de Computadoras** (`PROFESIO 10271C2T2`) | `AULSB_D102`<br>`LABSB_E403` | Jeimmy Victoria Devoz Díaz<br>Heybertt Moreno Díaz |
| **🟣 Viernes** | `07:30 PM - 09:45 PM` | **Ecuaciones Diferenciales** (`BAS_CIEN 5799C3HT3`) | `AULSB_C304` | Javier Mendoza Beltrán |

---

## 🛠️ Tecnologías y Estructura del Proyecto

```text
minijefe-discord-bot/
├── .env.example          # Plantilla de variables de entorno (sin credenciales)
├── .gitignore            # Bloqueo de seguridad para tokens y base de datos
├── bot.py                # Entrada principal y servidor web de salud 24/7
├── database.py           # Base de datos asíncrona SQLite (aiosqlite)
├── requirements.txt      # Dependencias del proyecto
├── cogs/
│   ├── tasks_cog.py      # Comandos de tareas (/tarea, /tareas, /vencidas, /equipo, /presentar)
│   ├── schedule_cog.py   # Comandos de horario (/horario, /clase, /hoy, /materias)
│   ├── admin_cog.py      # Configuración del servidor (/config)
│   └── reminders_loop.py # Recordatorios automáticos y avisos de clase dirigidos al equipo
├── utils/
│   ├── auto_cleaner.py   # Auto-limpieza inteligente de mensajes y consultas anteriores
│   ├── team_data.py      # Definición y resolución de los 5 integrantes con IDs de Discord
│   ├── date_parser.py    # Parser de fechas en español y cálculo de urgencia en 12h
│   ├── embeds.py         # Diseños visuales con paleta de colores y badges
│   └── schedule_data.py  # Estructura del horario y cálculo de clases en vivo
└── views/
    ├── task_modal.py     # Ventana emergente para agendar tareas del equipo
    ├── task_views.py     # Botoneras interactivas (Completar 1-clic, Posponer, etc.)
    └── schedule_views.py # Menú desplegable y botones por día
```
