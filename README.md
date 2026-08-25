# 🤖 MiniJefe — Bot de Tareas, Recordatorios & Horario Académico (24/7)

![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.14-blue?logo=python)
![Discord.py](https://img.shields.io/badge/Discord.py-v2.7-5865F2?logo=discord)
![Cloud Hosted](https://img.shields.io/badge/Hosted%20on-Render-46E3B7?logo=render)
![Uptime](https://img.shields.io/badge/Uptime-24%2F7%20Monitored-success?logo=uptimerobot)
![Timezone](https://img.shields.io/badge/Timezone-America%2FBogota%20(12h)-orange)

**MiniJefe** es un bot interactivo de Discord diseñado específicamente para la gestión académica universitaria, seguimiento estricto de entregas y control de horarios de clase con alertas inteligentes.

---

## 🌟 Características Principales

### 🎓 1. Horario Universitario de Clases (Formato 12h Colombia)
- Programación oficial de clases (Lunes a Viernes) en **Edificio Cedesarrollo**.
- Manejo de horas en formato estándar de 12 horas (`06:45 PM - 09:45 PM`).
- **🔔 Avisos automáticos 30 minutos antes:** Notifica en el servidor qué clase inicia, en qué salón y con qué docente.
- **Tarjetas en vivo:** Indica qué clase está en curso y cuenta regresiva para la siguiente.

### 📝 2. Gestión Inteligente de Tareas & Entregas
- **Registro con lenguaje natural en español:** Entiende expresiones como `mañana 6:30 pm`, `en 3 dias`, `hoy 8:00 pm`, `30/08 2:00 pm`, `15/09/2026 11:59 pm`.
- **Formulario Modal interactivo:** Ventana emergente con autocompletado de materias.
- **Acciones rápidas con botones:** `✅ Completar` (1 clic), `⏰ Posponer`, `🔍 Ver Detalles`, `🗑️ Eliminar`.

### 🚨 3. Recordatorios Diarios & Sección de Vencidas
- Envía un resumen diario de las tareas activas cada mañana.
- Al vencerse el plazo, pasa la tarea inmediatamente al apartado `/vencidas` y emite una alerta roja con el tiempo exacto de retraso.

### ☁️ 4. Arquitectura 24/7 en la Nube
- Desplegado en **Render.com** como servicio web continuo.
- Servidor web interno de salud (`/health`) monitoreado cada 5 minutos por **UptimeRobot** para evitar la suspensión por inactividad.

---

## 📖 Lista de Comandos Slash (`/`)

| Comando | Descripción |
|---|---|
| `/hoy` | 📋 Resumen completo del día: Clases de hoy con salones y lista de tareas pendientes. |
| `/clase` | 🎓 Tarjeta en vivo que indica qué clase está en curso o cuál es la siguiente con cuenta regresiva. |
| `/horario [dia]` | 🗓️ Panel interactivo del horario con botones rápidos (`Lunes` a `Viernes`) y vista semanal. |
| `/materias` | 📚 Directorio completo con códigos de materia, salones de Cedesarrollo y profesores. |
| `/tarea crear` | 📝 Abre el formulario emergente para agendar una tarea vinculada a una materia y fecha límite. |
| `/tareas [filtro]` | 🗂️ Gestor interactivo con filtros: *Pendientes*, *Vencidas*, *Completadas* y *Todas*. |
| `/vencidas` | 🚨 Acceso directo exclusivo al apartado de tareas retrasadas. |
| `/tarea ver [id]` | 🔍 Consulta la ficha técnica completa de una tarea. |
| `/tarea completar [id]` | ✅ Marca una tarea como finalizada. |
| `/tarea posponer [id]` | ⏰ Reprograma la fecha y hora límite de una entrega. |
| `/tarea eliminar [id]` | 🗑️ Elimina una tarea del sistema. |
| `/estadisticas` | 📊 Tablero de rendimiento con porcentaje de cumplimiento y resumen total. |
| `/config canal-recordatorios` | 📢 Configura el canal oficial donde se publicarán los avisos diarios y alertas de clase. |
| `/presentar` | 👋 Muestra la tarjeta oficial de bienvenida y guía de uso para los miembros del servidor. |

---

## 📅 Distribución Semanal de Clases (Cedesarrollo)

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
├── .env.example          # Plantilla segura de variables de entorno (sin credenciales)
├── .gitignore            # Bloqueo de seguridad para tokens y base de datos
├── bot.py                # Entrada principal y servidor web de salud 24/7
├── database.py           # Base de datos asíncrona SQLite (aiosqlite)
├── requirements.txt      # Dependencias del proyecto
├── cogs/
│   ├── tasks_cog.py      # Comandos de tareas (/tarea, /tareas, /vencidas, /presentar)
│   ├── schedule_cog.py   # Comandos de horario (/horario, /clase, /hoy, /materias)
│   ├── admin_cog.py      # Configuración del servidor (/config)
│   └── reminders_loop.py # Ciclo en segundo plano de recordatorios y avisos 30 min antes
├── utils/
│   ├── date_parser.py    # Parser de fechas en español y cálculo de urgencia en 12h
│   ├── embeds.py         # Diseños visuales con paleta de colores y badges
│   └── schedule_data.py  # Estructura del horario y cálculo de clases en vivo
└── views/
    ├── task_modal.py     # Ventana emergente para agendar tareas
    ├── task_views.py     # Botoneras interactivas (Completar, Posponer, etc.)
    └── schedule_views.py # Menú desplegable y botones por día
```

---

## 🚀 Despliegue en la Nube (24/7)

1. **Configurar Variables:** Crear un archivo `.env` basado en `.env.example` con `DISCORD_TOKEN`, `DEFAULT_TIMEZONE=America/Bogota` y `DEFAULT_REMINDER_TIME=09:00`.
2. **Render.com:** Conectar el repositorio como **Web Service** con runtime `Python 3`, Build Command `pip install -r requirements.txt` y Start Command `python bot.py`.
3. **UptimeRobot:** Agregar la URL pública de Render (ej. `https://tu-app.onrender.com`) con un intervalo de 5 minutos para mantener la instancia activa 24/7.
