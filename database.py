import sqlite3


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
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
    ''')

    # Пытаемся добавить колонку subject_id, если её нет (для обновления старых БД)
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN subject_id INTEGER DEFAULT NULL")
    except sqlite3.OperationalError:
        pass  # Колонка уже существует

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
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO subjects (name, teacher, room, description) VALUES (?, ?, ?, ?)",
                   (name, teacher, room, description))
    conn.commit()
    conn.close()


def get_all_subjects(sort_by='name', reverse=False):
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
        # Меняем ASC на DESC в строке
        order_clause = order_clause.replace("ASC", "DESC")

    cursor.execute(f"SELECT id, name, teacher, room FROM subjects ORDER BY {order_clause}")
    data = cursor.fetchall()
    conn.close()
    return data


def delete_subject(subject_id):
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
    conn.commit()
    conn.close()


def update_subject(subject_id, name, teacher, room, description):
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE subjects 
        SET name=?, teacher=?, room=?, description=? 
        WHERE id=?
    """, (name, teacher, room, description, subject_id))
    conn.commit()
    conn.close()


def get_subject_details(subject_id):
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,))
    data = cursor.fetchone()
    conn.close()
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


# --- Обновленные функции задач ---

def add_task(title, description, due_date, subject_id):
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title, description, due_date, subject_id) VALUES (?, ?, ?, ?)",
                   (title, description, due_date, subject_id))
    conn.commit()
    conn.close()


def get_all_tasks(sort_by='due_date', reverse=False):
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()

    # Определяем сортировку
    order_clause = "t.due_date ASC"  # По умолчанию по дате
    if sort_by == 'due_date':
        order_clause = "t.due_date ASC"
    elif sort_by == 'subject':
        order_clause = "s.name ASC"  # Сортировка по названию предмета
    elif sort_by == 'title':
        order_clause = "t.title ASC"  # Сортировка по названию задачи

    if reverse:
        order_clause = order_clause.replace("ASC", "DESC")

    query = f"""
        SELECT t.id, t.title, t.due_date, s.name 
        FROM tasks t 
        LEFT JOIN subjects s ON t.subject_id = s.id 
        ORDER BY {order_clause}
    """

    cursor.execute(query)
    data = cursor.fetchall()
    conn.close()
    return data


def delete_task(task_id):
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def update_task(task_id, title, description, due_date, subject_id):
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks 
        SET title=?, description=?, due_date=?, subject_id=? 
        WHERE id=?
    """, (title, description, due_date, subject_id, task_id))
    conn.commit()
    conn.close()


def get_task_details(task_id):
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    data = cursor.fetchone()
    conn.close()
    return data