# 🤖 TaskBot — Bot de Tareas y Recordatorios Diarios para Discord

Un bot profesional, interactivo y elegante para Discord diseñado para agendar tareas, enviar recordatorios diarios automáticos antes del plazo límite y gestionar de forma estricta las tareas vencidas.

---

## 🌟 Características Principales

- 📝 **Agendamiento Flexible de Tareas:**
  - Registra: **Tema/Título**, **Descripción**, **Fecha y Hora Límite (Plazo)**, **Usuario Asignado** y **Hora de Recordatorio Diario**.
  - Reconoce lenguaje natural y múltiples formatos: `mañana 18:00`, `en 3 dias`, `hoy 22:00`, `30/08/2026 15:30`, etc.
  - Formulario modal emergente (`/tarea crear`) o parámetros directos.

- ⏰ **Sistema de Recordatorios Diarios Inteligentes:**
  - Cada día a la hora configurada (ej. `09:00 AM`), el bot envía un recordatorio visual del avance.
  - Envía la notificación al **canal del servidor configurado** y también por **Mensaje Directo (DM)** al usuario asignado.
  - Incluye botón directo `✅ Marcar como Completada` en el mismo mensaje.

- 🚨 **Apartado y Detección de Tareas Vencidas:**
  - En cuanto expira el plazo límite, el bot cambia el estado de la tarea a **Vencida**, envía una alerta roja y la agrupa en `/vencidas`.
  - Calcula el tiempo exacto de retraso (ej. *Vencida hace 2 días y 4 horas*).

- 🎛️ **Panel Interactivo con Botones:**
  - `✅ Completar`: Finaliza la tarea en 1 clic.
  - `⏰ Posponer`: Abre una ventana emergente para reprogramar la fecha límite.
  - `🔍 Ver Detalles`: Muestra la ficha técnica completa.
  - `🗑️ Eliminar`: Borra la tarea (solo asignado, creador o admins).

- 📊 **Estadísticas y Resumen:**
  - Comando `/estadisticas` con tasa de cumplimiento, total de tareas registradas, pendientes y vencidas.

---

## 📁 Estructura del Proyecto

```text
discord-task-bot/
├── .env.example          # Plantilla de variables de entorno
├── .env                  # Tu archivo con el DISCORD_TOKEN
├── requirements.txt      # Dependencias de Python
├── bot.py                # Punto de entrada y configuración del bot
├── database.py           # Capa de datos con SQLite asíncrono (aiosqlite)
├── test_bot.py           # Script de pruebas automáticas
├── utils/
│   ├── date_parser.py    # Parser de fechas en español y cálculo de urgencia
│   └── embeds.py         # Tarjetas visuales, alertas y badges de estado
├── views/
│   ├── task_modal.py     # Ventana modal emergente para crear tareas
│   └── task_views.py     # Botoneras interactivas (Completar, Posponer, etc.)
└── cogs/
    ├── tasks_cog.py      # Comandos slash de tareas (/tarea, /tareas, /vencidas)
    ├── admin_cog.py      # Configuración del servidor (/config)
    └── reminders_loop.py # Ciclo en segundo plano para recordatorios y alertas
```

---

## 🚀 Guía de Instalación y Puesta en Marcha

### Paso 1: Crear la Aplicación en Discord Developer Portal

