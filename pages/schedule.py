import logging
import database
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QComboBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QGroupBox, QMessageBox, QInputDialog,
                             QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor

from ui.schedule_parser import WeekCalculator, SfuScheduleParser
from ui.dialogs import ScheduleEntryDialog

logger = logging.getLogger(__name__)


class SchedulePage:
    def __init__(self, mw):
        self.mw = mw
        self.schedule_map = {}
        self._setup_ui()

    def _setup_ui(self):
        page = self.mw.ui.page_schedule
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel('<h2>Расписание занятий</h2>'))

        week_group = QGroupBox('')
        week_layout = QHBoxLayout(week_group)
        week_layout.setContentsMargins(8, 4, 8, 4)
        self.lbl_current_week = QLabel()
        self.lbl_current_week.setMinimumWidth(80)
        self._update_week_label()
        week_layout.addWidget(self.lbl_current_week)
        week_group.setFixedWidth(100)
        top_layout.addWidget(week_group)
        top_layout.addStretch()

        self.combo_week_filter = QComboBox()
        self.combo_week_filter.addItem('Все недели', 'all')
        self.combo_week_filter.addItem('Четная', 'even')
        self.combo_week_filter.addItem('Нечетная', 'odd')
        self.combo_week_filter.currentIndexChanged.connect(self.load)
        top_layout.addWidget(QLabel('Фильтр:'))
        top_layout.addWidget(self.combo_week_filter)
        layout.addLayout(top_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(['Время', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton('Добавить занятие')
        self.btn_edit = QPushButton('Изменить')
        self.btn_del = QPushButton('Удалить')
        self.btn_import = QPushButton('Импорт из СФУ')
        self.btn_add.clicked.connect(self._add_entry)
        self.btn_edit.clicked.connect(self._edit_entry)
        self.btn_del.clicked.connect(self._delete_entry)
        self.btn_import.clicked.connect(self._import_sfu)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_del)
        btn_layout.addWidget(self.btn_import)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.lbl_details = QLabel('Выберите ячейку для просмотра деталей')
        self.lbl_details.setStyleSheet('padding: 10px; border: 1px solid #ccc; border-radius: 4px;')
        layout.addWidget(self.lbl_details)

    def _update_week_label(self):
        week_type = WeekCalculator.get_current_week_parity()
        week_name = 'Четная' if week_type == 'even' else 'Нечетная'
        self.lbl_current_week.setText(f'<b>{week_name}</b>')
        self.mw.lbl_current_week = self.lbl_current_week

    def load(self):
        try:
            week_filter = self.combo_week_filter.currentData()
            if week_filter == 'all':
                week_filter = None
            data = database.get_schedule(week_type=week_filter)
            self.schedule_map = {}
            for row in data:
                entry_id, subject_id, day, week_type, start_time = row[0], row[1], row[2], row[3], row[4]
                subject_name = row[9]
                room = row[6] or ''
                lesson_type = row[7] or ''
                key = (day, start_time)
                if key not in self.schedule_map:
                    self.schedule_map[key] = []
                self.schedule_map[key].append({
                    'id': entry_id, 'subject': subject_name, 'room': room,
                    'type': lesson_type, 'week': week_type, 'end_time': row[5] or ''
                })
            self._refresh_table()
            self._update_week_label()
        except Exception as e:
            logger.error(f'load_schedule: {e}', exc_info=True)

    def _refresh_table(self):
        self.table.setRowCount(0)
        all_times = set()
        for (day, start_time) in self.schedule_map.keys():
            all_times.add(start_time)
        if not all_times:
            time_slots = ['08:00', '09:00', '10:00', '11:00', '12:00',
                          '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00']
        else:
            time_slots = sorted(all_times)
        self.table.setRowCount(len(time_slots))
        for row_idx, time_str in enumerate(time_slots):
            time_item = QTableWidgetItem(time_str)
            time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row_idx, 0, time_item)
            for day in range(7):
                key = (day, time_str)
                if key in self.schedule_map:
                    entries = self.schedule_map[key]
                    texts = []
                    for entry in entries:
                        week_marker = ''
                        if entry['week'] == 'even':
                            week_marker = ' (чет)'
                        elif entry['week'] == 'odd':
                            week_marker = ' (нечет)'
                        text = f"{entry['subject']}{week_marker}\n{entry['type']}\n{entry['room']}"
                        texts.append(text)
                    cell_text = '\n---\n'.join(texts)
                    item = QTableWidgetItem(cell_text)
                    item.setData(Qt.ItemDataRole.UserRole, [e['id'] for e in entries])
                    last_entry = entries[-1]
                    if last_entry['week'] == 'even':
                        item.setBackground(QBrush(QColor(200, 230, 255)))
                    elif last_entry['week'] == 'odd':
                        item.setBackground(QBrush(QColor(255, 230, 200)))
                    else:
                        item.setBackground(QBrush(QColor(220, 255, 220)))
                    self.table.setItem(row_idx, day + 1, item)
        self.table.resizeRowsToContents()

    def _on_cell_clicked(self, row, column):
        if column == 0:
            return
        item = self.table.item(row, column)
        if not item:
            self.lbl_details.setText('Нет занятий в это время')
            return
        entry_ids = item.data(Qt.ItemDataRole.UserRole)
        if not entry_ids:
            return
        details_text = ''
        for entry_id in entry_ids:
            data = database.get_schedule_by_id(entry_id)
            if data:
                week_name = WeekCalculator.format_week_type(data[3])
                details_text += f"<b>{data[9]}</b><br>"
                details_text += f"Тип: {data[7] or '-'}<br>"
                details_text += f"Время: {data[4] or '-'} - {data[5] or '-'}<br>"
                details_text += f"Аудитория: {data[6] or '-'}<br>"
                details_text += f"Неделя: {week_name}<br>"
                details_text += f"Преподаватель: {data[10] or '-'}<br>"
                details_text += '<hr>'
        self.lbl_details.setText(details_text)

    def _add_entry(self):
        try:
            subjects = database.get_all_subjects()
            if not subjects:
                QMessageBox.warning(self.mw, 'Ошибка', 'Сначала добавьте предметы в разделе Предметы')
                return
            dlg = ScheduleEntryDialog(self.mw, subjects)
            if dlg.exec():
                data = dlg.get_data()
                database.add_schedule_entry(**data)
                self.load()
        except Exception as e:
            logger.error(f'add_schedule_entry: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))

    def _edit_entry(self):
        try:
            current = self.table.currentItem()
            if not current:
                QMessageBox.warning(self.mw, 'Ошибка', 'Выберите занятие в таблице')
                return
            entry_ids = current.data(Qt.ItemDataRole.UserRole)
            if not entry_ids:
                return
            entry_id = entry_ids[0]
            data = database.get_schedule_by_id(entry_id)
            if not data:
                return
            subjects = database.get_all_subjects()
            dlg = ScheduleEntryDialog(self.mw, subjects, data)
            if dlg.exec():
                new_data = dlg.get_data()
                database.update_schedule_entry(entry_id, **new_data)
                self.load()
        except Exception as e:
            logger.error(f'edit_schedule_entry: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))

    def _delete_entry(self):
        try:
            current = self.table.currentItem()
            if not current:
                QMessageBox.warning(self.mw, 'Ошибка', 'Выберите занятие в таблице')
                return
            entry_ids = current.data(Qt.ItemDataRole.UserRole)
            if not entry_ids:
                return
            entry_id = entry_ids[0]
            reply = QMessageBox.question(self.mw, 'Удаление', 'Удалить занятие из расписания?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                database.delete_schedule_entry(entry_id)
                self.load()
                self.lbl_details.setText('Выберите ячейку для просмотра деталей')
        except Exception as e:
            logger.error(f'delete_schedule_entry: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))

    def _import_sfu(self):
        try:
            source_type, ok = QInputDialog.getItem(
                self.mw, 'Импорт расписания СФУ', 'Источник:',
                ['HTML-файл страницы расписания', 'URL страницы расписания'], 0, False)
            if not ok:
                return
            parser = SfuScheduleParser()
            if source_type.startswith('HTML'):
                filepath, _ = QFileDialog.getOpenFileName(
                    self.mw, 'Выберите HTML-файл расписания', '',
                    'HTML и текстовые файлы (*.html *.htm *.txt);;Все файлы (*)')
                if not filepath:
                    return
                entries = parser.parse_file(filepath)
            else:
                url, ok = QInputDialog.getText(self.mw, 'URL расписания СФУ', 'Ссылка на страницу:')
                if not ok or not url.strip():
                    return
                entries = parser.parse_url(url.strip())
            if not entries:
                QMessageBox.warning(self.mw, 'Импорт расписания', 'В выбранном источнике не найдено занятий.')
                return
            reply = QMessageBox.question(
                self.mw, 'Импорт расписания',
                f'Найдено занятий: {len(entries)}.\nОчистить текущее расписание перед импортом?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                database.clear_schedule()
            imported, errors = parser.import_to_database(entries, create_missing_subjects=True)
            self.mw.subjects_page.load()
            self.load()
            message = f'Импортировано занятий: {imported} из {len(entries)}.'
            if errors:
                message += '\n\nОшибки:\n' + '\n'.join(errors[:5])
                if len(errors) > 5:
                    message += f'\n...и еще {len(errors) - 5}'
            QMessageBox.information(self.mw, 'Импорт расписания', message)
        except Exception as e:
            logger.error(f'import_schedule_from_sfu: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))
