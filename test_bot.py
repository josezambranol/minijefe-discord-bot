import asyncio
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from database import (
    init_db,
    add_periodic_reminder,
    get_active_periodic_reminders,
    complete_periodic_reminder,
    get_guild_settings,
    update_guild_setting,
    add_daily_plan,
    get_daily_plans_for_date,
    log_bot_activity,
    get_activities_since,
    get_activity_stats_since
)
from utils.reporting import ACTION_STYLES
from utils.image_generator import generate_welcome_card
from utils.embeds import (
    create_server_rules_embeds,
    create_project_template_embed,
    create_roadmap_template_embed,
    create_presentation_template_embed,
    create_roles_panel_embed
)
from utils.ai_service import get_gemini_api_key

async def run_tests():
    print("=" * 60)
    print("🤖 PRUEBAS UNITARIAS DE MINIJEFE — SUITE DE VALIDACIÓN")
    print("=" * 60)

    # 1. Base de datos SQLite
    print("\n[1/5] Inicializando y verificando base de datos y auditoría...")
    await init_db()
    rem_id = await add_periodic_reminder(
        guild_id=123456789,
        channel_id=987654321,
        creator_id=710931815271235645,
        assigned_user_id=111222333,
        title="Test: Revisar endpoints de la API",
        interval_minutes=60,
        send_dm=0
    )
    assert rem_id > 0, "Fallo al insertar recordatorio periódico"
    active = await get_active_periodic_reminders(123456789)
    assert any(r["id"] == rem_id for r in active), "No se encontró el recordatorio activo"
    await complete_periodic_reminder(rem_id)

    # Probar registro de actividad (#reportes)
    log_id = await log_bot_activity(
        guild_id=123456789,
        action_type="setup",
        title="Test de Auditoría",
        description="Verificación del sistema de reportes",
        user_id=710931815271235645
    )
    assert log_id > 0, "Fallo al registrar actividad en bot_activity_logs"
    recent = await get_activities_since(123456789, "2000-01-01T00:00:00")
    assert any(a["id"] == log_id for a in recent), "No se encontró la actividad en get_activities_since"
    stats = await get_activity_stats_since(123456789, "2000-01-01T00:00:00")
    assert stats.get("setup", 0) > 0, "Fallo en conteo de estadísticas por acción"
    print("  ✅ Base de datos SQLite, Auditoría y Recordatorios Periódicos: OK")

    # 2. Generador gráfico de tarjetas de bienvenida (Pillow)
    print("\n[2/5] Probando generador de tarjetas de bienvenida...")
    card_buf = await generate_welcome_card(
        username="JordyDev",
        member_count=142,
        avatar_url=None
    )
    assert len(card_buf.getvalue()) > 10000, "La tarjeta generada está vacía o es muy pequeña"
    print(f"  ✅ Tarjeta de bienvenida generada exitosamente ({len(card_buf.getvalue())} bytes): OK")

    # 3. Embeds de comunidad (Reglas, Proyectos, Roadmaps, Presentaciones, Roles)
    print("\n[3/5] Validando generadores de Embeds...")
    rules = create_server_rules_embeds()
    assert len(rules) == 2, "Deben generarse 2 embeds de reglas"
    assert len(rules[0].fields) + len(rules[1].fields) == 10, "El reglamento debe tener las 10 secciones completas"
    proj = create_project_template_embed()
    assert "PROYECTOS" in proj.title, "Fallo en plantilla de proyectos"
    road = create_roadmap_template_embed()
    assert "ROADMAP" in road.title, "Fallo en plantilla de roadmap"
    pres = create_presentation_template_embed()
    assert "PRESENTACIÓN" in pres.title, "Fallo en plantilla de presentación"
    roles = create_roles_panel_embed()
    assert "ROLES" in roles.title, "Fallo en panel de roles"
    print("  ✅ Todos los embeds y plantillas construidos correctamente (10 secciones de reglas sin ruido): OK")

    # 4. Estado de la IA (Gemini)
    print("\n[4/5] Verificando clave de API de Gemini...")
    key = get_gemini_api_key()
    if key:
        print("  ✅ Clave de Gemini API detectada y configurada: OK")
    else:
        print("  ⚠️ Clave de Gemini API no configurada en .env (se usará fallback offline): OK")

    # 5. Carga de Cogs
    print("\n[5/5] Verificando importación limpia de todos los Cogs...")
    import cogs.periodic_reminders_cog
    import cogs.ai_chat_cog
    import cogs.welcome_cog
    import cogs.roles_cog
    import cogs.community_cog
    import cogs.moderation_cog
    import cogs.daily_plans_cog
    import cogs.admin_cog
    import cogs.reports_cog
    print("  ✅ Todos los 9 cogs se importan limpiamente sin errores de sintaxis: OK")

    print("\n" + "=" * 60)
    print("🎉 ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE! MINIJEFE ESTÁ 100% PULIDO")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_tests())
