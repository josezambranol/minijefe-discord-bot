# 🤖 MiniJefe — Bot Comunitario con IA, Recordatorios Periódicos, Anti-Spam y Bienvenidas (24/7)

![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.14-blue?logo=python)
![Discord.py](https://img.shields.io/badge/Discord.py-v2.7-5865F2?logo=discord)
![AI Powered](https://img.shields.io/badge/AI-Google%20Gemini-orange?logo=google)
![Hosted](https://img.shields.io/badge/Hosted%20on-Render%20%7C%20Local-46E3B7?logo=render)
![Timezone](https://img.shields.io/badge/Timezone-America%2FBogota%20(12h)-orange)

**MiniJefe** es la mascota inteligente y co-líder con vida del servidor de Discord de **Jordy** (fundador del servidor) y **Jote** (dueño del bot). Equipado con la API de **Google Gemini**, MiniJefe cobra vida en el chat, recibe a los nuevos miembros, modera el spam de forma amigable, organiza la agenda diaria y permite a los líderes delegar tareas a cualquier miembro con **recordatorios periódicos automáticos** (cada 30 min, 1 hora, 2 horas, etc.) hasta que se completen.

---

## 🌟 Funcionalidades Principales

### ⏰ 1. Tareas Delegadas & Recordatorios Periódicos Flexibles
Tanto **Jordy** como **Jote** (o el equipo de moderación/staff) pueden asignar tareas a cualquier miembro con intervalos personalizados:
- **En lenguaje natural por chat o canal de staff:**
  > `@MiniJefe recuérdale a @usuario subir el informe cada 2 horas`  
  > `@MiniJefe ponle una tarea a @usuario de revisar los logs cada 30 minutos`  
  > MiniJefe responderá confirmando la orden: *"¡A la orden, Jefe! 🫡 Registrado..."*
- **Comando Slash:**
  > `/recordar usuario:@pepito tarea:Actualizar roles del servidor cada_horas:2 por_md:True`
- **Avisos automáticos e Interactivos:**
  - MiniJefe envía el aviso en el canal (o por mensaje directo) cada vez que se cumple el tiempo.
  - El mensaje incluye un botón directo: **`[✅ Marcar como Listo]`**. Al pulsarlo, la tarea se completa y los recordatorios se apagan automáticamente.
  - Botón **`[🛑 Cancelar]`** exclusivo para Jordy, Jote o el creador de la tarea.
- **Gestión:** `/recordatorios-activos`, `/tarea-lista [id]`, `/tarea-cancelar [id]`.

---

### 🧠 2. MiniJefe "Cobra Vida" con Inteligencia Artificial (Gemini)
- **Charla viva por mención:** Menciona a `@MiniJefe` en cualquier canal para platicar, pedirle opiniones, consejos de código o bromear.
- **Memoria de conversación:** Mantiene el hilo contextual de los últimos mensajes del canal.
- **Personalidades con `/personalidad`:**
  - `amigable`: Relajado, carismático, bromista y compa del servidor *(por defecto)*.
  - `jefe_motivador`: Alta energía y ánimo imparable.
  - `programador`: Tech Lead / Senior Dev para resolver dudas técnicas y de programación.
  - `tranquilo`: Compa Zen, pacífico y buena vibra.
- **Comandos:** `/hablar [mensaje]`, `/olvidar-charla`.

---

### 👋 3. Sistema de Bienvenidas Cálidas
- **Detección automática** de nuevos miembros (`on_member_join`).
- **Embed estético:** Foto de perfil, contador de miembros y guía inicial.
- **Saludo único con IA:** Redacta una bienvenida original para cada persona.
- **Comandos:** `/config-bienvenida canal #canal`, `/probar-bienvenida`.

---

### 🛡️ 4. Escudo Anti-Spam Amigable
- Detecta ráfagas (flood), mensajes repetidos idénticos, mayúsculas sostenidas y menciones masivas.
- Responde con avisos de advertencia amigables y con humor que se auto-eliminan a los 12 segundos para no ensuciar el chat.
- Notifica al staff si un usuario insiste tras 3 advertencias.
- **Comando:** `/config-antispam activar [True/False]`.

---

### 📅 5. Agenda Comunitaria & Briefing Matutino
- **Briefing matutino automático:** Cada mañana a las 8:00 AM (configurable), publica en el general el saludo con IA y las metas del día.
- **Comandos:** `/plan-agregar`, `/plan-hoy`, `/config-plan-diario`, `/plan-diario-enviar`.

---

## 📖 Directorio Completo de Comandos Slash (`/`)

### ⏰ Recordatorios & Tareas Delegadas
| Comando | Descripción |
|---|---|
| `/recordar [usuario] [tarea] [cada_horas] [por_md]` | Asigna una tarea a un usuario con recordatorio periódico (ej. cada 2 horas). |
| `/recordatorios-activos` | Consulta todas las tareas y recordatorios periódicos activos en el servidor. |
| `/tarea-lista [id]` | Marca una tarea periódica como completada y detiene los avisos. |
| `/tarea-cancelar [id]` | Cancela un recordatorio periódico activo. |

### 🤖 Comunidad & Inteligencia Artificial
| Comando | Descripción |
|---|---|
| `@MiniJefe [mensaje]` | Menciona al bot para charlar libremente en cualquier canal. |
| `/hablar [mensaje]` | Conversa con la IA de MiniJefe mediante comando slash. |
| `/personalidad [estilo]` | *(Admin)* Cambia la actitud: `amigable`, `jefe_motivador`, `programador`, `tranquilo`. |
| `/olvidar-charla` | Reinicia la memoria de conversación en el canal actual. |

### 👋 Bienvenidas & Moderación
| Comando | Descripción |
|---|---|
| `/config-bienvenida [canal]` | *(Admin)* Establece el canal de bienvenida para nuevos miembros. |
| `/probar-bienvenida` | *(Admin)* Simula una bienvenida contigo mismo para previsualizar. |
| `/config-antispam [activar]` | *(Admin)* Enciende (`True`) o apaga (`False`) el escudo anti-spam. |

### 📅 Agenda Diaria & Administración
| Comando | Descripción |
|---|---|
| `/plan-agregar [actividad] [hora]` | Agrega una actividad a la agenda de la comunidad para hoy. |
| `/plan-hoy` | Muestra el tablero interactivo de actividades del día. |
| `/plan-diario-enviar` | *(Admin)* Envía de inmediato el resumen matutino para probarlo. |
| `/config-plan-diario [canal] [hora]` | *(Admin)* Configura el canal y hora (0-23) para la publicación diaria. |
| `/config ver` | *(Admin)* Visualiza el panel general de configuración del servidor. |

---

## 🔒 Seguridad y Git

El archivo `.env` que almacena tus credenciales (`DISCORD_TOKEN`, `GEMINI_API_KEY`) se encuentra registrado en `.gitignore` y **NUNCA** se sube a GitHub.