1. Entra a [Discord Developer Portal](https://discord.com/developers/applications).
2. Haz clic en **"New Application"** y dale un nombre (ej. `TaskBot`).
3. Ve a la pestaña **"Bot"** en el menú izquierdo:
   - Haz clic en **"Reset Token"** y **copia tu Token secreto**.
   - En la sección **"Privileged Gateway Intents"**, activa:
     - ✅ **Server Members Intent**
     - ✅ **Message Content Intent**
   - Guarda los cambios (**Save Changes**).

### Paso 2: Invitar el Bot a tu Servidor

1. En el Developer Portal, ve a **"OAuth2"** > **"URL Generator"**.
2. En **SCOPES**, marca:
   - `bot`
   - `applications.commands`
3. En **BOT PERMISSIONS**, marca:
   - `Send Messages`
   - `Embed Links`
   - `Attach Files`
   - `Read Message History`
   - `Use External Emojis`
   - `Manage Messages` (opcional)
   *(O simplemente marca `Administrator` si es tu servidor de pruebas)*.
4. Copia la URL generada al final, pégala en tu navegador y selecciona tu servidor de Discord.

---

### Paso 3: Configurar el archivo `.env`

Abre el archivo `.env` en la carpeta `discord-task-bot` y coloca tu token:

```env
DISCORD_TOKEN=MTE5OTk...tu_token_aqui...
DEFAULT_TIMEZONE=America/Bogota
DEFAULT_REMINDER_TIME=09:00
```

---

### Paso 4: Iniciar el Bot

Abre una terminal en la carpeta del proyecto y ejecuta:

```powershell
# En Windows (usando el entorno virtual creado):
.\.venv\Scripts\python bot.py
```

Al iniciar verás en la consola:
```text
[INFO] Inicializando base de datos SQLite...
[INFO] ¡Sincronizados 7 comandos de aplicación exitosamente!
[INFO] 🤖 Bot conectado como: TaskBot#1234
```

---

## 📖 Lista de Comandos Slash (`/`)

| Comando | Descripción |
|---|---|
| `/tarea crear` | Abre el formulario emergente para crear una tarea (puedes vincular la materia). |
| `/tareas` | Muestra el panel interactivo con pestañas de *Pendientes*, *Vencidas* y *Completadas*. |
| `/vencidas` | Acceso directo exclusivo al apartado de tareas retrasadas con alerta visual roja. |
| `/horario [dia]` | Panel interactivo del horario de clases con menú selector y botones por día. |
| `/clase` | Tarjeta en vivo que indica qué clase está en curso o cuál es la siguiente hoy con cuenta regresiva. |
| `/materias` | Directorio con docentes, salones de Cedesarrollo y códigos de materia. |
| `/tarea ver [id]` | Consulta los detalles completos y botones de acción de una tarea por su ID. |
| `/tarea completar [id]` | Marca una tarea como terminada. |
| `/tarea posponer [id] [nuevo_plazo]` | Amplía la fecha límite de una tarea (ej: `mañana 20:00`). |
| `/tarea eliminar [id]` | Borra una tarea de la base de datos. |
| `/estadisticas` | Muestra el tablero con porcentaje de cumplimiento y resumen total. |
| `/config canal-recordatorios [canal]` | Establece el canal donde se publicarán los recordatorios diarios y avisos de clase. |
| `/config zona-horaria [zona]` | Configura la zona horaria del servidor (ej: `America/Bogota`, `America/Mexico_City`). |
| `/config enviar-md [activar]` | Activa o desactiva las notificaciones por Mensaje Directo (DM). |
| `/config ver` | Muestra los ajustes actuales del servidor. |
| `/probar-recordatorios` | Fuerza la ejecución inmediata del ciclo de recordatorios para pruebas. |


---

## 💡 Nota sobre WhatsApp vs. Discord

> **¿Por qué Discord es ideal para este caso de uso?**
> - Discord ofrece soporte nativo para **botones interactivos**, **formularios modales desplegables**, **menciones con alertas inmediatas** y **tarjetas visuales (Embeds)** con colores de urgencia.
> - En WhatsApp, Meta restringe drásticamente las cuentas personales que usan librerías no oficiales (como Puppeteer/Baileys) aplicando bloqueos de número frecuentes.
> - Si en el futuro deseas enviar notificaciones a WhatsApp de forma oficial, se puede conectar este mismo backend SQLite con la **WhatsApp Cloud API** oficial mediante Webhooks y plantillas autorizadas.
