import asyncio
import os
import sys
from datetime import datetime, timedelta
import pytz

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# Test Database and Date Parser
from database import (
    init_db, create_task, get_task, get_tasks, get_overdue_tasks,
    mark_task_completed, mark_task_overdue, postpone_task, delete_task,
    get_guild_settings, update_guild_setting, get_task_stats
)
from utils.date_parser import parse_task_date, format_time_left, format_date_display

async def test_database_and_parser():
    print("Testing date parser...")
    tz = "America/Bogota"
    
    # Test 1: Date parser tests
    d1, err1, t1 = parse_task_date("mañana 15:00", tz)
    assert err1 is None, f"Failed parse 'mañana 15:00': {err1}"
    assert d1 is not None
    print(f"  [OK] 'mañana 15:00' -> {d1} ({t1})")

    d2, err2, t2 = parse_task_date("en 3 dias", tz)
    assert err2 is None, f"Failed parse 'en 3 dias': {err2}"
    assert d2 is not None
    print(f"  [OK] 'en 3 dias' -> {d2} ({t2})")

    d3, err3, t3 = parse_task_date("30/08/2026 18:30", tz)
    assert err3 is None, f"Failed parse '30/08/2026 18:30': {err3}"
    assert d3.day == 30 and d3.month == 8 and d3.year == 2026
    print(f"  [OK] '30/08/2026 18:30' -> {d3} ({t3})")

    d4, err4, t4 = parse_task_date("15 de septiembre 6:00 pm", tz)
    assert err4 is None
    print(f"  [OK] '15 de septiembre 6:00 pm' -> {d4} ({t4})")

    d5, err5, t5 = parse_task_date("a finales de mes", tz)
    assert err5 is None
    print(f"  [OK] 'a finales de mes' -> {d5} ({t5})")

    d6, err6, t6 = parse_task_date("por definir", tz)
    assert err6 is None
    print(f"  [OK] 'por definir' -> {d6} ({t6})")


    time_str, urgency, _ = format_time_left((datetime.now(pytz.timezone(tz)) + timedelta(days=2)).isoformat(), tz)
    print(f"  [OK] format_time_left (+2 days) -> {time_str} | Urgencia: {urgency}")

    time_str_overdue, urgency_od, _ = format_time_left((datetime.now(pytz.timezone(tz)) - timedelta(days=1)).isoformat(), tz)
    print(f"  [OK] format_time_left (-1 day) -> {time_str_overdue} | Urgencia: {urgency_od}")
    assert urgency_od == "OVERDUE"

    print("\nTesting Database CRUD operations...")
    await init_db()

    # Create task
    future_date = (datetime.now(pytz.timezone(tz)) + timedelta(days=5)).isoformat()
    task_id = await create_task(
        guild_id=123456789,
        channel_id=987654321,
        creator_id=111,
        assigned_user_id=222,
        title="Crear reporte de métricas",
        description="Incluir gráficas de retención y DAU",
        due_date_iso=future_date,
        reminder_time="09:30"
    )
    print(f"  [OK] Created task with ID: {task_id}")

    # Read task
    task = await get_task(task_id)
    assert task is not None
    assert task["title"] == "Crear reporte de métricas"
    assert task["assigned_user_id"] == 222
    print(f"  [OK] Fetched task #{task_id}: {task['title']}")

    # Guild settings
    settings = await get_guild_settings(123456789)
    assert settings["timezone"] == "America/Bogota"
    await update_guild_setting(123456789, "reminder_channel_id", 555)
    updated_settings = await get_guild_settings(123456789)
    assert updated_settings["reminder_channel_id"] == 555
    print(f"  [OK] Guild settings updated correctly: {updated_settings}")

    # Mark completed
    await mark_task_completed(task_id)
    task_done = await get_task(task_id)
    assert task_done["status"] == "completed"
    print(f"  [OK] Marked task as completed.")

    # Postpone
    new_due = (datetime.now(pytz.timezone(tz)) + timedelta(days=7)).isoformat()
    await postpone_task(task_id, new_due)
    task_postponed = await get_task(task_id)
    assert task_postponed["status"] == "pending"
    assert task_postponed["due_date"] == new_due
    print(f"  [OK] Postponed task and restored pending status.")

    # Mark overdue
    await mark_task_overdue(task_id)
    overdue_list = await get_overdue_tasks(guild_id=123456789)
    assert any(t["id"] == task_id for t in overdue_list)
    print(f"  [OK] Overdue tasks list contains task #{task_id}.")

    # Stats
    stats = await get_task_stats(123456789)
    print(f"  [OK] Stats: {stats}")

    # Delete
    await delete_task(task_id)
    task_deleted = await get_task(task_id)
    assert task_deleted is None
    print(f"  [OK] Deleted task #{task_id} successfully.")

    print("\nAll database & parsing tests passed successfully! ✨\n")

if __name__ == "__main__":
    asyncio.run(test_database_and_parser())
