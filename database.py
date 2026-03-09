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
            due_date TEXT
        )
    ''')
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

def get_all_subjects():
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, teacher, room FROM subjects")
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

def add_task(title, description, due_date):
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title, description, due_date) VALUES (?, ?, ?)",
                   (title, description, due_date))
    conn.commit()
    conn.close()

def get_all_tasks():
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, due_date FROM tasks ORDER BY due_date ASC")
    data = cursor.fetchall()
    conn.close()
    return data

def delete_task(task_id):
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def update_task(task_id, title, description, due_date):
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks 
        SET title=?, description=?, due_date=? 
        WHERE id=?
    """, (title, description, due_date, task_id))
    conn.commit()
    conn.close()

def get_task_details(task_id):
    conn = sqlite3.connect('study_planner.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    data = cursor.fetchone()
    conn.close()
    return data