# database.py
import sqlite3
import logging

logger = logging.getLogger(__name__)


def init_db():
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            teacher TEXT,
            room TEXT,
            description TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            due_date TEXT,
            subject_id INTEGER DEFAULT NULL,
            status TEXT DEFAULT 'active',
            completed INTEGER DEFAULT 0,
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
    ''')

    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN status TEXT DEFAULT 'active'")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN completed INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    cursor.execute("UPDATE tasks SET status='active' WHERE status IS NULL")
    cursor.execute("UPDATE tasks SET completed=0 WHERE completed IS NULL")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('theme', 'light')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('path', '')")
    conn.commit()
    conn.close()


def add_subject(name, teacher, room, description):
    logger.debug(f"add_subject: name={name}, teacher={teacher}, room={room}")
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO subjects (name, teacher, room, description) VALUES (?, ?, ?, ?)",
                       (name, teacher, room, description))
        conn.commit()
        logger.info(f"add_subject: предмет добавлен, id={cursor.lastrowid}")
    except Exception as e:
        logger.error(f"add_subject: ошибка: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def get_all_subjects(sort_by='name', reverse=False):
    logger.debug(f"get_all_subjects: sort_by={sort_by}, reverse={reverse}")
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()

    order_clause = "name ASC"
    if sort_by == 'name':
        order_clause = "name ASC"
    elif sort_by == 'teacher':
        order_clause = "teacher ASC"
    elif sort_by == 'room':
        order_clause = "room ASC"

    if reverse:
        order_clause = order_clause.replace("ASC", "DESC")

    # Явно указываем порядок полей: id, name, teacher, room, description
    cursor.execute(f"SELECT id, name, teacher, room, description FROM subjects ORDER BY {order_clause}")
    data = cursor.fetchall()
    conn.close()
    logger.debug(f"get_all_subjects: возвращено {len(data)} записей")
    return data


def delete_subject(subject_id):
    """Удаляет предмет и обнуляет subject_id у связанных задач"""
    logger.debug(f"delete_subject: subject_id={subject_id}")
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE tasks SET subject_id = NULL WHERE subject_id = ?", (subject_id,))
        logger.debug(f"delete_subject: обновлено {cursor.rowcount} задач")

        cursor.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
        logger.debug(f"delete_subject: удалено предметов: {cursor.rowcount}")

        conn.commit()
        logger.info(f"delete_subject: предмет {subject_id} успешно удалён")
    except Exception as e:
        logger.error(f"delete_subject: ошибка: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def update_subject(subject_id, name, teacher, room, description):
    logger.debug(f"update_subject: id={subject_id}, name={name}")
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE subjects 
            SET name=?, teacher=?, room=?, description=? 
            WHERE id=?
        """, (name, teacher, room, description, subject_id))
        conn.commit()
        logger.info(f"update_subject: предмет {subject_id} обновлён, изменено строк: {cursor.rowcount}")
    except Exception as e:
        logger.error(f"update_subject: ошибка: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def get_subject_details(subject_id):
    logger.debug(f"get_subject_details: subject_id={subject_id}")
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    # Явно указываем порядок полей для консистентности: id, name, teacher, room, description
    cursor.execute("SELECT id, name, teacher, room, description FROM subjects WHERE id = ?", (subject_id,))
    data = cursor.fetchone()
    conn.close()
    logger.debug(f"get_subject_details: результат={data}")
    return data


def get_setting(key, default=None):
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else default


def save_setting(key, value):
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def add_task(title, description, due_date, subject_id):
    logger.debug(f"add_task: title={title}, subject_id={subject_id}")
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO tasks (title, description, due_date, subject_id, status, completed) VALUES (?, ?, ?, ?, 'active', 0)",
            (title, description, due_date, subject_id))
        conn.commit()
        logger.info(f"add_task: задача добавлена, id={cursor.lastrowid}")
    except Exception as e:
        logger.error(f"add_task: ошибка: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def get_all_tasks(sort_by='due_date', reverse=False, status_filter='active'):
    logger.debug(f"get_all_tasks: sort_by={sort_by}, reverse={reverse}, status_filter={status_filter}")
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()

    order_clause = "t.due_date ASC"
    if sort_by == 'due_date':
        order_clause = "t.due_date ASC"
    elif sort_by == 'subject':
        order_clause = "s.name ASC"
    elif sort_by == 'title':
        order_clause = "t.title ASC"

    if reverse:
        order_clause = order_clause.replace("ASC", "DESC")

    where_clause = ""
    if status_filter and status_filter != 'all':
        where_clause = f" AND t.status = '{status_filter}'"

    query = f"""
        SELECT t.id, t.title, t.due_date, s.name, t.status, t.completed 
        FROM tasks t 
        LEFT JOIN subjects s ON t.subject_id = s.id 
        WHERE 1=1 {where_clause}
        ORDER BY {order_clause}
    """

    cursor.execute(query)
    data = cursor.fetchall()
    conn.close()
    logger.debug(f"get_all_tasks: возвращено {len(data)} задач")
    return data


def delete_task(task_id):
    logger.debug(f"delete_task: task_id={task_id}")
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        logger.info(f"delete_task: удалено задач: {cursor.rowcount}")
    except Exception as e:
        logger.error(f"delete_task: ошибка: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def update_task(task_id, title, description, due_date, subject_id, status='active', completed=0):
    logger.debug(f"update_task: id={task_id}, title={title}, status={status}, completed={completed}")
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE tasks 
            SET title=?, description=?, due_date=?, subject_id=?, status=?, completed=?
            WHERE id=?
        """, (title, description, due_date, subject_id, status, completed, task_id))
        conn.commit()
        logger.info(f"update_task: задача {task_id} обновлена, изменено строк: {cursor.rowcount}")
    except Exception as e:
        logger.error(f"update_task: ошибка: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def archive_task(task_id):
    logger.debug(f"archive_task: task_id={task_id}")
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE tasks SET status='archived' WHERE id = ?", (task_id,))
        conn.commit()
        logger.info(f"archive_task: задача {task_id} архивирована")
    except Exception as e:
        logger.error(f"archive_task: ошибка: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def restore_task(task_id):
    logger.debug(f"restore_task: task_id={task_id}")
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE tasks SET status='active' WHERE id = ?", (task_id,))
        conn.commit()
        logger.info(f"restore_task: задача {task_id} восстановлена")
    except Exception as e:
        logger.error(f"restore_task: ошибка: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def toggle_task_completed(task_id, completed):
    logger.debug(f"toggle_task_completed: task_id={task_id}, completed={completed}")
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE tasks SET completed=? WHERE id = ?", (1 if completed else 0, task_id))
        conn.commit()
        logger.info(f"toggle_task_completed: задача {task_id}, completed={completed}")
    except Exception as e:
        logger.error(f"toggle_task_completed: ошибка: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def get_task_details(task_id):
    logger.debug(f"get_task_details: task_id={task_id}")
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    data = cursor.fetchone()
    conn.close()
    logger.debug(f"get_task_details: результат={data}")
    return data


def global_search(query):
    """Регистро-независимый поиск по предметам и задачам"""
    logger.info(f"=== ПОИСК: query='{query}' ===")

    if not query or not query.strip():
        logger.warning("Пустой запрос")
        return []

    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    results = []

    # Приводим запрос к нижнему регистру Python (работает с русским)
    search_query = query.strip().lower()

    logger.info(f"Поисковый запрос (lower): '{search_query}'")

    try:
        # Проверим что вообще есть в таблице subjects
        cursor.execute("SELECT id, name, teacher, room, description FROM subjects")
        all_subjects = cursor.fetchall()
        logger.info(f"Всего предметов: {len(all_subjects)}")
        for s in all_subjects:
            logger.info(f"  Предмет {s[0]}: name='{s[1]}', teacher='{s[2]}', room='{s[3]}', desc='{s[4]}'")

        # Ручная проверка для предметов (Python lower() работает с русским)
        logger.info("Ищем в предметах через Python...")
        subjects_results = []
        for row in all_subjects:
            sid, name, teacher, room, description = row
            # Проверяем каждое поле через Python lower()
            if (search_query in (name or '').lower() or
                    search_query in (teacher or '').lower() or
                    search_query in (room or '').lower() or
                    search_query in (description or '').lower()):
                subjects_results.append((sid, name, 'subject', None))
                logger.info(f"  Найден предмет: {name}")

        logger.info(f"Найдено предметов: {len(subjects_results)}")
        results.extend(subjects_results)

        # Проверим задачи
        cursor.execute(
            "SELECT t.id, t.title, t.description, s.name FROM tasks t LEFT JOIN subjects s ON t.subject_id = s.id")
        all_tasks = cursor.fetchall()
        logger.info(f"Всего задач: {len(all_tasks)}")
        for t in all_tasks:
            logger.info(f"  Задача {t[0]}: title='{t[1]}', desc='{t[2]}', subject='{t[3]}'")

        # Ручная проверка для задач
        logger.info("Ищем в задачах через Python...")
        tasks_results = []
        for row in all_tasks:
            tid, title, description, subject_name = row
            if (search_query in (title or '').lower() or
                    search_query in (description or '').lower()):
                tasks_results.append((tid, title, 'task', subject_name))
                logger.info(f"  Найдена задача: {title}")

        logger.info(f"Найдено задач: {len(tasks_results)}")
        results.extend(tasks_results)

        logger.info(f"=== ВСЕГО РЕЗУЛЬТАТОВ: {len(results)} ===")

    except Exception as e:
        logger.error(f"ОШИБКА ПОИСКА: {e}", exc_info=True)
        raise
    finally:
        conn.close()

    return results