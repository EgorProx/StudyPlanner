import logging
import database
from PyQt6.QtWidgets import (QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
                             QComboBox, QListWidget, QListWidgetItem, QFrame,
                             QMessageBox, QInputDialog)
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


class SubjectsPage:
    def __init__(self, mw):
        self.mw = mw
        self.is_reverse = False
        self._setup_ui()

    def _setup_ui(self):
        page = self.mw.ui.page_subjects
        layout = QHBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel('<h2>Мои предметы</h2>'))

        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel('Сортировка:'))
        self.combo_sort = QComboBox()
        self.combo_sort.addItem('По названию', 'name')
        self.combo_sort.addItem('По преподавателю', 'teacher')
        self.combo_sort.addItem('По кабинету', 'room')
        self.combo_sort.currentTextChanged.connect(self.load)
        sort_layout.addWidget(self.combo_sort)
        self.btn_reverse = QPushButton('⇅')
        self.btn_reverse.setFixedWidth(30)
        self.btn_reverse.setToolTip('Изменить порядок')
        self.btn_reverse.clicked.connect(self._toggle_sort)
        sort_layout.addWidget(self.btn_reverse)
        sort_layout.addStretch()
        left_layout.addLayout(sort_layout)

        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._show_details)
        left_layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton('Добавить')
        self.btn_edit = QPushButton('Изменить')
        self.btn_del = QPushButton('Удалить')
        self.btn_add.clicked.connect(self._add)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_del.clicked.connect(self._delete)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_del)
        self.btn_clear = QPushButton('Очистить всё')
        self.btn_clear.setToolTip('Удалить все предметы, расписание и оценки')
        self.btn_clear.setStyleSheet('QPushButton { color: #dc3545; } QPushButton:hover { background-color: #dc3545; color: white; }')
        self.btn_clear.clicked.connect(self._clear_all)
        btn_layout.addWidget(self.btn_clear)
        left_layout.addLayout(btn_layout)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel('<h2>Детали</h2>'))
        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.Shape.StyledPanel)
        info_layout = QVBoxLayout(info_frame)
        self.lbl_name = QLabel('Название: -')
        self.lbl_teacher = QLabel('Преподаватель: -')
        self.lbl_room = QLabel('Кабинет: -')
        info_layout.addWidget(self.lbl_name)
        info_layout.addWidget(self.lbl_teacher)
        info_layout.addWidget(self.lbl_room)
        info_layout.addSpacing(10)
        info_layout.addWidget(QLabel('<b>Описание:</b>'))
        self.txt_desc = QLabel('-')
        self.txt_desc.setWordWrap(True)
        self.txt_desc.setAlignment(Qt.AlignmentFlag.AlignTop)
        info_layout.addWidget(self.txt_desc)
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
            sort_mode = self.combo_sort.currentData() or 'name'
            data = database.get_all_subjects(sort_by=sort_mode, reverse=self.is_reverse)
            for row in data:
                if len(row) < 5:
                    continue
                display_text = f'{row[1]} (каб. {row[3] or "-"})'
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, row[0])
                self.list_widget.addItem(item)
        except Exception as e:
            logger.error(f'load_subjects: {e}', exc_info=True)

    def _show_details(self, item):
        try:
            if not item:
                return
            sid = item.data(Qt.ItemDataRole.UserRole)
            if not sid:
                return
            data = database.get_subject_details(sid)
            if not data or len(data) < 5:
                return
            self.lbl_name.setText(f'<b>Название:</b> {data[1] or "-"}')
            self.lbl_teacher.setText(f'<b>Преподаватель:</b> {data[2] or "-"}')
            self.lbl_room.setText(f'<b>Кабинет:</b> {data[3] or "-"}')
            self.txt_desc.setText(data[4] if data[4] else 'Нет описания')
        except Exception as e:
            logger.error(f'show_subject_details: {e}', exc_info=True)

    def _add(self):
        try:
            name, ok = QInputDialog.getText(self.mw, 'Новый предмет', 'Название:')
            if ok and name:
                teacher, _ = QInputDialog.getText(self.mw, 'Новый предмет', 'Преподаватель:')
                room, _ = QInputDialog.getText(self.mw, 'Новый предмет', 'Кабинет:')
                desc, _ = QInputDialog.getText(self.mw, 'Новый предмет', 'Описание:', text='')
                database.add_subject(name, teacher or '', room or '', desc or '')
                self.load()
            elif ok and not name:
                QMessageBox.warning(self.mw, 'Ошибка', 'Название предмета не может быть пустым')
        except Exception as e:
            logger.error(f'add_subject: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))

    def _edit(self):
        try:
            item = self.list_widget.currentItem()
            if not item:
                return
            sid = item.data(Qt.ItemDataRole.UserRole)
            data = database.get_subject_details(sid)
            if not data or len(data) < 5:
                return
            name, ok = QInputDialog.getText(self.mw, 'Редактирование', 'Название:', text=data[1] or '')
            if ok:
                teacher, _ = QInputDialog.getText(self.mw, 'Редактирование', 'Преподаватель:', text=data[2] or '')
                room, _ = QInputDialog.getText(self.mw, 'Редактирование', 'Кабинет:', text=data[3] or '')
                desc, _ = QInputDialog.getText(self.mw, 'Редактирование', 'Описание:', text=data[4] or '')
                database.update_subject(sid, name or '', teacher or '', room or '', desc or '')
                self.load()
                for i in range(self.list_widget.count()):
                    new_item = self.list_widget.item(i)
                    if new_item.data(Qt.ItemDataRole.UserRole) == sid:
                        self.list_widget.setCurrentItem(new_item)
                        self._show_details(new_item)
                        break
        except Exception as e:
            logger.error(f'edit_subject: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))

    def _delete(self):
        try:
            item = self.list_widget.currentItem()
            if not item:
                return
            sid = item.data(Qt.ItemDataRole.UserRole)
            reply = QMessageBox.question(self.mw, 'Удаление', 'Удалить предмет? Задачи останутся без привязки.',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                database.delete_subject(sid)
                self.load()
                self.lbl_name.setText('Название: -')
                self.lbl_teacher.setText('Преподаватель: -')
                self.lbl_room.setText('Кабинет: -')
                self.txt_desc.setText('-')
        except Exception as e:
            logger.error(f'delete_subject: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))

    def _clear_all(self):
        try:
            reply = QMessageBox.warning(
                self.mw, 'Очистка предметов',
                'Удалить ВСЕ предметы, расписание и оценки?\n\nЭто действие невозможно отменить!',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
            database.clear_all_subjects()
            self.load()
            self.lbl_name.setText('Название: -')
            self.lbl_teacher.setText('Преподаватель: -')
            self.lbl_room.setText('Кабинет: -')
            self.txt_desc.setText('-')
            QMessageBox.information(self.mw, 'Готово', 'Все предметы удалены')
        except Exception as e:
            logger.error(f'clear_all_subjects: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))

    def find_and_select(self, item_id):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == item_id:
                self.list_widget.setCurrentItem(item)
                self._show_details(item)
                return True
        return False
