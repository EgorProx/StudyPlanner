import sys
import os
import logging
from datetime import datetime
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QLineEdit, QFormLayout,
                             QMessageBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QDoubleSpinBox, QTextEdit,
                             QGroupBox, QGridLayout, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush, QFont
import database

logger = logging.getLogger(__name__)


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


class GradeStatistics:
    def __init__(self):
        self.data = None

    def load_statistics(self, subject_id=None, semester=None):
        self.data = database.get_grade_statistics(subject_id, semester)
        return self.data

    def get_overall_average(self, semester=None):
        stats = self.load_statistics(semester=semester)
        if not stats:
            return 0.0
        total = sum(row[1] for row in stats)
        return round(total / len(stats), 2)

    def get_weighted_overall(self, semester=None):
        stats = self.load_statistics(semester=semester)
        if not stats:
            return 0.0
        total_weighted = sum(row[5] for row in stats if row[5])
        return round(total_weighted / len(stats), 2)

    def get_grade_distribution(self, semester=None):
        grades = database.get_all_grades(semester=semester)
        distribution = {'5': 0, '4': 0, '3': 0, '2': 0, 'other': 0}
        for g in grades:
            val = float(g[2])
            if val >= 4.5:
                distribution['5'] += 1
            elif val >= 3.5:
                distribution['4'] += 1
            elif val >= 2.5:
                distribution['3'] += 1
            elif val >= 1.5:
                distribution['2'] += 1
            else:
                distribution['other'] += 1
        return distribution

    def get_performance_level(self, average):
        if average >= 4.5:
            return 'Отлично', QColor(0, 128, 0)
        elif average >= 3.5:
            return 'Хорошо', QColor(0, 100, 200)
        elif average >= 2.5:
            return 'Удовлетворительно', QColor(200, 150, 0)
        else:
            return 'Неудовлетворительно', QColor(200, 0, 0)