import logging
import types
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QLineEdit, QFormLayout,
                             QMessageBox, QDialogButtonBox, QGroupBox, QRadioButton,
                             QButtonGroup, QDoubleSpinBox)
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


class TaskDialog(QDialog):
    def __init__(self, parent=None, subjects=None, task_data=None):
        super().__init__(parent)
        self.setWindowTitle('Задача')
        self.resize(300, 200)
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.input_title = QLineEdit()
        self.input_date = QLineEdit()
        self.input_date.setPlaceholderText('ГГГГ-ММ-ДД')
        self.combo_subject = QComboBox()
        self.subjects_map = {}
        if subjects:
            for sub in subjects:
                self.combo_subject.addItem(sub[1], sub[0])
                self.subjects_map[sub[1]] = sub[0]
        self.combo_subject.addItem('Без предмета', None)
        self.input_desc = QLineEdit()
        form_layout.addRow('Название:', self.input_title)
        form_layout.addRow('Срок:', self.input_date)
        form_layout.addRow('Предмет:', self.combo_subject)
        form_layout.addRow('Описание:', self.input_desc)
        layout.addLayout(form_layout)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        if task_data:
            self.input_title.setText(task_data[1])
            self.input_date.setText(task_data[2] if task_data[2] else '')
            self.input_desc.setText(task_data[4] if len(task_data) > 4 else '')
            if task_data[3]:
                index = self.combo_subject.findText(task_data[3])
                if index >= 0:
                    self.combo_subject.setCurrentIndex(index)
            else:
                self.combo_subject.setCurrentText('Без предмета')

    def get_data(self):
        subject_id = self.combo_subject.currentData()
        return {
            'title': self.input_title.text(),
            'due_date': self.input_date.text(),
            'subject_id': subject_id,
            'description': self.input_desc.text()
        }


class SearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Глобальный поиск')
        self.resize(400, 100)
        self.parent_window = parent
        layout = QVBoxLayout(self)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Введите текст для поиска...')
        self.search_input.returnPressed.connect(self.perform_search)
        layout.addWidget(self.search_input)
        btn_search = QPushButton('Найти')
        btn_search.clicked.connect(self.perform_search)
        layout.addWidget(btn_search)
        self.search_input.setFocus()

    def perform_search(self):
        query = self.search_input.text().strip()
        if not query:
            return
        import database
        results = database.global_search(query)
        self.close()
        if not results:
            QMessageBox.information(self.parent_window, 'Поиск', 'Ничего не найдено')
            return
        results_dialog = SearchResultsDialog(self.parent_window, results)
        results_dialog.exec()


class SearchResultsDialog(QDialog):
    def __init__(self, parent=None, results=None):
        super().__init__(parent)
        self.setWindowTitle('Результаты поиска')
        self.resize(400, 300)
        self.parent_window = parent
        layout = QVBoxLayout(self)
        from PyQt6.QtWidgets import QListWidget
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        self.results_map = {}
        if results:
            for i, item in enumerate(results):
                try:
                    item_id, name, item_type, extra = item
                    if item_type == 'subject':
                        display_text = f'[Предмет] {name}'
                        self.list_widget.addItem(display_text)
                        self.results_map[self.list_widget.count() - 1] = ('subject', item_id)
                    elif item_type == 'task':
                        display_text = f'[Задание] {name}'
                        if extra:
                            display_text += f' (Предмет: {extra})'
                        self.list_widget.addItem(display_text)
                        self.results_map[self.list_widget.count() - 1] = ('task', item_id)
                except Exception as e:
                    logger.error(f'Error processing item {i}: {e}')
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.list_widget.itemDoubleClicked.connect(self.on_item_clicked)
        btn_close = QPushButton('Закрыть')
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

    def on_item_clicked(self, item):
        row = self.list_widget.row(item)
        if row in self.results_map:
            item_type, item_id = self.results_map[row]
            self.parent_window.navigate_to_item(item_type, item_id)
            self.close()


