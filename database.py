import aiosqlite
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "tasks.db")

async def init_db():
    """Inicializa las tablas de la base de datos si no existen."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                creator_id INTEGER NOT NULL,
                assigned_user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                due_date TEXT NOT NULL,
                due_date_text TEXT,
                status TEXT DEFAULT 'pending',
                reminder_time TEXT DEFAULT '09:00',
                last_reminded_date TEXT DEFAULT '',
                overdue_alert_sent INTEGER DEFAULT 0,
                grade_notes TEXT,
                completed_by_id INTEGER,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                reminder_channel_id INTEGER,
                timezone TEXT DEFAULT 'America/Bogota',
                default_reminder_hour INTEGER DEFAULT 9,
                send_dm INTEGER DEFAULT 1
            )
        """)

        # Tabla para evitar spam y mensajes duplicados
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sent_notifications (
                notification_key TEXT PRIMARY KEY,
                sent_at TEXT NOT NULL
            )
        """)
        
        # Índices para consultas rápidas
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_guild_status ON tasks(guild_id, status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_user_id, status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date)")
        
        # Migraciones automáticas de columnas
        migrations = [
            "ALTER TABLE tasks ADD COLUMN overdue_alert_sent INTEGER DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN due_date_text TEXT",
            "ALTER TABLE tasks ADD COLUMN grade_notes TEXT",
            "ALTER TABLE tasks ADD COLUMN completed_by_id INTEGER"
        ]
        for mig in migrations:
            try:
                await db.execute(mig)
            except Exception:
                pass

        await db.commit()


async def has_notification_been_sent(notification_key: str) -> bool:
    """Verifica si una notificación específica ya fue enviada (Anti-Spam)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM sent_notifications WHERE notification_key = ?", (notification_key,)) as cursor:
            row = await cursor.fetchone()
            return row is not None

async def record_notification_sent(notification_key: str) -> bool:
    """Registra una clave de notificación para no volver a repetirla."""
    now_iso = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO sent_notifications (notification_key, sent_at) VALUES (?, ?)",
            (notification_key, now_iso)
        )
        await db.commit()
        return True

async def mark_overdue_alert_sent(task_id: int) -> bool:
    """Marca que la alerta roja de vencimiento ya fue enviada para esta tarea."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tasks SET overdue_alert_sent = 1 WHERE id = ?", (task_id,))
        await db.commit()
        return True


async def create_task(
    guild_id: int,
    channel_id: int,
    creator_id: int,
    assigned_user_id: int,
    title: str,
    description: Optional[str],
    due_date_iso: str,
    due_date_text: Optional[str] = None,
    reminder_time: str = "09:00"
) -> int:
    """Crea una nueva tarea y retorna su ID."""
    created_at_iso = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO tasks (
                guild_id, channel_id, creator_id, assigned_user_id,
                title, description, due_date, due_date_text, status,
                reminder_time, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """, (
            guild_id, channel_id, creator_id, assigned_user_id,
            title, description or "", due_date_iso, due_date_text or "",
            reminder_time, created_at_iso
        ))
        await db.commit()
        return cursor.lastrowid

async def get_task(task_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene una tarea por su ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_tasks(
    guild_id: Optional[int] = None,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Obtiene una lista de tareas con filtros opcionales."""
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if guild_id is not None:
        query += " AND guild_id = ?"
        params.append(guild_id)
    if user_id is not None:
        query += " AND assigned_user_id = ?"
        params.append(user_id)
    if status is not None:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY due_date ASC LIMIT ?"
    params.append(limit)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, tuple(params)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_overdue_tasks(guild_id: Optional[int] = None, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Obtiene todas las tareas con estado 'overdue' o vencidas."""
    return await get_tasks(guild_id=guild_id, user_id=user_id, status='overdue')

async def get_pending_tasks_due_for_overdue_check(now_iso: str) -> List[Dict[str, Any]]:
    """Obtiene tareas que siguen en estado 'pending' pero cuya fecha límite ya pasó."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM tasks 
            WHERE status = 'pending' AND due_date <= ?
        """, (now_iso,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def mark_task_overdue(task_id: int) -> bool:
    """Marca una tarea como vencida ('overdue')."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tasks SET status = 'overdue' WHERE id = ?", (task_id,))
        await db.commit()
        return True

async def mark_task_completed(task_id: int, completed_by_id: Optional[int] = None, grade_notes: Optional[str] = None) -> bool:
    """Marca una tarea como completada/calificada por cualquier usuario y silencia recordatorios."""
    completed_at = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE tasks 
            SET status = 'completed', completed_at = ?, completed_by_id = ?, grade_notes = ?
            WHERE id = ?
        """, (completed_at, completed_by_id, grade_notes, task_id))
        await db.commit()
        return cursor.rowcount > 0


async def postpone_task(task_id: int, new_due_date_iso: str) -> bool:
    """Pospone una tarea cambiando su fecha límite y restaurando estado a 'pending'."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE tasks 
            SET due_date = ?, status = 'pending' 
            WHERE id = ?
        """, (new_due_date_iso, task_id))
        await db.commit()
        return cursor.rowcount > 0

async def delete_task(task_id: int) -> bool:
    """Elimina una tarea permanentemente."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await db.commit()
        return cursor.rowcount > 0

async def update_last_reminded(task_id: int, today_str: str) -> bool:
    """Actualiza la fecha del último recordatorio diario enviado."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tasks SET last_reminded_date = ? WHERE id = ?", (today_str, task_id))
        await db.commit()
        return True

async def get_all_active_tasks() -> List[Dict[str, Any]]:
    """Obtiene todas las tareas pendientes de todos los servidores para el ciclo de recordatorios."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tasks WHERE status = 'pending'") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_guild_settings(guild_id: int) -> Dict[str, Any]:
    """Obtiene la configuración de un servidor (o los valores por defecto)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            # Insertar configuración por defecto si no existe
            default_tz = os.getenv("DEFAULT_TIMEZONE", "America/Bogota")
            await db.execute("""
                INSERT OR IGNORE INTO guild_settings (guild_id, timezone, default_reminder_hour, send_dm)
                VALUES (?, ?, 9, 1)
            """, (guild_id, default_tz))
            await db.commit()
            return {
                "guild_id": guild_id,
                "reminder_channel_id": None,
                "timezone": default_tz,
                "default_reminder_hour": 9,
                "send_dm": 1
            }

async def update_guild_setting(guild_id: int, key: str, value: Any) -> bool:
    """Actualiza una propiedad en la configuración del servidor."""
    # Asegurar que el registro exista
    await get_guild_settings(guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE guild_settings SET {key} = ? WHERE guild_id = ?", (value, guild_id))
        await db.commit()
        return True

async def get_task_stats(guild_id: int, user_id: Optional[int] = None) -> Dict[str, int]:
    """Obtiene estadísticas de tareas (total, pendientes, vencidas, completadas)."""
    base_where = "WHERE guild_id = ?"
    params = [guild_id]
    if user_id:
        base_where += " AND assigned_user_id = ?"
        params.append(user_id)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'overdue' THEN 1 ELSE 0 END) as overdue,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
            FROM tasks {base_where}
        """, tuple(params)) as cursor:
            row = await cursor.fetchone()
            return {
                "total": row[0] or 0,
                "pending": row[1] or 0,
                "overdue": row[2] or 0,
                "completed": row[3] or 0
            }
