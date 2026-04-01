import sys
import os
import database
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QWidget,
                             QVBoxLayout, QHBoxLayout, QListWidget, QLabel,
                             QLineEdit, QPushButton, QTextEdit, QCalendarWidget,
                             QComboBox, QFileDialog, QInputDialog, QFrame, QDialog, QDialogButtonBox, QFormLayout)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QTextCharFormat, QColor, QBrush, QFont, QTextCursor, QTextBlockFormat
from ui_py.ui_main import Ui_MainWindow


# --- Диалог для добавления/редактирования задачи ---
class TaskDialog(QDialog):
    def __init__(self, parent=None, subjects=None, task_data=None):
        super().__init__(parent)
        self.setWindowTitle("Задача")
        self.resize(300, 200)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.input_title = QLineEdit()
        self.input_date = QLineEdit()
        self.input_date.setPlaceholderText("ГГГГ-ММ-ДД")
        self.combo_subject = QComboBox()
        self.input_desc = QLineEdit()

        # Заполняем предметы
        self.subjects_map = {}  # map name -> id
        if subjects:
            for sub in subjects:
                self.combo_subject.addItem(sub[1], sub[0])  # text, data
                self.subjects_map[sub[1]] = sub[0]

        self.combo_subject.addItem("Без предмета", None)  # Опция "без привязки"

        form_layout.addRow("Название:", self.input_title)
        form_layout.addRow("Срок:", self.input_date)
        form_layout.addRow("Предмет:", self.combo_subject)
        form_layout.addRow("Описание:", self.input_desc)

        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Если редактируем - заполняем данными
        if task_data:
            # task_data = (id, title, due_date, subject_name)
            self.input_title.setText(task_data[1])
            self.input_date.setText(task_data[2] if task_data[2] else "")
            self.input_desc.setText(
                task_data[4] if len(task_data) > 4 else "")  # desc is not in get_all_tasks list, but we can pass it

            # Ищем индекс предмета
            if task_data[3]:  # subject_name
                index = self.combo_subject.findText(task_data[3])
                if index >= 0:
                    self.combo_subject.setCurrentIndex(index)
            else:
                self.combo_subject.setCurrentText("Без предмета")

    def get_data(self):
        subject_id = self.combo_subject.currentData()
        return {
            'title': self.input_title.text(),
            'due_date': self.input_date.text(),
            'subject_id': subject_id,
            'description': self.input_desc.text()
        }


# --- Основное окно ---

