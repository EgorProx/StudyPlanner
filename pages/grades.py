import logging
import database
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QComboBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QSplitter, QWidget, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor

from ui.dialogs import GradeDialog
from ui.grade_statistics import GradeStatistics

logger = logging.getLogger(__name__)


class GradesPage:
    def __init__(self, mw):
        self.mw = mw
        self.grades_map = {}
        self.selected_grade_id = None
        self._setup_ui()

    def _setup_ui(self):
        page = self.mw.ui.page_grades
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel('<h2>Журнал оценок</h2>'))
        top_layout.addStretch()
        top_layout.addWidget(QLabel('Семестр:'))
        self.combo_semester = QComboBox()
        self.combo_semester.addItem('Все', None)
        self.combo_semester.currentIndexChanged.connect(self.load)
        top_layout.addWidget(self.combo_semester)
        layout.addLayout(top_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel('<b>Список оценок</b>'))
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['Предмет', 'Оценка', 'Тип', 'Дата', 'Семестр', 'Вес'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemClicked.connect(self._on_grade_selected)
        left_layout.addWidget(self.table)
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
        left_layout.addLayout(btn_layout)
        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel('<b>Статистика</b>'))
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(6)
        self.stats_table.setHorizontalHeaderLabels(['Предмет', 'Среднее', 'Кол-во', 'Мин', 'Макс', 'Взвешенное'])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        self.stats_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        right_layout.addWidget(self.stats_table)
        self.lbl_overall = QLabel('Общий средний балл: -')
        self.lbl_overall.setStyleSheet('font-size: 14px; padding: 10px;')
        right_layout.addWidget(self.lbl_overall)
        self.lbl_performance = QLabel('Успеваемость: -')
        self.lbl_performance.setStyleSheet('font-size: 14px; padding: 10px;')
        right_layout.addWidget(self.lbl_performance)
        right_layout.addStretch()
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 400])
        layout.addWidget(splitter)

    def load(self):
        try:
            semester = self.combo_semester.currentData()
            data = database.get_all_grades(semester=semester)
            self.table.setRowCount(len(data))
            self.grades_map = {}
            for row_idx, row in enumerate(data):
                grade_id, subject_id, grade, grade_type, date, sem, weight, description, sub_name = row
                self.table.setItem(row_idx, 0, QTableWidgetItem(sub_name or ''))
                grade_item = QTableWidgetItem(str(grade))
                grade_val = float(grade)
                if grade_val >= 4.5:
                    grade_item.setForeground(QBrush(QColor(0, 128, 0)))
                elif grade_val >= 3.5:
                    grade_item.setForeground(QBrush(QColor(0, 100, 200)))
                elif grade_val >= 2.5:
                    grade_item.setForeground(QBrush(QColor(200, 150, 0)))
                else:
                    grade_item.setForeground(QBrush(QColor(200, 0, 0)))
                self.table.setItem(row_idx, 1, grade_item)
                self.table.setItem(row_idx, 2, QTableWidgetItem(grade_type or ''))
                self.table.setItem(row_idx, 3, QTableWidgetItem(date or ''))
                self.table.setItem(row_idx, 4, QTableWidgetItem(sem or ''))
                self.table.setItem(row_idx, 5, QTableWidgetItem(str(weight or 1.0)))
                self.grades_map[row_idx] = grade_id
            self._load_statistics()
            self._update_semester_combo()
        except Exception as e:
            logger.error(f'load_grades: {e}', exc_info=True)

    def _update_semester_combo(self):
        current = self.combo_semester.currentData()
        self.combo_semester.blockSignals(True)
        self.combo_semester.clear()
        self.combo_semester.addItem('Все', None)
        for sem in database.get_semesters():
            self.combo_semester.addItem(sem, sem)
        if current:
            idx = self.combo_semester.findData(current)
            if idx >= 0:
                self.combo_semester.setCurrentIndex(idx)
        self.combo_semester.blockSignals(False)

    def _load_statistics(self):
        try:
            semester = self.combo_semester.currentData()
            stats = GradeStatistics()
            data = stats.load_statistics(semester=semester)
            self.stats_table.setRowCount(len(data))
            for row_idx, row in enumerate(data):
                sub_name, avg_grade, count, min_grade, max_grade, weighted_avg = row
                self.stats_table.setItem(row_idx, 0, QTableWidgetItem(sub_name or ''))
                self.stats_table.setItem(row_idx, 1, QTableWidgetItem(f'{avg_grade:.2f}' if avg_grade else '-'))
                self.stats_table.setItem(row_idx, 2, QTableWidgetItem(str(count or 0)))
                self.stats_table.setItem(row_idx, 3, QTableWidgetItem(str(min_grade) if min_grade else '-'))
                self.stats_table.setItem(row_idx, 4, QTableWidgetItem(str(max_grade) if max_grade else '-'))
                self.stats_table.setItem(row_idx, 5, QTableWidgetItem(f'{weighted_avg:.2f}' if weighted_avg else '-'))
            overall = stats.get_overall_average(semester=semester)
            self.lbl_overall.setText(f'Общий средний балл: <b>{overall:.2f}</b>')
            level, color = stats.get_performance_level(overall)
            self.lbl_performance.setText(f'Успеваемость: <b>{level}</b>')
            self.lbl_performance.setStyleSheet(f'font-size: 14px; padding: 10px; color: {color.name()};')
        except Exception as e:
            logger.error(f'load_statistics: {e}', exc_info=True)

    def _on_grade_selected(self, item):
        row = item.row()
        if row in self.grades_map:
            self.selected_grade_id = self.grades_map[row]

    def _add(self):
        try:
            subjects = database.get_all_subjects()
            if not subjects:
                QMessageBox.warning(self.mw, 'Ошибка', 'Сначала добавьте предметы')
                return
            dlg = GradeDialog(self.mw, subjects)
            if dlg.exec():
                data = dlg.get_data()
                database.add_grade(**data)
                self.load()
        except Exception as e:
            logger.error(f'add_grade: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))

    def _edit(self):
        try:
            selected = self.table.selectedItems()
            if not selected:
                QMessageBox.warning(self.mw, 'Ошибка', 'Выберите оценку')
                return
            row = selected[0].row()
            if row not in self.grades_map:
                return
            grade_id = self.grades_map[row]
            data = database.get_grade_by_id(grade_id)
            if not data:
                return
            subjects = database.get_all_subjects()
            dlg = GradeDialog(self.mw, subjects, data)
            if dlg.exec():
                new_data = dlg.get_data()
                database.update_grade(grade_id, **new_data)
                self.load()
        except Exception as e:
            logger.error(f'edit_grade: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))

    def _delete(self):
        try:
            selected = self.table.selectedItems()
            if not selected:
                QMessageBox.warning(self.mw, 'Ошибка', 'Выберите оценку')
                return
            row = selected[0].row()
            if row not in self.grades_map:
                return
            grade_id = self.grades_map[row]
            reply = QMessageBox.question(self.mw, 'Удаление', 'Удалить оценку?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                database.delete_grade(grade_id)
                self.load()
        except Exception as e:
            logger.error(f'delete_grade: {e}', exc_info=True)
            QMessageBox.critical(self.mw, 'Ошибка', str(e))
