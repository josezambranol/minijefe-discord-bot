# 🤖 MiniJefe — Bot Comunitario para Desarrolladores (24/7)

![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.14-blue?logo=python)
![Discord.py](https://img.shields.io/badge/Discord.py-v2.7-5865F2?logo=discord)
![AI Powered](https://img.shields.io/badge/AI-Google%20Gemini-orange?logo=google)
![Image Gen](https://img.shields.io/badge/Image%20Gen-Pillow%2012-brightgreen?logo=pillow)
![Hosted](https://img.shields.io/badge/Hosted%20on-Render%20%7C%20Local-46E3B7?logo=render)
![Timezone](https://img.shields.io/badge/Timezone-America%2FBogota%20(12h)-orange)

**MiniJefe** es la mascota inteligente y mano derecha de la comunidad de desarrolladores fundada y liderada por **Jordy** (la máxima autoridad del servidor, a quien MiniJefe llama con respeto como *"Jefe"*). 

Equipado con la API de **Google Gemini** y un motor gráfico con **Pillow**, MiniJefe cobra vida en el chat, recibe a los nuevos miembros con tarjetas personalizadas de programación, administra roles en lote sin latencia, modera el spam de forma amigable, organiza la agenda diaria y permite a Jordy y al Staff delegar tareas a cualquier miembro con **recordatorios periódicos automáticos** (cada 30 min, 1 hora, 2 horas, etc.) hasta que se completen.

---

## 🌟 Funcionalidades Principales

### 🎭 1. Selector de Roles de Alta Velocidad (Sin Latencia)
- **Menús desplegables (`Select Menus`) interactivos y por categorías:**
  - 💼 **Especialidades:** Frontend, Backend, Fullstack, Mobile, DevOps, UI/UX, Data & IA, QA.
  - 💻 **Lenguajes:** Java, Python, JavaScript/TypeScript, C/C++, C#, Rust, Go, PHP.
  - 🔔 **Notificaciones:** Anuncios, Proyectos & Colaboración, Eventos & Talleres.
- **Respuesta instantánea (<100ms):** Procesa selecciones por lote en memoria, eliminando la latencia y los bloqueos típicos de los bots de reacciones.
- **Vistas Persistentes:** Siguen funcionando incluso después de que el bot se reinicie o se actualice.
- **Comandos:**
  - `/panel-roles`: Publica el panel interactivo en el canal oficial de `#roles`.
  - `/crear-roles-default`: Crea automáticamente en Discord los roles dev que falten con sus colores correspondientes.

---

### 🎨 2. Tarjetas de Bienvenida Gráficas (Estilo Dev)
- **Generación dinámica de imágenes con Pillow:**
  - Renderiza una tarjeta de alta resolución (960x360 px) con fondo moderno de código y terminal.
  - Recorta el avatar del nuevo usuario en un círculo perfecto con anillo neón brillante.
  - Incluye el nombre, número de miembro oficial y un saludo personalizado con IA.
- **Comandos:**
  - `/config-bienvenida canal #canal`: Establece el canal de bienvenida.
  - `/probar-bienvenida`: Simula una bienvenida contigo mismo para previsualizar la tarjeta gráfica.

---

### 📜 3. Recursos de Comunidad y Plantillas
- **Reglamento adaptado a programadores:** Publica directrices claras sobre convivencia, formato de código (no fotos al monitor), no spam de DMs y sanciones escalonadas.
- **Comandos oficiales:**
  - `/publicar-reglas [canal]`: Publica el reglamento oficial en `#reglas`.
  - `/plantilla-proyecto`: Muestra o publica el formato estructurado para el foro `#proyectos-colaboracion`.
  - `/plantilla-roadmap`: Muestra o publica la plantilla de ruta de estudio para `#roadmaps-aprendizaje`.
  - `/plantilla-presentacion`: Muestra o publica el formato de presentación para `#presentaciones`.

---

### ⏰ 4. Recordatorios Periódicos y Tareas Delegadas
Permite a **Jordy (el Jefe)** y al Staff asignar tareas a cualquier miembro con intervalos personalizados:
- **Por chat en lenguaje natural:**
  > `@MiniJefe recuérdale a @usuario subir el informe cada 2 horas`  
  > MiniJefe confirma: *"¡A la orden, Jefe Jordy! 🫡 Recordatorio Registrado..."*
- **Por comando slash:**
  > `/recordar usuario:@pepito tarea:Optimizar queries de PostgreSQL cada_horas:2 por_md:True`
- **Botón `[✅ Marcar como Listo]`:** Completa la tarea y apaga los avisos automáticamente.
- **Botón `[🛑 Cancelar]`:** Exclusivo para Jordy, Staff o el creador de la tarea.
- **Gestión:** `/recordatorios-activos`, `/tarea-lista [id]`, `/tarea-cancelar [id]`.

---

### 🧠 5. Inteligencia Artificial (Gemini) y Charla Viva
- **Mención directa:** Menciona a `@MiniJefe` para charlar, pedir tips de código o bromear.
- Si lo menciona **Jordy**, el bot le responde con máxima lealtad como su Jefe.
- Si le preguntan por la jerarquía del servidor, tiene claro que Jordy es el fundador y líder absoluto (y que Jote no es el dueño).
- **Personalidades:** `/personalidad [amigable | jefe_motivador | programador | tranquilo]`.
- **Comando:** `/hablar [mensaje]`.

---

### 🛡️ 6. Escudo Anti-Spam y Limpieza
- Detecta ráfagas (flood), mensajes idénticos repetidos, mayúsculas sostenidas y menciones masivas.
- Responde con avisos amigables que se auto-eliminan a los 12 segundos.
- **Comandos:**
  - `/limpiar cantidad:10 usuario:@usuario`: Purga mensajes del canal.
  - `@MiniJefe borra 5 mensajes`: Orden rápida por chat para moderadores.
  - `/config-antispam activar:True`: Activa o desactiva la protección.

---

### 📅 7. Agenda Comunitaria & Briefing Matutino
- Cada mañana publica un briefing con IA con saludo motivador y retos de programación.
- **Comandos:** `/plan-agregar`, `/plan-hoy`, `/config-plan-diario`.

---

## 🚀 Despliegue y Ejecución

### Ejecución Local en Windows
```powershell
.\iniciar_bot.bat
```
O bien:
```powershell
.\.venv\Scripts\python bot.py
```

### Ejecutar Pruebas Unitarias
```powershell
.\.venv\Scripts\python test_bot.py
```

### Despliegue en Render.com (24/7)
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python bot.py`
- **Variables de Entorno (Environment Variables):**
  - `DISCORD_TOKEN`: Token de Discord Developer Portal
  - `GEMINI_API_KEY`: API Key de Google AI Studio
  - `PORT`: 8080 (servidor web interno de salud incluido)
