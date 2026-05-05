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
        cursor.execute('ALTER TABLE tasks ADD COLUMN completed INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass

    cursor.execute("UPDATE tasks SET status='active' WHERE status IS NULL")
    cursor.execute('UPDATE tasks SET completed=0 WHERE completed IS NULL')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('theme', 'light')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('path', '')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('semester_start', '2025-09-01')")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            day_of_week INTEGER NOT NULL,
            week_type TEXT NOT NULL DEFAULT 'both',
            start_time TEXT NOT NULL,
            end_time TEXT,
            room TEXT,
            lesson_type TEXT,
            group_name TEXT,
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            grade REAL NOT NULL,
            grade_type TEXT DEFAULT 'exam',
            date TEXT,
            semester TEXT,
            weight REAL DEFAULT 1.0,
            description TEXT,
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT DEFAULT 'general',
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    ''')

    conn.commit()
    conn.close()


def add_subject(name, teacher, room, description):
    logger.debug(f'add_subject: name={name}, teacher={teacher}, room={room}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO subjects (name, teacher, room, description) VALUES (?, ?, ?, ?)', (name, teacher, room, description))
        conn.commit()
        logger.info(f'add_subject: id={cursor.lastrowid}')
    except Exception as e:
        logger.error(f'add_subject: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def get_all_subjects(sort_by='name', reverse=False):
    logger.debug(f'get_all_subjects: sort_by={sort_by}, reverse={reverse}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    order_clause = 'name ASC'
    if sort_by == 'name':
        order_clause = 'name ASC'
    elif sort_by == 'teacher':
        order_clause = 'teacher ASC'
    elif sort_by == 'room':
        order_clause = 'room ASC'
    if reverse:
        order_clause = order_clause.replace('ASC', 'DESC')
    cursor.execute(f'SELECT id, name, teacher, room, description FROM subjects ORDER BY {order_clause}')
    data = cursor.fetchall()
    conn.close()
    logger.debug(f'get_all_subjects: {len(data)} records')
    return data


def delete_subject(subject_id):
    logger.debug(f'delete_subject: subject_id={subject_id}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE tasks SET subject_id = NULL WHERE subject_id = ?', (subject_id,))
        cursor.execute('DELETE FROM schedule WHERE subject_id = ?', (subject_id,))
        cursor.execute('DELETE FROM grades WHERE subject_id = ?', (subject_id,))
        cursor.execute('DELETE FROM subjects WHERE id = ?', (subject_id,))
        conn.commit()
        logger.info(f'delete_subject: {subject_id} deleted')
    except Exception as e:
        logger.error(f'delete_subject: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def clear_all_subjects():
    logger.debug('clear_all_subjects')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM schedule')
        cursor.execute('DELETE FROM grades')
        cursor.execute('UPDATE tasks SET subject_id = NULL')
        cursor.execute('DELETE FROM subjects')
        conn.commit()
        logger.info('clear_all_subjects: all deleted')
    except Exception as e:
        logger.error(f'clear_all_subjects: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def update_subject(subject_id, name, teacher, room, description):
    logger.debug(f'update_subject: id={subject_id}, name={name}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE subjects SET name=?, teacher=?, room=?, description=? WHERE id=?', (name, teacher, room, description, subject_id))
        conn.commit()
        logger.info(f'update_subject: {subject_id} updated')
    except Exception as e:
        logger.error(f'update_subject: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def get_subject_details(subject_id):
    logger.debug(f'get_subject_details: subject_id={subject_id}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, teacher, room, description FROM subjects WHERE id = ?', (subject_id,))
    data = cursor.fetchone()
    conn.close()
    logger.debug(f'get_subject_details: {data}')
    return data


def get_setting(key, default=None):
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else default


def save_setting(key, value):
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()


def add_task(title, description, due_date, subject_id):
    logger.debug(f'add_task: title={title}, subject_id={subject_id}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO tasks (title, description, due_date, subject_id, status, completed) VALUES (?, ?, ?, ?, ?, 0)', (title, description, due_date, subject_id, 'active'))
        conn.commit()
        logger.info(f'add_task: id={cursor.lastrowid}')
    except Exception as e:
        logger.error(f'add_task: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def get_all_tasks(sort_by='due_date', reverse=False, status_filter='active'):
    logger.debug(f'get_all_tasks: sort_by={sort_by}, reverse={reverse}, status_filter={status_filter}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    order_clause = 't.due_date ASC'
    if sort_by == 'due_date':
        order_clause = 't.due_date ASC'
    elif sort_by == 'subject':
        order_clause = 's.name ASC'
    elif sort_by == 'title':
        order_clause = 't.title ASC'
    if reverse:
        order_clause = order_clause.replace('ASC', 'DESC')
    where_clause = ''
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
    logger.debug(f'get_all_tasks: {len(data)} tasks')
    return data


def delete_task(task_id):
    logger.debug(f'delete_task: task_id={task_id}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()
        logger.info(f'delete_task: {cursor.rowcount}')
    except Exception as e:
        logger.error(f'delete_task: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def update_task(task_id, title, description, due_date, subject_id, status='active', completed=0):
    logger.debug(f'update_task: id={task_id}, title={title}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE tasks SET title=?, description=?, due_date=?, subject_id=?, status=?, completed=? WHERE id=?', (title, description, due_date, subject_id, status, completed, task_id))
        conn.commit()
        logger.info(f'update_task: {task_id} updated')
    except Exception as e:
        logger.error(f'update_task: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def archive_task(task_id):
    logger.debug(f'archive_task: task_id={task_id}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE tasks SET status='archived' WHERE id = ?", (task_id,))
        conn.commit()
        logger.info(f'archive_task: {task_id}')
    except Exception as e:
        logger.error(f'archive_task: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def restore_task(task_id):
    logger.debug(f'restore_task: task_id={task_id}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE tasks SET status='active' WHERE id = ?", (task_id,))
        conn.commit()
        logger.info(f'restore_task: {task_id}')
    except Exception as e:
        logger.error(f'restore_task: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def toggle_task_completed(task_id, completed):
    logger.debug(f'toggle_task_completed: task_id={task_id}, completed={completed}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE tasks SET completed=? WHERE id = ?', (1 if completed else 0, task_id))
        conn.commit()
        logger.info(f'toggle_task_completed: {task_id}')
    except Exception as e:
        logger.error(f'toggle_task_completed: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def get_task_details(task_id):
    logger.debug(f'get_task_details: task_id={task_id}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    data = cursor.fetchone()
    conn.close()
    logger.debug(f'get_task_details: {data}')
    return data


def global_search(query):
    logger.info(f"global_search: query='{query}'")
    if not query or not query.strip():
        logger.warning('empty query')
        return []
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    results = []
    search_query = query.strip().lower()
    try:
        cursor.execute('SELECT id, name, teacher, room, description FROM subjects')
        all_subjects = cursor.fetchall()
        for row in all_subjects:
            sid, name, teacher, room, description = row
            if (search_query in (name or '').lower() or search_query in (teacher or '').lower() or search_query in (room or '').lower() or search_query in (description or '').lower()):
                results.append((sid, name, 'subject', None))
        cursor.execute('SELECT t.id, t.title, t.description, s.name FROM tasks t LEFT JOIN subjects s ON t.subject_id = s.id')
        all_tasks = cursor.fetchall()
        for row in all_tasks:
            tid, title, description, subject_name = row
            if (search_query in (title or '').lower() or search_query in (description or '').lower()):
                results.append((tid, title, 'task', subject_name))
    except Exception as e:
        logger.error(f'global_search: {e}', exc_info=True)
        raise
    finally:
        conn.close()
    return results


def add_schedule_entry(subject_id, day_of_week, week_type, start_time, end_time, room, lesson_type, group_name):
    logger.debug(f'add_schedule_entry: subject_id={subject_id}, day={day_of_week}, week={week_type}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO schedule (subject_id, day_of_week, week_type, start_time, end_time, room, lesson_type, group_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (subject_id, day_of_week, week_type, start_time, end_time, room, lesson_type, group_name))
        conn.commit()
        logger.info(f'add_schedule_entry: id={cursor.lastrowid}')
        return cursor.lastrowid
    except Exception as e:
        logger.error(f'add_schedule_entry: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def get_schedule(week_type=None, day_of_week=None):
    logger.debug(f'get_schedule: week_type={week_type}, day={day_of_week}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    query = """
        SELECT s.id, s.subject_id, s.day_of_week, s.week_type, s.start_time, s.end_time,
               s.room, s.lesson_type, s.group_name, sub.name, sub.teacher
        FROM schedule s
        JOIN subjects sub ON s.subject_id = sub.id
        WHERE 1=1
    """
    params = []
    if week_type:
        query += " AND (s.week_type = ? OR s.week_type = 'both')"
        params.append(week_type)
    if day_of_week is not None:
        query += ' AND s.day_of_week = ?'
        params.append(day_of_week)
    query += ' ORDER BY s.day_of_week, s.start_time'
    cursor.execute(query, params)
    data = cursor.fetchall()
    conn.close()
    logger.debug(f'get_schedule: {len(data)} entries')
    return data


def get_schedule_by_id(entry_id):
    logger.debug(f'get_schedule_by_id: {entry_id}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.subject_id, s.day_of_week, s.week_type, s.start_time, s.end_time,
               s.room, s.lesson_type, s.group_name, sub.name, sub.teacher
        FROM schedule s
        JOIN subjects sub ON s.subject_id = sub.id
        WHERE s.id = ?
    """, (entry_id,))
    data = cursor.fetchone()
    conn.close()
    return data


def update_schedule_entry(entry_id, subject_id, day_of_week, week_type, start_time, end_time, room, lesson_type, group_name):
    logger.debug(f'update_schedule_entry: id={entry_id}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE schedule SET subject_id=?, day_of_week=?, week_type=?, start_time=?, end_time=?, room=?, lesson_type=?, group_name=? WHERE id=?', (subject_id, day_of_week, week_type, start_time, end_time, room, lesson_type, group_name, entry_id))
        conn.commit()
        logger.info(f'update_schedule_entry: {entry_id}')
    except Exception as e:
        logger.error(f'update_schedule_entry: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_schedule_entry(entry_id):
    logger.debug(f'delete_schedule_entry: {entry_id}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM schedule WHERE id = ?', (entry_id,))
        conn.commit()
        logger.info(f'delete_schedule_entry: {entry_id}')
    except Exception as e:
        logger.error(f'delete_schedule_entry: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def clear_schedule():
    logger.debug('clear_schedule')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM schedule')
        conn.commit()
        logger.info('clear_schedule: all entries deleted')
    except Exception as e:
        logger.error(f'clear_schedule: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def add_grade(subject_id, grade, grade_type, date, semester, weight, description):
    logger.debug(f'add_grade: subject_id={subject_id}, grade={grade}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO grades (subject_id, grade, grade_type, date, semester, weight, description) VALUES (?, ?, ?, ?, ?, ?, ?)', (subject_id, grade, grade_type, date, semester, weight, description))
        conn.commit()
        logger.info(f'add_grade: id={cursor.lastrowid}')
        return cursor.lastrowid
    except Exception as e:
        logger.error(f'add_grade: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def get_all_grades(subject_id=None, semester=None):
    logger.debug(f'get_all_grades: subject_id={subject_id}, semester={semester}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    query = """
        SELECT g.id, g.subject_id, g.grade, g.grade_type, g.date, g.semester, g.weight, g.description, sub.name
        FROM grades g
        JOIN subjects sub ON g.subject_id = sub.id
        WHERE 1=1
    """
    params = []
    if subject_id:
        query += ' AND g.subject_id = ?'
        params.append(subject_id)
    if semester:
        query += ' AND g.semester = ?'
        params.append(semester)
    query += ' ORDER BY g.date DESC, sub.name'
    cursor.execute(query, params)
    data = cursor.fetchall()
    conn.close()
    logger.debug(f'get_all_grades: {len(data)} records')
    return data


def get_grade_by_id(grade_id):
    logger.debug(f'get_grade_by_id: {grade_id}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT g.id, g.subject_id, g.grade, g.grade_type, g.date, g.semester, g.weight, g.description, sub.name
        FROM grades g
        JOIN subjects sub ON g.subject_id = sub.id
        WHERE g.id = ?
    """, (grade_id,))
    data = cursor.fetchone()
    conn.close()
    return data


def update_grade(grade_id, subject_id, grade, grade_type, date, semester, weight, description):
    logger.debug(f'update_grade: id={grade_id}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE grades SET subject_id=?, grade=?, grade_type=?, date=?, semester=?, weight=?, description=? WHERE id=?', (subject_id, grade, grade_type, date, semester, weight, description, grade_id))
        conn.commit()
        logger.info(f'update_grade: {grade_id}')
    except Exception as e:
        logger.error(f'update_grade: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_grade(grade_id):
    logger.debug(f'delete_grade: {grade_id}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM grades WHERE id = ?', (grade_id,))
        conn.commit()
        logger.info(f'delete_grade: {grade_id}')
    except Exception as e:
        logger.error(f'delete_grade: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def get_grade_statistics(subject_id=None, semester=None):
    logger.debug(f'get_grade_statistics: subject_id={subject_id}, semester={semester}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    query = """
        SELECT sub.name, AVG(g.grade) as avg_grade, COUNT(g.id) as count,
               MIN(g.grade) as min_grade, MAX(g.grade) as max_grade,
               SUM(g.grade * g.weight) / SUM(g.weight) as weighted_avg
        FROM grades g
        JOIN subjects sub ON g.subject_id = sub.id
        WHERE 1=1
    """
    params = []
    if subject_id:
        query += ' AND g.subject_id = ?'
        params.append(subject_id)
    if semester:
        query += ' AND g.semester = ?'
        params.append(semester)
    query += ' GROUP BY sub.id, sub.name ORDER BY sub.name'
    cursor.execute(query, params)
    data = cursor.fetchall()
    conn.close()
    return data


def get_semesters():
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT semester FROM grades WHERE semester IS NOT NULL ORDER BY semester')
    data = cursor.fetchall()
    conn.close()
    return [row[0] for row in data if row[0]]


def add_wishlist_item(title, description='', category='general', priority='medium'):
    logger.debug(f'add_wishlist_item: title={title}, priority={priority}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO wishlist (title, description, category, priority) VALUES (?, ?, ?, ?)',
                       (title, description, category, priority))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f'add_wishlist_item: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def get_all_wishlist(sort_by='created_at', reverse=False, status_filter=None, category_filter=None):
    logger.debug(f'get_all_wishlist: sort_by={sort_by}, status={status_filter}, category={category_filter}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    order_map = {
        'created_at': 'created_at DESC',
        'title': 'title ASC',
        'priority': "CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 WHEN 'low' THEN 2 END ASC",
        'status': 'status ASC'
    }
    order_clause = order_map.get(sort_by, 'created_at DESC')
    query = 'SELECT id, title, description, category, priority, status, created_at FROM wishlist WHERE 1=1'
    params = []
    if status_filter and status_filter != 'all':
        query += ' AND status = ?'
        params.append(status_filter)
    if category_filter and category_filter != 'all':
        query += ' AND category = ?'
        params.append(category_filter)
    query += f' ORDER BY {order_clause}'
    cursor.execute(query, params)
    data = cursor.fetchall()
    conn.close()
    return data


def update_wishlist_item(item_id, title, description='', category='general', priority='medium', status='pending'):
    logger.debug(f'update_wishlist_item: id={item_id}, title={title}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE wishlist SET title=?, description=?, category=?, priority=?, status=? WHERE id=?',
                       (title, description, category, priority, status, item_id))
        conn.commit()
    except Exception as e:
        logger.error(f'update_wishlist_item: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_wishlist_item(item_id):
    logger.debug(f'delete_wishlist_item: {item_id}')
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM wishlist WHERE id = ?', (item_id,))
        conn.commit()
    except Exception as e:
        logger.error(f'delete_wishlist_item: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


def get_wishlist_by_id(item_id):
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, description, category, priority, status, created_at FROM wishlist WHERE id = ?', (item_id,))
    data = cursor.fetchone()
    conn.close()
    return data


def get_wishlist_categories():
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT category FROM wishlist ORDER BY category')
    data = cursor.fetchall()
    conn.close()
    return [row[0] for row in data if row[0]]