class WishlistDialog(QDialog):
    def __init__(self, parent=None, item_data=None):
        super().__init__(parent)
        self.setWindowTitle('Редактирование желания' if item_data else 'Новое желание')
        self.resize(400, 350)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.input_title = QLineEdit()
        self.input_title.setPlaceholderText('Название желания')
        form.addRow('Название:', self.input_title)
        self.input_desc = QLineEdit()
        self.input_desc.setPlaceholderText('Описание...')
        form.addRow('Описание:', self.input_desc)
        self.combo_category = QComboBox()
        self.combo_category.addItems(['Учеба', 'Личное', 'Книги', 'Навыки', 'Проекты', 'Другое'])
        self.combo_category.setEditable(True)
        form.addRow('Категория:', self.combo_category)
        self.combo_priority = QComboBox()
        self.combo_priority.addItems(['Высокий', 'Средний', 'Низкий'])
        self.combo_priority.setCurrentIndex(1)
        form.addRow('Приоритет:', self.combo_priority)
        layout.addLayout(form)
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton('Сохранить')
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton('Отмена')
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        if item_data:
            self.load_data(item_data)

    def load_data(self, data):
        item_id, title, description, category, priority, status, created_at = data
        self.input_title.setText(title or '')
        self.input_desc.setText(description or '')
        if category:
            idx = self.combo_category.findText(category)
            if idx >= 0:
                self.combo_category.setCurrentIndex(idx)
            else:
                self.combo_category.setCurrentText(category)
        priority_map = {'high': 'Высокий', 'medium': 'Средний', 'low': 'Низкий'}
        priority_name = priority_map.get(priority, 'Средний')
        idx = self.combo_priority.findText(priority_name)
        if idx >= 0:
            self.combo_priority.setCurrentIndex(idx)

    def get_data(self):
        priority_map = {'Высокий': 'high', 'Средний': 'medium', 'Низкий': 'low'}
        return {
            'title': self.input_title.text(),
            'description': self.input_desc.text(),
            'category': self.combo_category.currentText(),
            'priority': priority_map.get(self.combo_priority.currentText(), 'medium')
        }


class ScheduleEntryDialog(QDialog):
    def __init__(self, parent=None, subjects=None, entry_data=None):
        super().__init__(parent)
        self.setWindowTitle('Редактирование занятия' if entry_data else 'Новое занятие')
        self.resize(400, 350)
        self.entry_data = entry_data
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.combo_subject = QComboBox()
        self.subjects_map = {}
        if subjects:
            for sub in subjects:
                self.combo_subject.addItem(sub[1], sub[0])
                self.subjects_map[sub[1]] = sub[0]
        form.addRow('Предмет:', self.combo_subject)
        self.combo_day = QComboBox()
        days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        for i, day in enumerate(days):
            self.combo_day.addItem(day, i)
        form.addRow('День недели:', self.combo_day)
        week_group = QGroupBox('Тип недели')
        week_layout = QHBoxLayout(week_group)
        self.week_group = QButtonGroup(self)
        self.radio_even = QRadioButton('Четная')
        self.radio_odd = QRadioButton('Нечетная')
        self.radio_both = QRadioButton('Каждую')
        self.radio_both.setChecked(True)
        self.week_group.addButton(self.radio_even)
        self.week_group.addButton(self.radio_odd)
        self.week_group.addButton(self.radio_both)
        week_layout.addWidget(self.radio_even)
        week_layout.addWidget(self.radio_odd)
        week_layout.addWidget(self.radio_both)
        form.addRow(week_group)
        self.input_start = QLineEdit()
        self.input_start.setPlaceholderText('09:00')
        form.addRow('Начало:', self.input_start)
        self.input_end = QLineEdit()
        self.input_end.setPlaceholderText('10:30')
        form.addRow('Конец:', self.input_end)
        self.input_room = QLineEdit()
        form.addRow('Аудитория:', self.input_room)
        self.combo_type = QComboBox()
        self.combo_type.addItems(['Лекция', 'Практика', 'Лабораторная', 'Семинар', 'Консультация', 'Экзамен', 'Зачет'])
        form.addRow('Тип занятия:', self.combo_type)
        self.input_group = QLineEdit()
        form.addRow('Группа:', self.input_group)
        layout.addLayout(form)
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton('Сохранить')
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton('Отмена')
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        if entry_data:
            self.load_data(entry_data)

    def load_data(self, data):
        entry_id, subject_id, day_of_week, week_type, start_time, end_time, room, lesson_type, group_name, sub_name, teacher = data
        index = self.combo_subject.findData(subject_id)
        if index >= 0:
            self.combo_subject.setCurrentIndex(index)
        self.combo_day.setCurrentIndex(day_of_week)
        if week_type == 'even':
            self.radio_even.setChecked(True)
        elif week_type == 'odd':
            self.radio_odd.setChecked(True)
        else:
            self.radio_both.setChecked(True)
        self.input_start.setText(start_time or '')
        self.input_end.setText(end_time or '')
        self.input_room.setText(room or '')
        if lesson_type:
            index = self.combo_type.findText(lesson_type)
            if index >= 0:
                self.combo_type.setCurrentIndex(index)
        self.input_group.setText(group_name or '')

    def get_data(self):
        week_type = 'both'
        if self.radio_even.isChecked():
            week_type = 'even'
        elif self.radio_odd.isChecked():
            week_type = 'odd'
        return {
            'subject_id': self.combo_subject.currentData(),
            'day_of_week': self.combo_day.currentIndex(),
            'week_type': week_type,
            'start_time': self.input_start.text(),
            'end_time': self.input_end.text(),
            'room': self.input_room.text(),
            'lesson_type': self.combo_type.currentText(),
            'group_name': self.input_group.text()
        }


