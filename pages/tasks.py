import logging
import database
from PyQt6.QtWidgets import (QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
                             QComboBox, QListWidget, QListWidgetItem, QFrame,
                             QMessageBox)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor

from ui.dialogs import TaskDialog

logger = logging.getLogger(__name__)


class TasksPage:
    def __init__(self, mw):
        self.mw = mw
        self.is_reverse = False
        self._setup_ui()

    def _setup_ui(self):
        page = self.mw.ui.page_tasks
        layout = QHBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel('<h2>Список заданий</h2>'))

        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel('Показать:'))
        self.combo_status = QComboBox()
        self.combo_status.addItem('Активные', 'active')
        self.combo_status.addItem('Архив', 'archived')
        self.combo_status.addItem('Все', 'all')
        self.combo_status.currentTextChanged.connect(self.load)
        status_layout.addWidget(self.combo_status)
        status_layout.addStretch()
        left_layout.addLayout(status_layout)

        task_sort_layout = QHBoxLayout()
        task_sort_layout.addWidget(QLabel('Сортировка:'))
        self.combo_sort = QComboBox()
        self.combo_sort.addItem('По дедлайну', 'due_date')
        self.combo_sort.addItem('По предмету', 'subject')
        self.combo_sort.addItem('По названию', 'title')
        self.combo_sort.currentTextChanged.connect(self.load)
        task_sort_layout.addWidget(self.combo_sort)
        self.btn_reverse = QPushButton('⇅')
        self.btn_reverse.setFixedWidth(30)
        self.btn_reverse.clicked.connect(self._toggle_sort)
        task_sort_layout.addWidget(self.btn_reverse)
        task_sort_layout.addStretch()
        left_layout.addLayout(task_sort_layout)

        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._show_details)
        left_layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton('Добавить')
        self.btn_edit = QPushButton('Ред.')
        self.btn_del = QPushButton('Удалить')
        self.btn_complete = QPushButton('Выполнено')
        self.btn_archive = QPushButton('В архив')
        self.btn_add.clicked.connect(self._add)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_del.clicked.connect(self._delete)
        self.btn_complete.clicked.connect(self._toggle_complete)
        self.btn_archive.clicked.connect(self._toggle_archive)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_del)
        btn_layout.addWidget(self.btn_complete)
        btn_layout.addWidget(self.btn_archive)
        left_layout.addLayout(btn_layout)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel('<h2>Детали задания</h2>'))
        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.Shape.StyledPanel)
        info_layout = QVBoxLayout(info_frame)
        self.task_title = QLabel('Название: -')
        self.task_subject = QLabel('Предмет: -')
        self.task_date = QLabel('Срок: -')
        self.task_completed = QLabel('Выполнение: -')
        self.task_status = QLabel('Архив: -')
        info_layout.addWidget(self.task_title)
        info_layout.addWidget(self.task_subject)
        info_layout.addWidget(self.task_date)
        info_layout.addWidget(self.task_completed)
        info_layout.addWidget(self.task_status)
        info_layout.addSpacing(10)
        info_layout.addWidget(QLabel('<b>Описание:</b>'))
        self.task_desc = QLabel('-')
        self.task_desc.setWordWrap(True)
        self.task_desc.setAlignment(Qt.AlignmentFlag.AlignTop)
        info_layout.addWidget(self.task_desc)
        right_layout.addWidget(info_frame)
        right_layout.addStretch()
        layout.addLayout(left_layout, 30)
        layout.addLayout(right_layout, 70)

    def _toggle_sort(self):
        self.is_reverse = not self.is_reverse
        self.load()

    def load(self):
        try:
            self.list_widget.clear()
            sort_mode = self.combo_sort.currentData() or 'due_date'
            status_filter = self.combo_status.currentData() or 'active'
            data = database.get_all_tasks(sort_by=sort_mode, reverse=self.is_reverse, status_filter=status_filter)
            for row in data:
                subject_name = row[3] if row[3] else 'Без предмета'
                date_str = row[2] if row[2] else 'Без даты'
                completed = row[5] if len(row) > 5 else 0
                status = row[4] if len(row) > 4 else 'active'
                status_text, color = self._get_status_info(row[2], completed, status)
                item_text = f'[{status_text}] [{subject_name}] {row[1]} ({date_str})'
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, row[0])
                item.setForeground(color)
                self.list_widget.addItem(item)
        except Exception as e:
            logger.error(f'load_tasks: {e}', exc_info=True)

    def _get_status_info(self, due_date_str, completed, status):
        if completed:
            return 'Выполнено', QColor(0, 128, 0)
        if status == 'archived':
            return 'В архиве', QColor(128, 128, 128)
        if not due_date_str:
            return 'Без даты', QColor(128, 128, 128)
        try:
            due_date = QDate.fromString(due_date_str, 'yyyy-MM-dd')
            today = QDate.currentDate()
            if due_date < today:
                return 'Просрочено', QColor(220, 20, 60)
            elif due_date <= today.addDays(3):
                return 'Скоро дедлайн', QColor(255, 140, 0)
            else:
                default_color = QColor(0, 0, 0) if self.mw.current_theme == 'light' else QColor(255, 255, 255)
                return 'Активно', default_color
        except:
            return 'Неизвестно', QColor(128, 128, 128)

    def _show_details(self, item):
        if not item:
            return
        try:
            tid = item.data(Qt.ItemDataRole.UserRole)
            if not tid:
                return
            data = database.get_task_details(tid)
            if not data:
                return
            self.task_title.setText(f'<b>Название:</b> {data[1]}')
            self.task_date.setText(f'<b>Срок:</b> {data[3] if data[3] else "Не указан"}')
            sub_id = data[4] if len(data) > 4 else None
            if sub_id:
                sub_details = database.get_subject_details(sub_id)
                sub_name = sub_details[1] if sub_details else 'Неизвестен'
                self.task_subject.setText(f'<b>Предмет:</b> {sub_name}')
            else:
                self.task_subject.setText('<b>Предмет:</b> -')
            status = data[5] if len(data) > 5 else 'active'
            completed = data[6] if len(data) > 6 else 0
            self.task_completed.setText(f'<b>Выполнение:</b> {"Да" if completed else "Нет"}')
            self.task_status.setText(f'<b>Архив:</b> {"Да" if status == "archived" else "Нет"}')
            self.btn_complete.setText('Не выполнено' if completed else 'Выполнено')
            self.btn_archive.setText('Из архива' if status == 'archived' else 'В архив')
            self.task_desc.setText(data[2] if data[2] else 'Нет описания')
        except Exception as e:
            logger.error(f'show_task_details: {e}', exc_info=True)

    def _add(self):
        try:
            subjects = database.get_all_subjects()
            dlg = TaskDialog(self.mw, subjects)
            if dlg.exec():
                data = dlg.get_data()
                database.add_task(data['title'], data['description'], data['due_date'], data['subject_id'])
                self.load()
                self.mw.calendar_page.update_deadlines()
        except Exception as e:
            logger.error(f'add_task: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))

    def _edit(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        try:
            tid = item.data(Qt.ItemDataRole.UserRole)
            data = database.get_task_details(tid)
            if not data:
                return
            subject_name = None
            sub_id = data[4] if len(data) > 4 else None
            if sub_id:
                sub = database.get_subject_details(sub_id)
                if sub:
                    subject_name = sub[1]
            task_data = (data[0], data[1], data[3], subject_name, data[2] if len(data) > 2 else '')
            subjects = database.get_all_subjects()
            dlg = TaskDialog(self.mw, subjects, task_data)
            if dlg.exec():
                new_data = dlg.get_data()
                status = data[5] if len(data) > 5 else 'active'
                completed = data[6] if len(data) > 6 else 0
                database.update_task(tid, new_data['title'], new_data['description'],
                                     new_data['due_date'], new_data['subject_id'], status, completed)
                self.load()
                self.mw.calendar_page.update_deadlines()
                for i in range(self.list_widget.count()):
                    new_item = self.list_widget.item(i)
                    if new_item.data(Qt.ItemDataRole.UserRole) == tid:
                        self.list_widget.setCurrentItem(new_item)
                        self._show_details(new_item)
                        break
        except Exception as e:
            logger.error(f'edit_task: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))

    def _delete(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        try:
            reply = QMessageBox.question(self.mw, 'Удаление', 'Удалить задание?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                tid = item.data(Qt.ItemDataRole.UserRole)
                database.delete_task(tid)
                self.load()
                self.mw.calendar_page.update_deadlines()
                self.task_title.setText('Название: -')
                self.task_subject.setText('Предмет: -')
                self.task_date.setText('Срок: -')
                self.task_completed.setText('Выполнение: -')
                self.task_status.setText('Архив: -')
                self.task_desc.setText('-')
        except Exception as e:
            logger.error(f'delete_task: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))

    def _toggle_complete(self):
        try:
            item = self.list_widget.currentItem()
            if not item:
                return
            tid = item.data(Qt.ItemDataRole.UserRole)
            data = database.get_task_details(tid)
            if not data:
                return
            completed = data[6] if len(data) > 6 else 0
            new_completed = 0 if completed else 1
            database.toggle_task_completed(tid, new_completed)
            self.load()
            self.mw.calendar_page.update_deadlines()
            for i in range(self.list_widget.count()):
                new_item = self.list_widget.item(i)
                if new_item.data(Qt.ItemDataRole.UserRole) == tid:
                    self.list_widget.setCurrentItem(new_item)
                    self._show_details(new_item)
                    break
        except Exception as e:
            logger.error(f'toggle_complete_task: {e}', exc_info=True)

    def _toggle_archive(self):
        try:
            item = self.list_widget.currentItem()
            if not item:
                return
            tid = item.data(Qt.ItemDataRole.UserRole)
            data = database.get_task_details(tid)
            if not data:
                return
            current_status = data[5] if len(data) > 5 else 'active'
            if current_status == 'archived':
                database.restore_task(tid)
                QMessageBox.information(self.mw, 'Готово', 'Задание восстановлено из архива')
            else:
                database.archive_task(tid)
                QMessageBox.information(self.mw, 'Готово', 'Задание перемещено в архив')
            self.load()
            self.mw.calendar_page.update_deadlines()
            for i in range(self.list_widget.count()):
                new_item = self.list_widget.item(i)
                if new_item.data(Qt.ItemDataRole.UserRole) == tid:
                    self.list_widget.setCurrentItem(new_item)
                    self._show_details(new_item)
                    break
        except Exception as e:
            logger.error(f'toggle_archive_task: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))

    def find_and_select(self, item_id):
        self.combo_status.setCurrentIndex(self.combo_status.findData('all'))
        self.load()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == item_id:
                self.list_widget.setCurrentItem(item)
                self._show_details(item)
                return True
        return False