STYLES = {
    "light": """
        QMainWindow, QWidget { background-color: #f5f5f5; color: #333; font-family: "Segoe UI", sans-serif; }
        QListWidget { background-color: #ffffff; border: none; border-right: 1px solid #ddd; font-size: 16px; }
        QListWidget::item { padding: 15px; border-bottom: 1px solid #f0f0f0; }
        QListWidget::item:selected { background-color: #e3f2fd; color: #000; font-weight: bold; }
        QPushButton { background-color: #007bff; color: white; border-radius: 6px; padding: 10px; font-weight: bold; border: none; }
        QPushButton:hover { background-color: #0056b3; }
        QLineEdit, QTextEdit, QComboBox { background-color: white; border: 1px solid #ccc; border-radius: 6px; padding: 8px; color: #333; }

        /* CALENDAR LIGHT */
        QCalendarWidget QTableView { background-color: white; color: #333; selection-background-color: #007bff; selection-color: white; }
        QCalendarWidget QToolButton { color: #333; background-color: transparent; }
        QCalendarWidget QWidget#qt_calendar_navigationbar { background-color: #e0e0e0; }
    """,
    "dark": """
        QMainWindow, QWidget { background-color: #121212; color: #e0e0e0; font-family: "Segoe UI", sans-serif; }
        QListWidget { background-color: #1e1e1e; border: none; border-right: 1px solid #333; font-size: 16px; }
        QListWidget::item { padding: 15px; border-bottom: 1px solid #2c2c2c; }
        QListWidget::item:selected { background-color: #3a7bd5; color: white; font-weight: bold; }
        QPushButton { background-color: #3a7bd5; color: white; border-radius: 6px; padding: 10px; font-weight: bold; border: none; }
        QPushButton:hover { background-color: #5a95e5; }
        QLineEdit, QTextEdit, QComboBox { background-color: #2d2d2d; border: 1px solid #444; border-radius: 6px; padding: 8px; color: white; }

        /* CALENDAR DARK - Полностью переделано */
        QCalendarWidget { background-color: #121212; }
        QCalendarWidget QTableView { 
            background-color: #1e1e1e; 
            color: #e0e0e0; 
            selection-background-color: #3a7bd5; 
            selection-color: white; 
            gridline-color: #444; 
            alternate-background-color: #252525;
            outline: 0px;
        }
        QCalendarWidget QTableView::item:selected { 
            background-color: #3a7bd5; 
            color: white; 
        }
        QCalendarWidget QTableView::item:hover { 
            background-color: #2a2a2a; 
        }
        QCalendarWidget QToolButton { 
            color: #e0e0e0; 
            background-color: #252525; 
            border: 1px solid #444; 
            border-radius: 4px; 
            margin: 2px; 
            padding: 4px;
            font-weight: bold;
        }
        QCalendarWidget QToolButton:hover { 
            background-color: #3a3a3a; 
        }
        QCalendarWidget QToolButton::menu-indicator { 
            image: none; 
        }
        QCalendarWidget QWidget#qt_calendar_navigationbar { 
            background-color: #252525; 
        }
        QCalendarWidget QSpinBox { 
            background-color: #2d2d2d; 
            color: white; 
            selection-color: white; 
            selection-background-color: #3a7bd5; 
            border: 1px solid #444; 
            padding: 2px;
            border-radius: 4px;
        }
        QCalendarWidget QSpinBox::up-button, QCalendarWidget QSpinBox::down-button { 
            background-color: #3a3a3a; 
            border: none; 
            width: 15px;
        }
        QCalendarWidget QSpinBox::up-button:hover, QCalendarWidget QSpinBox::down-button:hover { 
            background-color: #4a4a4a; 
        }
    """
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        database.init_db()
        self.current_theme = database.get_setting('theme', 'light')
        self.apply_theme(self.current_theme)
        self.storage_path = database.get_setting('path', '')

        self.current_note_path = None
        # Состояние сортировки
        self.is_subj_reverse = False
        self.is_task_reverse = False

        self.setup_subjects_ui()
        self.setup_settings_ui()
        self.setup_calendar_ui()
        self.setup_tasks_ui()
        self.setup_notes_ui()
        self.setup_menu_logic()
        self.load_subjects()
        self.load_tasks()
        self.update_calendar_deadlines()

    def apply_theme(self, theme_name):
        app = QApplication.instance()
        app.setStyleSheet(STYLES.get(theme_name, STYLES["light"]))

    def setup_menu_logic(self):
        self.ui.menuList.addItem("  📚 Предметы")
        self.ui.menuList.addItem("  📅 Календарь")
        self.ui.menuList.addItem("  ⚙️ Настройки")
        self.ui.menuList.addItem("  📝 Задания")
        self.ui.menuList.addItem("  📓 Блокнот")
        self.ui.menuList.currentRowChanged.connect(self.change_page)

    def change_page(self, index):
        if index == 0:
            self.ui.pagesStack.setCurrentWidget(self.ui.page_subjects)
            self.load_subjects()
        elif index == 1:
            self.ui.pagesStack.setCurrentWidget(self.ui.page_calendar)
            self.update_calendar_deadlines()
        elif index == 2:
            self.ui.pagesStack.setCurrentWidget(self.ui.page_settings)
            self.load_settings_data()
        elif index == 3:
            self.ui.pagesStack.setCurrentWidget(self.ui.page_tasks)
            self.load_tasks()
        elif index == 4:
            self.ui.pagesStack.setCurrentWidget(self.ui.page_notes)
            self.update_note_path_label()

    def setup_subjects_ui(self):
        page = self.ui.page_subjects
        layout = QHBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("<h2>Мои предметы</h2>"))

        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("Сортировка:"))
        self.combo_subj_sort = QComboBox()
        self.combo_subj_sort.addItem("По названию", "name")
        self.combo_subj_sort.addItem("По преподавателю", "teacher")
        self.combo_subj_sort.addItem("По кабинету", "room")
        self.combo_subj_sort.currentTextChanged.connect(self.load_subjects)
        sort_layout.addWidget(self.combo_subj_sort)

        self.btn_subj_reverse = QPushButton("⇅")
        self.btn_subj_reverse.setFixedWidth(30)
        self.btn_subj_reverse.setToolTip("Изменить порядок")
        self.btn_subj_reverse.clicked.connect(self.toggle_subject_sort)
        sort_layout.addWidget(self.btn_subj_reverse)

        sort_layout.addStretch()
        left_layout.addLayout(sort_layout)

        self.subjects_list = QListWidget()
        self.subjects_list.itemClicked.connect(self.show_subject_details)
        left_layout.addWidget(self.subjects_list)
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Добавить")
        self.btn_edit = QPushButton("Изменить")
        self.btn_del = QPushButton("Удалить")
        self.btn_add.clicked.connect(self.add_subject)
        self.btn_edit.clicked.connect(self.edit_subject)
        self.btn_del.clicked.connect(self.delete_subject)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_del)
        left_layout.addLayout(btn_layout)
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("<h2>Детали</h2>"))
        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.Shape.StyledPanel)
        info_layout = QVBoxLayout(info_frame)
        self.lbl_name = QLabel("Название: -")
        self.lbl_teacher = QLabel("Преподаватель: -")
        self.lbl_room = QLabel("Кабинет: -")
        info_layout.addWidget(self.lbl_name)
        info_layout.addWidget(self.lbl_teacher)
        info_layout.addWidget(self.lbl_room)
        info_layout.addSpacing(10)
        info_layout.addWidget(QLabel("<b>Описание:</b>"))
        self.txt_desc = QLabel("-")
        self.txt_desc.setWordWrap(True)
        self.txt_desc.setAlignment(Qt.AlignmentFlag.AlignTop)
        info_layout.addWidget(self.txt_desc)
        right_layout.addWidget(info_frame)
        right_layout.addStretch()
        layout.addLayout(left_layout, 30)
        layout.addLayout(right_layout, 70)

    def toggle_subject_sort(self):
        self.is_subj_reverse = not self.is_subj_reverse
        self.load_subjects()

    def load_subjects(self):
        self.subjects_list.clear()
        sort_mode = self.combo_subj_sort.currentData()
        if not sort_mode: sort_mode = 'name'

        data = database.get_all_subjects(sort_by=sort_mode, reverse=self.is_subj_reverse)
        for row in data:
            self.subjects_list.addItem(f"{row[1]} (каб. {row[3]})")
            self.subjects_list.item(self.subjects_list.count() - 1).setData(Qt.ItemDataRole.UserRole, row[0])

    def show_subject_details(self, item):
        sid = item.data(Qt.ItemDataRole.UserRole)
        data = database.get_subject_details(sid)
        if data:
            self.lbl_name.setText(f"<b>Название:</b> {data[1]}")
            self.lbl_teacher.setText(f"<b>Преподаватель:</b> {data[2]}")
            self.lbl_room.setText(f"<b>Кабинет:</b> {data[3]}")
            self.txt_desc.setText(data[4] if data[4] else "Нет описания")

    def add_subject(self):
        name, ok = QInputDialog.getText(self, "Новый предмет", "Название:")
        if ok and name:
            teacher, ok1 = QInputDialog.getText(self, "Новый предмет", "Преподаватель:")
            room, ok2 = QInputDialog.getText(self, "Новый предмет", "Кабинет:")
            desc, ok3 = QInputDialog.getText(self, "Новый предмет", "Описание:", text="")
            database.add_subject(name, teacher or "", room or "", desc or "")
            self.load_subjects()

    def edit_subject(self):
        item = self.subjects_list.currentItem()
        if not item: return
        sid = item.data(Qt.ItemDataRole.UserRole)
        data = database.get_subject_details(sid)
        name, ok = QInputDialog.getText(self, "Ред.", "Название:", text=data[1])
        if ok:
            teacher, ok1 = QInputDialog.getText(self, "Ред.", "Преподаватель:", text=data[2])
            room, ok2 = QInputDialog.getText(self, "Ред.", "Кабинет:", text=data[3])
            desc, ok3 = QInputDialog.getText(self, "Ред.", "Описание:", text=data[4] or "")
            database.update_subject(sid, name, teacher or "", room or "", desc or "")
            self.load_subjects()
            self.show_subject_details(item)

    def delete_subject(self):
        item = self.subjects_list.currentItem()
        if not item: return
        if QMessageBox.question(self, "Удаление", "Удалить предмет?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            database.delete_subject(item.data(Qt.ItemDataRole.UserRole))
            self.load_subjects()
            self.lbl_name.setText("Название: -")
            self.lbl_teacher.setText("Преподаватель: -")
            self.lbl_room.setText("Кабинет: -")
            self.txt_desc.setText("-")

    def setup_calendar_ui(self):
        page = self.ui.page_calendar
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.addWidget(QLabel("<h2>Календарь дедлайнов</h2>"))
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        layout.addWidget(self.calendar)
        self.lbl_date = QLabel("Выберите дату")
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_date)
        self.calendar.clicked.connect(self.on_date_click)

    def update_calendar_deadlines(self):
        self.calendar.setDateTextFormat(QDate(), QTextCharFormat())
        tasks = database.get_all_tasks()
        for task in tasks:
            date_str = task[2]
            if date_str:
                y, m, d = map(int, date_str.split('-'))
                qdate = QDate(y, m, d)
                fmt = QTextCharFormat()
                fmt.setBackground(QColor("#ffcccc"))
                if self.current_theme == 'dark':
                    fmt.setForeground(QBrush(QColor("white")))
                self.calendar.setDateTextFormat(qdate, fmt)

    def on_date_click(self, date):
        date_str = date.toString("yyyy-MM-dd")
        tasks = database.get_all_tasks()
        task_names = [t[1] for t in tasks if t[2] == date_str]
        if task_names:
            self.lbl_date.setText(f"<b>{date.toString('dddd, d MMMM yyyy')}</b><br>Задачи: {', '.join(task_names)}")
        else:
            self.lbl_date.setText(f"{date.toString('dddd, d MMMM yyyy')}<br>Нет задач")

    def setup_settings_ui(self):
        page = self.ui.page_settings
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        layout.addWidget(QLabel("<h2>Настройки</h2>"))
        layout.addWidget(QLabel("Оформление:"))
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["light", "dark"])
        self.combo_theme.currentTextChanged.connect(self.change_theme)
        layout.addWidget(self.combo_theme)
        layout.addSpacing(20)
        layout.addWidget(QLabel("Рабочая папка (по умолчанию):"))
        path_layout = QHBoxLayout()
        self.edit_path = QLineEdit()
        self.edit_path.setReadOnly(True)
        btn_browse = QPushButton("Обзор...")
        btn_browse.clicked.connect(self.browse_folder)
        path_layout.addWidget(self.edit_path)
        path_layout.addWidget(btn_browse)
        layout.addLayout(path_layout)
        layout.addStretch()

    def load_settings_data(self):
        self.combo_theme.setCurrentText(self.current_theme)
        self.edit_path.setText(self.storage_path)

    def change_theme(self, theme):
        self.current_theme = theme
        self.apply_theme(theme)
        database.save_setting('theme', theme)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            self.storage_path = folder
            self.edit_path.setText(folder)
            database.save_setting('path', folder)

    def setup_tasks_ui(self):
        page = self.ui.page_tasks
        layout = QHBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("<h2>Список заданий</h2>"))

        task_sort_layout = QHBoxLayout()
        task_sort_layout.addWidget(QLabel("Сортировка:"))
        self.combo_task_sort = QComboBox()
        self.combo_task_sort.addItem("По дедлайну", "due_date")
        self.combo_task_sort.addItem("По предмету", "subject")
        self.combo_task_sort.addItem("По названию", "title")
        self.combo_task_sort.currentTextChanged.connect(self.load_tasks)
        task_sort_layout.addWidget(self.combo_task_sort)

        self.btn_task_reverse = QPushButton("⇅")
        self.btn_task_reverse.setFixedWidth(30)
        self.btn_task_reverse.setToolTip("Изменить порядок")
        self.btn_task_reverse.clicked.connect(self.toggle_task_sort)
        task_sort_layout.addWidget(self.btn_task_reverse)

        task_sort_layout.addStretch()
        left_layout.addLayout(task_sort_layout)

        self.tasks_list = QListWidget()
        self.tasks_list.itemClicked.connect(self.show_task_details)
        left_layout.addWidget(self.tasks_list)
        btn_layout = QHBoxLayout()
        self.btn_add_task = QPushButton("Добавить")
        self.btn_edit_task = QPushButton("Ред.")
        self.btn_del_task = QPushButton("Удалить")
        self.btn_add_task.clicked.connect(self.add_task)
        self.btn_edit_task.clicked.connect(self.edit_task)
        self.btn_del_task.clicked.connect(self.delete_task)
        btn_layout.addWidget(self.btn_add_task)
        btn_layout.addWidget(self.btn_edit_task)
        btn_layout.addWidget(self.btn_del_task)
        left_layout.addLayout(btn_layout)
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("<h2>Детали задания</h2>"))
        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.Shape.StyledPanel)
        info_layout = QVBoxLayout(info_frame)
        self.task_title = QLabel("Название: -")
        self.task_subject = QLabel("Предмет: -")
        self.task_date = QLabel("Срок: -")
        info_layout.addWidget(self.task_title)
        info_layout.addWidget(self.task_subject)
        info_layout.addWidget(self.task_date)
        info_layout.addSpacing(10)
        info_layout.addWidget(QLabel("<b>Описание:</b>"))
        self.task_desc = QLabel("-")
        self.task_desc.setWordWrap(True)
        self.task_desc.setAlignment(Qt.AlignmentFlag.AlignTop)
        info_layout.addWidget(self.task_desc)
        right_layout.addWidget(info_frame)
        right_layout.addStretch()
        layout.addLayout(left_layout, 30)
        layout.addLayout(right_layout, 70)

    def toggle_task_sort(self):
        self.is_task_reverse = not self.is_task_reverse
        self.load_tasks()

    def load_tasks(self):
        self.tasks_list.clear()
        sort_mode = self.combo_task_sort.currentData()
        if not sort_mode: sort_mode = 'due_date'

        data = database.get_all_tasks(sort_by=sort_mode, reverse=self.is_task_reverse)
        # data structure: (id, title, due_date, subject_name)
        for row in data:
            subject_name = row[3] if row[3] else "Без предмета"
            date_str = row[2] if row[2] else "Без даты"
            self.tasks_list.addItem(f"[{subject_name}] {row[1]} ({date_str})")
            self.tasks_list.item(self.tasks_list.count() - 1).setData(Qt.ItemDataRole.UserRole, row[0])

    def show_task_details(self, item):
        tid = item.data(Qt.ItemDataRole.UserRole)
        data = database.get_task_details(tid)
        if data:
            # data = (id, title, description, due_date, subject_id)
            self.task_title.setText(f"<b>Название:</b> {data[1]}")
            self.task_date.setText(f"<b>Срок:</b> {data[3] if data[3] else 'Не указан'}")

            sub_id = data[4]
            if sub_id:
                sub_details = database.get_subject_details(sub_id)
                sub_name = sub_details[1] if sub_details else "Неизвестен"
                self.task_subject.setText(f"<b>Предмет:</b> {sub_name}")
            else:
                self.task_subject.setText("<b>Предмет:</b> -")

            self.task_desc.setText(data[2] if data[2] else "Нет описания")

    def add_task(self):
        subjects = database.get_all_subjects()
        dlg = TaskDialog(self, subjects)
        if dlg.exec():
            data = dlg.get_data()
            database.add_task(data['title'], data['description'], data['due_date'], data['subject_id'])
            self.load_tasks()
            self.update_calendar_deadlines()

    def edit_task(self):
        item = self.tasks_list.currentItem()
        if not item: return

        try:
            tid = item.data(Qt.ItemDataRole.UserRole)
            data = database.get_task_details(tid)  # (id, title, desc, due_date, subject_id)

            if not data:
                QMessageBox.warning(self, "Ошибка", "Задача не найдена в базе.")
                return

            # Нам нужно полное имя предмета для диалога
            subject_name = None
            sub_id = data[4]

            if sub_id:
                try:
                    sub = database.get_subject_details(sub_id)
                    if sub:
                        subject_name = sub[1]
                except:
                    subject_name = None

            # Формируем данные для диалога
            # (id, title, due_date, subject_name, description)
            task_data_for_dialog = (data[0], data[1], data[3], subject_name, data[2])

            subjects = database.get_all_subjects()
            dlg = TaskDialog(self, subjects, task_data_for_dialog)

            if dlg.exec():
                new_data = dlg.get_data()

                # Обновляем в БД
                database.update_task(tid, new_data['title'], new_data['description'], new_data['due_date'],
                                     new_data['subject_id'])

                # Перезагружаем список
                self.load_tasks()

                # Обновляем детали на экране (пытаемся найти тот же item по индексу)
                current_row = self.tasks_list.row(item)
                new_item = self.tasks_list.item(current_row)
                if new_item:
                    self.show_task_details(new_item)

                self.update_calendar_deadlines()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка редактирования", f"Произошла ошибка при сохранении:\n{str(e)}")
            print(f"Error: {e}")  # Для отладки в консоли

    def delete_task(self):
        item = self.tasks_list.currentItem()
        if not item: return
        if QMessageBox.question(self, "Удаление", "Удалить задание?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            database.delete_task(item.data(Qt.ItemDataRole.UserRole))
            self.load_tasks()
            self.task_title.setText("Название: -")
            self.task_subject.setText("Предмет: -")
            self.task_date.setText("Срок: -")
            self.task_desc.setText("-")
            self.update_calendar_deadlines()

    def setup_notes_ui(self):
        page = self.ui.page_notes
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_current_file = QLabel("<b>Новый файл</b>")
        self.lbl_current_file.setStyleSheet("font-size: 12px; padding: 5px; color: gray;")
        layout.addWidget(self.lbl_current_file)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(5, 5, 5, 5)

        self.btn_open = QPushButton("📂 Открыть")
        self.btn_open.clicked.connect(self.open_file)
        toolbar_layout.addWidget(self.btn_open)

        self.btn_save = QPushButton("💾 Сохранить")
        self.btn_save.clicked.connect(self.save_file)
        toolbar_layout.addWidget(self.btn_save)

        self.btn_save_as = QPushButton("📤 Сохранить как...")
        self.btn_save_as.clicked.connect(self.save_file_as)
        toolbar_layout.addWidget(self.btn_save_as)

        toolbar_layout.addSpacing(15)

        toolbar_layout.addWidget(QLabel("Размер:"))
        self.combo_font_size = QComboBox()
        self.combo_font_size.addItems(["8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "28", "36"])
        self.combo_font_size.setCurrentText("12")
        self.combo_font_size.currentTextChanged.connect(self.change_font_size)
        toolbar_layout.addWidget(self.combo_font_size)

        self.btn_align_center = QPushButton("Центр")
        self.btn_align_center.setCheckable(True)
        self.btn_align_center.clicked.connect(self.toggle_align_center)
        toolbar_layout.addWidget(self.btn_align_center)

        self.btn_bold = QPushButton("B")
        self.btn_bold.setCheckable(True)
        self.btn_bold.clicked.connect(self.toggle_bold)
        toolbar_layout.addWidget(self.btn_bold)

        self.btn_italic = QPushButton("I")
        self.btn_italic.setCheckable(True)
        self.btn_italic.clicked.connect(self.toggle_italic)
        toolbar_layout.addWidget(self.btn_italic)

        toolbar_layout.addStretch()

        layout.addLayout(toolbar_layout)

        self.notes_editor = QTextEdit()
        self.notes_editor.setPlaceholderText("Текст редактора...")
        layout.addWidget(self.notes_editor)

    def update_note_path_label(self):
        if self.current_note_path:
            self.lbl_current_file.setText(f"📄 {self.current_note_path}")
        else:
            self.lbl_current_file.setText("<b>Новый файл</b> (не сохранен)")

    def change_font_size(self, size):
        fmt = self.notes_editor.currentCharFormat()
        fmt.setFontPointSize(float(size))
        self.notes_editor.setCurrentCharFormat(fmt)

    def toggle_align_center(self):
        if self.btn_align_center.isChecked():
            self.notes_editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            self.notes_editor.setAlignment(Qt.AlignmentFlag.AlignLeft)

    def toggle_bold(self):
        fmt = self.notes_editor.currentCharFormat()
        if self.btn_bold.isChecked():
            fmt.setFontWeight(QFont.Weight.Bold)
        else:
            fmt.setFontWeight(QFont.Weight.Normal)
        self.notes_editor.setCurrentCharFormat(fmt)

    def toggle_italic(self):
        fmt = self.notes_editor.currentCharFormat()
        fmt.setFontItalic(self.btn_italic.isChecked())
        self.notes_editor.setCurrentCharFormat(fmt)

    def open_file(self):
        start_dir = self.storage_path if self.storage_path else os.path.expanduser("~")
        filepath, _ = QFileDialog.getOpenFileName(self, "Открыть файл", start_dir,
                                                  "Документы (*.docx *.txt);;Word (*.docx);;Текст (*.txt)")
        if filepath:
            self.load_file_content(filepath)
            self.current_note_path = filepath
            self.update_note_path_label()

    def save_file(self):
        if self.current_note_path:
            self.save_file_content(self.current_note_path)
        else:
            self.save_file_as()

    def save_file_as(self):
        start_dir = self.storage_path if self.storage_path else os.path.expanduser("~")
        filepath, _ = QFileDialog.getSaveFileName(self, "Сохранить файл", start_dir,
                                                  "Word Documents (*.docx);;Text Files (*.txt)")
        if filepath:
            self.save_file_content(filepath)
            self.current_note_path = filepath
            self.update_note_path_label()

    def load_file_content(self, path):
        try:
            if path.endswith('.docx'):
                doc = Document(path)
                self.notes_editor.clear()
                cursor = self.notes_editor.textCursor()

                is_first_paragraph = True

                for para in doc.paragraphs:
                    if not is_first_paragraph:
                        cursor.insertBlock()
                    else:
                        is_first_paragraph = False

                    block_fmt = QTextBlockFormat()
                    alignment = para.alignment

                    if alignment == WD_ALIGN_PARAGRAPH.CENTER:
                        block_fmt.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    elif alignment == WD_ALIGN_PARAGRAPH.RIGHT:
                        block_fmt.setAlignment(Qt.AlignmentFlag.AlignRight)
                    else:
                        block_fmt.setAlignment(Qt.AlignmentFlag.AlignLeft)

                    cursor.setBlockFormat(block_fmt)

                    for run in para.runs:
                        if run.text:
                            char_fmt = QTextCharFormat()

                            f_size = None
                            if run.font.size:
                                f_size = run.font.size.pt

                            if not f_size or f_size < 1:
                                f_size = 12

                            char_fmt.setFontPointSize(f_size)

                            is_bold = run.font.bold
                            if is_bold:
                                char_fmt.setFontWeight(QFont.Weight.Bold)

                            is_italic = run.font.italic
                            if is_italic:
                                char_fmt.setFontItalic(True)

                            cursor.insertText(run.text, char_fmt)

                    if not para.text.strip() and len(para.runs) == 0:
                        cursor.insertText(" ")

            elif path.endswith('.txt'):
                with open(path, 'r', encoding='utf-8') as f:
                    self.notes_editor.setPlainText(f.read())
            else:
                QMessageBox.warning(self, "Ошибка", "Неподдерживаемый формат файла")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось прочитать файл:\n{e}")

    def save_file_content(self, path):
        try:
            if path.endswith('.docx'):
                doc = Document()

                block = self.notes_editor.document().begin()

                while block.isValid():
                    text = block.text()

                    char_fmt = block.charFormat()
                    block_fmt = block.blockFormat()

                    para = doc.add_paragraph(text, style=None)

                    if not para.runs:
                        run = para.add_run("")
                    else:
                        run = para.runs[0]

                    font_size = char_fmt.fontPointSize()
                    if font_size <= 1:
                        font_size = 11
                    run.font.size = Pt(font_size)

                    if char_fmt.fontWeight() == QFont.Weight.Bold:
                        run.font.bold = True
                    else:
                        run.font.bold = False

                    if char_fmt.fontItalic():
                        run.font.italic = True
                    else:
                        run.font.italic = False

                    run.font.color.rgb = RGBColor(0, 0, 0)

                    if block_fmt.alignment() == Qt.AlignmentFlag.AlignCenter:
                        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    elif block_fmt.alignment() == Qt.AlignmentFlag.AlignRight:
                        para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    else:
                        para.alignment = WD_ALIGN_PARAGRAPH.LEFT

                    block = block.next()

                doc.save(path)
                QMessageBox.information(self, "Успех", f"Файл сохранен:\n{path}")

            elif path.endswith('.txt'):
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.notes_editor.toPlainText())
                QMessageBox.information(self, "Успех", f"Файл сохранен:\n{path}")
            else:
                QMessageBox.warning(self, "Ошибка", "Неподдерживаемый формат для сохранения")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())