class GradeDialog(QDialog):
    def __init__(self, parent=None, subjects=None, grade_data=None):
        super().__init__(parent)
        self.setWindowTitle('Редактирование оценки' if grade_data else 'Новая оценка')
        self.resize(400, 350)
        self.grade_data = grade_data
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.combo_subject = QComboBox()
        if subjects:
            for sub in subjects:
                self.combo_subject.addItem(sub[1], sub[0])
        form.addRow('Предмет:', self.combo_subject)
        self.spin_grade = QDoubleSpinBox()
        self.spin_grade.setRange(0, 100)
        self.spin_grade.setDecimals(1)
        self.spin_grade.setValue(5.0)
        form.addRow('Оценка:', self.spin_grade)
        self.combo_type = QComboBox()
        self.combo_type.addItems(['Экзамен', 'Зачет', 'Дифференцированный зачет', 'Курсовая', 'Контрольная', 'Домашняя работа', 'Лабораторная', 'Практика', 'Другое'])
        form.addRow('Тип:', self.combo_type)
        self.input_date = QLineEdit()
        self.input_date.setPlaceholderText('ГГГГ-ММ-ДД')
        form.addRow('Дата:', self.input_date)
        self.input_semester = QLineEdit()
        self.input_semester.setPlaceholderText('2025-весна')
        form.addRow('Семестр:', self.input_semester)
        self.spin_weight = QDoubleSpinBox()
        self.spin_weight.setRange(0.1, 10.0)
        self.spin_weight.setDecimals(1)
        self.spin_weight.setValue(1.0)
        form.addRow('Вес:', self.spin_weight)
        self.input_desc = QLineEdit()
        self.input_desc.setPlaceholderText('Комментарий...')
        form.addRow('Описание:', self.input_desc)
        layout.addLayout(form)
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton('Сохранить')
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton('Отмена')
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        if grade_data:
            self.load_data(grade_data)

    def load_data(self, data):
        grade_id, subject_id, grade, grade_type, date, semester, weight, description, sub_name = data
        index = self.combo_subject.findData(subject_id)
        if index >= 0:
            self.combo_subject.setCurrentIndex(index)
        self.spin_grade.setValue(float(grade))
        if grade_type:
            idx = self.combo_type.findText(grade_type)
            if idx >= 0:
                self.combo_type.setCurrentIndex(idx)
        self.input_date.setText(date or '')
        self.input_semester.setText(semester or '')
        self.spin_weight.setValue(float(weight) if weight else 1.0)
        self.input_desc.setText(description or '')

    def get_data(self):
        return {
            'subject_id': self.combo_subject.currentData(),
            'grade': self.spin_grade.value(),
            'grade_type': self.combo_type.currentText(),
            'date': self.input_date.text(),
            'semester': self.input_semester.text(),
            'weight': self.spin_weight.value(),
            'description': self.input_desc.text()
        }
