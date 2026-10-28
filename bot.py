import os
import sys
import asyncio
import logging
from typing import Optional
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import discord
from discord.ext import commands


from database import init_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cargar variables de entorno (locales y Secret Files de Render)
local_env = os.path.join(BASE_DIR, ".env")
if os.path.exists(local_env):
    load_dotenv(local_env)
else:
    load_dotenv()

if os.path.exists("/etc/secrets/.env"):
    load_dotenv("/etc/secrets/.env")

def get_discord_token() -> Optional[str]:
    """Obtiene el token de Discord desde .env, variables de entorno o Secret Files de Render."""
    token = os.getenv("DISCORD_TOKEN")
    if token and token != "TU_TOKEN_DE_DISCORD_AQUI":
        return token.strip()
    if os.path.isdir("/etc/secrets"):
        for fname in os.listdir("/etc/secrets"):
            if "DISCORD" in fname.upper() or "TOKEN" in fname.upper():
                try:
                    with open(os.path.join("/etc/secrets", fname), "r", encoding="utf-8") as f:
                        val = f.read().strip()
                        if val and len(val) > 30 and not val.startswith("#"):
                            return val
                except Exception:
                    pass
    return token

TOKEN = get_discord_token()

# Configuración de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("TaskBot")

# Configuración de intents de Discord
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class TaskBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        # 1. Inicializar la base de datos
        logger.info("Inicializando base de datos SQLite...")
        await init_db()
        logger.info("Base de datos inicializada correctamente.")

        # 2. Cargar extensiones / Cogs optimizados para el servidor comunitario
        extensions = [
            "cogs.periodic_reminders_cog",
            "cogs.ai_chat_cog",
            "cogs.welcome_cog",
            "cogs.roles_cog",
            "cogs.community_cog",
            "cogs.moderation_cog",
            "cogs.daily_plans_cog",
            "cogs.admin_cog"
        ]

        for ext in extensions:
            try:
                await self.load_extension(ext)
                logger.info(f"Cog cargado exitosamente: {ext}")
            except Exception as e:
                logger.error(f"Error al cargar cog {ext}: {e}", exc_info=True)

        # 3. Registrar vistas persistentes para que sobrevivan a reinicios
        try:
            from cogs.roles_cog import RolesPanelView
            self.add_view(RolesPanelView())
            logger.info("Vista persistente de Roles registrada con éxito.")
        except Exception as e:
            logger.error(f"Error al registrar vista de Roles: {e}")

        # 4. Sincronizar comandos slash (/)
        logger.info("Sincronizando árbol de comandos slash con Discord...")
        try:
            synced = await self.tree.sync()
            logger.info(f"¡Sincronizados {len(synced)} comandos de aplicación exitosamente!")
        except Exception as e:
            logger.error(f"Error al sincronizar comandos: {e}")

    async def on_ready(self):
        from utils.ai_service import get_gemini_api_key
        has_gemini = "CONECTADA ✅" if get_gemini_api_key() else "NO DETECTADA ❌ (Configura GEMINI_API_KEY)"

        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"🤖 Bot conectado como: {self.user.name} ({self.user.id})")
        logger.info(f"🌐 Servidores conectados: {len(self.guilds)}")
        logger.info(f"🔑 Gemini IA Status: {has_gemini}")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="la comunidad dev | @MiniJefe o /hablar"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)




    async def on_tree_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Manejador global de errores para comandos slash."""
        if isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message(
                "🚫 **No tienes permisos suficientes** para ejecutar este comando (se requiere Administrador).",
                ephemeral=True
            )
        elif isinstance(error, discord.app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ Este comando está en enfriamiento. Espera {error.retry_after:.1f} segundos.",
                ephemeral=True
            )
        else:
            logger.error(f"Error no controlado en comando {interaction.command.name if interaction.command else 'desconocido'}: {error}", exc_info=True)
            msg = "❌ Ocurrió un error inesperado al procesar tu solicitud. Por favor intenta de nuevo."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)

async def run_web_server():
    """Servidor web ultraligero para mantener activo el bot en plataformas cloud gratuitas (Render, Koyeb, etc.)."""
    from aiohttp import web
    async def handle_ping(request):
        return web.Response(text="🟢 MiniJefe Discord Bot is alive and running 24/7!")

    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 Servidor web de salud iniciado en puerto {port}")

async def async_main():
    if not TOKEN or TOKEN == "TU_TOKEN_DE_DISCORD_AQUI":
        print("\n" + "="*70)
        print(" [!] ERROR: NO SE ENCONTRÓ EL TOKEN DE DISCORD")
        print(" Por favor abre el archivo '.env' y coloca tu DISCORD_TOKEN.")
        print(" Puedes obtenerlo en: https://discord.com/developers/applications")
        print("="*70 + "\n")
        sys.exit(1)

    bot = TaskBot()
    bot.tree.on_error = bot.on_tree_error

    async def run_bot_resilient():
        while True:
            try:
                await bot.start(TOKEN)
            except discord.LoginFailure:
                logger.error("Token de Discord inválido. Verifica la variable DISCORD_TOKEN.")
                break
            except Exception as e:
                logger.warning(f"Conexión con Discord perdida o interrumpida ({e}). Reintentando en 5s...")
                await asyncio.sleep(5)

    # Iniciar servidor web y bot de Discord juntos
    await asyncio.gather(
        run_web_server(),
        run_bot_resilient()
    )

def main():
    try:
        asyncio.run(async_main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot apagado.")

if __name__ == "__main__":
    main()

