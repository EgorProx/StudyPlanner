import sys
import database
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QWidget,
                             QVBoxLayout, QHBoxLayout, QListWidget, QLabel,
                             QLineEdit, QPushButton, QTextEdit, QCalendarWidget,
                             QComboBox, QFileDialog, QInputDialog, QFrame)
from PyQt6.QtCore import Qt
from ui_py.ui_main import Ui_MainWindow

STYLES = {
    "light": """
        QMainWindow, QWidget { background-color: #f5f5f5; color: #333; font-family: "Segoe UI", sans-serif; }
        QListWidget { background-color: #ffffff; border: none; border-right: 1px solid #ddd; font-size: 16px; }
        QListWidget::item { padding: 15px; border-bottom: 1px solid #f0f0f0; }
        QListWidget::item:selected { background-color: #e3f2fd; color: #000; font-weight: bold; }
        QPushButton { background-color: #007bff; color: white; border-radius: 6px; padding: 10px; font-weight: bold; border: none; }
        QPushButton:hover { background-color: #0056b3; }
        QLineEdit, QTextEdit, QComboBox { background-color: white; border: 1px solid #ccc; border-radius: 6px; padding: 8px; color: #333; }
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
        QCalendarWidget QTableView { background-color: #2d2d2d; color: #e0e0e0; selection-background-color: #3a7bd5; selection-color: white; gridline-color: #444; }
        QCalendarWidget QToolButton { color: #e0e0e0; background-color: transparent; }
        QCalendarWidget QWidget#qt_calendar_navigationbar { background-color: #252525; }
        QCalendarWidget QSpinBox { background-color: #252525; color: white; selection-color: white; selection-background-color: #3a7bd5; }
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

        self.setup_subjects_ui()
        self.setup_settings_ui()
        self.setup_calendar_ui()
        self.setup_tasks_ui()
        self.setup_menu_logic()
        self.load_subjects()
        self.load_tasks()

    def apply_theme(self, theme_name):
        app = QApplication.instance()
        app.setStyleSheet(STYLES.get(theme_name, STYLES["light"]))

    def setup_menu_logic(self):
        self.ui.menuList.addItem("Предметы")
        self.ui.menuList.addItem("Календарь")
        self.ui.menuList.addItem("Настройки")
        self.ui.menuList.addItem("Задания")
        self.ui.menuList.currentRowChanged.connect(self.change_page)

    def change_page(self, index):
        if index == 0:
            self.ui.pagesStack.setCurrentWidget(self.ui.page_subjects)
            self.load_subjects()
        elif index == 1:
            self.ui.pagesStack.setCurrentWidget(self.ui.page_calendar)
        elif index == 2:
            self.ui.pagesStack.setCurrentWidget(self.ui.page_settings)
            self.load_settings_data()
        elif index == 3:
            self.ui.pagesStack.setCurrentWidget(self.ui.page_tasks)
            self.load_tasks()

    def setup_subjects_ui(self):
        page = self.ui.page_subjects
        layout = QHBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("<h2>Мои предметы</h2>"))
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

    def load_subjects(self):
        self.subjects_list.clear()
        data = database.get_all_subjects()
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
        layout.addWidget(QLabel("<h2>Календарь</h2>"))
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        layout.addWidget(self.calendar)
        self.lbl_date = QLabel("Выберите дату")
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_date)
        self.calendar.clicked.connect(self.on_date_click)

    def on_date_click(self, date):
        self.lbl_date.setText(f"Вы выбрали: {date.toString('dddd, d MMMM yyyy')}")

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
        layout.addWidget(QLabel("Рабочая папка:"))
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
        self.task_date = QLabel("Срок: -")

        info_layout.addWidget(self.task_title)
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

    def load_tasks(self):
        self.tasks_list.clear()
        data = database.get_all_tasks()
        for row in data:
            date_str = row[2] if row[2] else "Без даты"
            self.tasks_list.addItem(f"{row[1]} ({date_str})")
            self.tasks_list.item(self.tasks_list.count() - 1).setData(Qt.ItemDataRole.UserRole, row[0])

    def show_task_details(self, item):
        tid = item.data(Qt.ItemDataRole.UserRole)
        data = database.get_task_details(tid)
        if data:
            self.task_title.setText(f"<b>Название:</b> {data[1]}")
            self.task_date.setText(f"<b>Срок:</b> {data[3] if data[3] else 'Не указан'}")
            self.task_desc.setText(data[2] if data[2] else "Нет описания")

    def add_task(self):
        title, ok = QInputDialog.getText(self, "Новое задание", "Название:")
        if ok and title:
            date, ok1 = QInputDialog.getText(self, "Новое задание", "Срок (ГГГГ-ММ-ДД):", text="")
            desc, ok2 = QInputDialog.getText(self, "Новое задание", "Описание:", text="")
            database.add_task(title, desc or "", date or "")
            self.load_tasks()

    def edit_task(self):
        item = self.tasks_list.currentItem()
        if not item: return
        tid = item.data(Qt.ItemDataRole.UserRole)
        data = database.get_task_details(tid)

        title, ok = QInputDialog.getText(self, "Ред. задание", "Название:", text=data[1])
        if ok:
            date, ok1 = QInputDialog.getText(self, "Ред. задание", "Срок (ГГГГ-ММ-ДД):", text=data[3] or "")
            desc, ok2 = QInputDialog.getText(self, "Ред. задание", "Описание:", text=data[2] or "")
            database.update_task(tid, title, desc or "", date or "")
            self.load_tasks()
            self.show_task_details(item)

    def delete_task(self):
        item = self.tasks_list.currentItem()
        if not item: return
        if QMessageBox.question(self, "Удаление", "Удалить задание?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            database.delete_task(item.data(Qt.ItemDataRole.UserRole))
            self.load_tasks()
            self.task_title.setText("Название: -")
            self.task_date.setText("Срок: -")
            self.task_desc.setText("-")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())