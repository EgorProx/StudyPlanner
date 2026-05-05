import logging
import database
from PyQt6.QtWidgets import (QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
                             QComboBox, QListWidget, QListWidgetItem, QFrame,
                             QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ui.dialogs import WishlistDialog

logger = logging.getLogger(__name__)


class WishlistPage:
    def __init__(self, mw):
        self.mw = mw
        self._setup_ui()

    def _setup_ui(self):
        page = self.mw.ui.page_wishlist
        layout = QHBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel('<h2>Список желаний</h2>'))

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel('Статус:'))
        self.combo_status = QComboBox()
        self.combo_status.addItem('Все', 'all')
        self.combo_status.addItem('Активные', 'pending')
        self.combo_status.addItem('Выполненные', 'done')
        self.combo_status.currentTextChanged.connect(self.load)
        filter_layout.addWidget(self.combo_status)
        filter_layout.addWidget(QLabel('Категория:'))
        self.combo_category = QComboBox()
        self.combo_category.addItem('Все', 'all')
        self.combo_category.currentTextChanged.connect(self.load)
        filter_layout.addWidget(self.combo_category)
        filter_layout.addStretch()
        left_layout.addLayout(filter_layout)

        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel('Сортировка:'))
        self.combo_sort = QComboBox()
        self.combo_sort.addItem('По дате', 'created_at')
        self.combo_sort.addItem('По названию', 'title')
        self.combo_sort.addItem('По приоритету', 'priority')
        self.combo_sort.currentTextChanged.connect(self.load)
        sort_layout.addWidget(self.combo_sort)
        sort_layout.addStretch()
        left_layout.addLayout(sort_layout)

        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._show_details)
        left_layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton('Добавить')
        self.btn_edit = QPushButton('Изменить')
        self.btn_del = QPushButton('Удалить')
        self.btn_done = QPushButton('Выполнено')
        self.btn_add.clicked.connect(self._add)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_del.clicked.connect(self._delete)
        self.btn_done.clicked.connect(self._toggle_done)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_del)
        btn_layout.addWidget(self.btn_done)
        left_layout.addLayout(btn_layout)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel('<h2>Детали</h2>'))
        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.Shape.StyledPanel)
        info_layout = QVBoxLayout(info_frame)
        self.lbl_title = QLabel('Название: -')
        self.lbl_desc = QLabel('Описание: -')
        self.lbl_category = QLabel('Категория: -')
        self.lbl_priority = QLabel('Приоритет: -')
        self.lbl_status = QLabel('Статус: -')
        self.lbl_date = QLabel('Дата: -')
        info_layout.addWidget(self.lbl_title)
        info_layout.addWidget(self.lbl_desc)
        info_layout.addWidget(self.lbl_category)
        info_layout.addWidget(self.lbl_priority)
        info_layout.addWidget(self.lbl_status)
        info_layout.addWidget(self.lbl_date)
        right_layout.addWidget(info_frame)
        right_layout.addStretch()

        layout.addLayout(left_layout, 35)
        layout.addLayout(right_layout, 65)

    def load(self):
        try:
            self.list_widget.clear()
            status_filter = self.combo_status.currentData()
            category_filter = self.combo_category.currentData()
            sort_by = self.combo_sort.currentData()
            data = database.get_all_wishlist(sort_by=sort_by, status_filter=status_filter, category_filter=category_filter)
            categories = set()
            for row in data:
                item_id, title, description, category, priority, status, created_at = row
                if category:
                    categories.add(category)
                priority_display = {'high': 'HIGH', 'medium': 'MED', 'low': 'LOW'}.get(priority, priority)
                status_mark = 'V' if status == 'done' else ' '
                display = f'[{status_mark}] [{priority_display}] {title}'
                item = QListWidgetItem(display)
                item.setData(Qt.ItemDataRole.UserRole, item_id)
                if status == 'done':
                    item.setForeground(QColor(128, 128, 128))
                elif priority == 'high':
                    item.setForeground(QColor(220, 20, 60))
                elif priority == 'low':
                    item.setForeground(QColor(0, 128, 0))
                self.list_widget.addItem(item)
            current_cat = self.combo_category.currentData()
            self.combo_category.blockSignals(True)
            self.combo_category.clear()
            self.combo_category.addItem('Все', 'all')
            for cat in sorted(categories):
                self.combo_category.addItem(cat, cat)
            if current_cat:
                idx = self.combo_category.findData(current_cat)
                if idx >= 0:
                    self.combo_category.setCurrentIndex(idx)
            self.combo_category.blockSignals(False)
        except Exception as e:
            logger.error(f'load_wishlist: {e}', exc_info=True)

    def _show_details(self, item):
        if not item:
            return
        try:
            item_id = item.data(Qt.ItemDataRole.UserRole)
            data = database.get_wishlist_by_id(item_id)
            if not data:
                return
            item_id, title, description, category, priority, status, created_at = data
            self.lbl_title.setText(f'<b>Название:</b> {title or "-"}')
            self.lbl_desc.setText(f'<b>Описание:</b> {description or "-"}')
            self.lbl_desc.setWordWrap(True)
            self.lbl_category.setText(f'<b>Категория:</b> {category or "Другое"}')
            priority_display = {'high': 'Высокий', 'medium': 'Средний', 'low': 'Низкий'}.get(priority, priority)
            self.lbl_priority.setText(f'<b>Приоритет:</b> {priority_display}')
            self.lbl_status.setText(f'<b>Статус:</b> {"Выполнено" if status == "done" else "Активно"}')
            self.lbl_date.setText(f'<b>Дата:</b> {created_at or "-"}')
            self.btn_done.setText('Восстановить' if status == 'done' else 'Выполнено')
        except Exception as e:
            logger.error(f'show_wishlist_detail: {e}', exc_info=True)

    def _add(self):
        try:
            dlg = WishlistDialog(self.mw)
            if dlg.exec():
                data = dlg.get_data()
                if not data['title']:
                    QMessageBox.warning(self.mw, 'Ошибка', 'Название не может быть пустым')
                    return
                database.add_wishlist_item(data['title'], data['description'], data['category'], data['priority'])
                self.load()
        except Exception as e:
            logger.error(f'add_wishlist_item: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))

    def _edit(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        try:
            item_id = item.data(Qt.ItemDataRole.UserRole)
            data = database.get_wishlist_by_id(item_id)
            if not data:
                return
            dlg = WishlistDialog(self.mw, data)
            if dlg.exec():
                new_data = dlg.get_data()
                database.update_wishlist_item(item_id, new_data['title'], new_data['description'],
                                             new_data['category'], new_data['priority'], data[5])
                self.load()
        except Exception as e:
            logger.error(f'edit_wishlist_item: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))

    def _delete(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        try:
            item_id = item.data(Qt.ItemDataRole.UserRole)
            reply = QMessageBox.question(self.mw, 'Удаление', 'Удалить желание?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                database.delete_wishlist_item(item_id)
                self.load()
                self.lbl_title.setText('Название: -')
                self.lbl_desc.setText('Описание: -')
        except Exception as e:
            logger.error(f'delete_wishlist_item: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))

    def _toggle_done(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        try:
            item_id = item.data(Qt.ItemDataRole.UserRole)
            data = database.get_wishlist_by_id(item_id)
            if not data:
                return
            new_status = 'pending' if data[5] == 'done' else 'done'
            database.update_wishlist_item(item_id, data[1], data[2], data[3], data[4], new_status)
            self.load()
            for i in range(self.list_widget.count()):
                new_item = self.list_widget.item(i)
                if new_item.data(Qt.ItemDataRole.UserRole) == item_id:
                    self.list_widget.setCurrentItem(new_item)
                    self._show_details(new_item)
                    break
        except Exception as e:
            logger.error(f'toggle_wishlist_done: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))
