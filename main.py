import sys
import os
import logging
import database
import notifications
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMessageBox,
                             QFileDialog, QInputDialog)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QKeySequence, QShortcut
from ui_py.ui_main import Ui_MainWindow
from ui.styles import STYLES
from ui.dialogs import SearchDialog
from ui.ai_chat import AIChatWidget
from ui.schedule_parser import WeekCalculator

from pages.subjects import SubjectsPage
from pages.schedule import SchedulePage
from pages.calendar import CalendarPage
from pages.settings import SettingsPage
from pages.tasks import TasksPage
from pages.notes import NotesPage
from pages.grades import GradesPage
from pages.wishlist import WishlistPage

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.info('=== START ===')
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        database.init_db()
        self.current_theme = database.get_setting('theme', 'light')
        self.apply_theme(self.current_theme)
        self.storage_path = database.get_setting('path', '')
        self.current_note_path = None

        self.subjects_page = SubjectsPage(self)
        self.schedule_page = SchedulePage(self)
        self.calendar_page = CalendarPage(self)
        self.settings_page = SettingsPage(self)
        self.tasks_page = TasksPage(self)
        self.notes_page = NotesPage(self)
        self.grades_page = GradesPage(self)
        self.wishlist_page = WishlistPage(self)

        self._setup_ai_ui()
        self._setup_menu_logic()
        self._setup_global_search()

        self.subjects_page.load()
        self.tasks_page.load()
        self.calendar_page.update_deadlines()
        logger.info('=== INIT DONE ===')

        self.notification_manager = notifications.NotificationManager(self)
        self.notification_manager.initialize()
        self._setup_notifications_menu()

    def apply_theme(self, theme_name):
        app = QApplication.instance()
        app.setStyleSheet(STYLES.get(theme_name, STYLES['light']))

    def _setup_menu_logic(self):
        self.ui.menuList.addItem('Предметы')
        self.ui.menuList.addItem('Расписание')
        self.ui.menuList.addItem('Календарь')
        self.ui.menuList.addItem('Настройки')
        self.ui.menuList.addItem('Задания')
        self.ui.menuList.addItem('Блокнот')
        self.ui.menuList.addItem('Оценки')
        self.ui.menuList.addItem('ИИ-ассистент')
        self.ui.menuList.addItem('Желания')
        self.ui.menuList.currentRowChanged.connect(self.change_page)

    def _setup_global_search(self):
        search_menu = self.ui.menubar.addMenu('Поиск')
        search_action = search_menu.addAction('Глобальный поиск')
        search_action.triggered.connect(self.open_search_dialog)
        self.search_shortcut = QShortcut(QKeySequence('Ctrl+F'), self)
        self.search_shortcut.activated.connect(self.open_search_dialog)

    def _setup_ai_ui(self):
        self.ai_chat = AIChatWidget(self)
        page = self.ui.page_ai
        from PyQt6.QtWidgets import QVBoxLayout
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ai_chat)

    def _setup_notifications_menu(self):
        notif_menu = self.ui.menubar.addMenu('Уведомления')
        check_action = notif_menu.addAction('Проверить дедлайны')
        check_action.triggered.connect(self.notification_manager.manual_check)
        notif_menu.addSeparator()
        settings_action = notif_menu.addAction('Настройки уведомлений')
        settings_action.triggered.connect(self.show_notification_settings)

    def show_notification_settings(self):
        QMessageBox.information(self, 'Настройки уведомлений',
                                'Уведомления проверяются автоматически каждые 30 минут. '
                                'Срочные уведомления показываются в трее.')

    def open_search_dialog(self):
        dialog = SearchDialog(self)
        dialog.exec()

    def navigate_to_item(self, item_type, item_id):
        logger.debug(f'navigate_to_item: type={item_type}, id={item_id}')
        if item_type == 'subject':
            self.ui.menuList.setCurrentRow(0)
            self.ui.pagesStack.setCurrentWidget(self.ui.page_subjects)
            self.subjects_page.find_and_select(item_id)
        elif item_type == 'task':
            self.ui.menuList.setCurrentRow(4)
            self.ui.pagesStack.setCurrentWidget(self.ui.page_tasks)
            self.tasks_page.find_and_select(item_id)

    def change_page(self, index):
        logger.debug(f'change_page: index={index}')
        pages = {
            0: (self.ui.page_subjects, self.subjects_page.load),
            1: (self.ui.page_schedule, self.schedule_page.load),
            2: (self.ui.page_calendar, self.calendar_page.update_deadlines),
            3: (self.ui.page_settings, self.settings_page.load_data),
            4: (self.ui.page_tasks, self.tasks_page.load),
            5: (self.ui.page_notes, self.notes_page.update_path_label),
            6: (self.ui.page_grades, self.grades_page.load),
            7: (self.ui.page_ai, self.ai_chat.load_settings),
            8: (self.ui.page_wishlist, self.wishlist_page.load),
        }
        if index in pages:
            widget, load_fn = pages[index]
            self.ui.pagesStack.setCurrentWidget(widget)
            load_fn()

    def closeEvent(self, event):
        if self.notification_manager and self.notification_manager.tray_icon:
            self.hide()
            self.notification_manager.show_tray_message(
                'Study Planner', 'Приложение свернуто в трей. Двойной клик для разворачивания.')
            event.ignore()
        else:
            if self.notification_manager:
                self.notification_manager.cleanup()
            event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
