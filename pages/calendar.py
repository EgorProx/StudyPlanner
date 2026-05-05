import logging
import database
from PyQt6.QtWidgets import (QVBoxLayout, QLabel, QCalendarWidget)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QTextCharFormat, QColor, QBrush

logger = logging.getLogger(__name__)


class CalendarPage:
    def __init__(self, mw):
        self.mw = mw
        self._setup_ui()

    def _setup_ui(self):
        page = self.mw.ui.page_calendar
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.addWidget(QLabel('<h2>Календарь дедлайнов</h2>'))
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        layout.addWidget(self.calendar)
        self.lbl_date = QLabel('Выберите дату')
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_date)
        self.calendar.clicked.connect(self._on_date_click)

    def update_deadlines(self):
        try:
            self.calendar.setDateTextFormat(QDate(), QTextCharFormat())
            tasks = database.get_all_tasks()
            for task in tasks:
                date_str = task[2]
                if date_str:
                    try:
                        y, m, d = map(int, date_str.split('-'))
                        qdate = QDate(y, m, d)
                        fmt = QTextCharFormat()
                        fmt.setBackground(QColor('#ffcccc'))
                        if self.mw.current_theme == 'dark':
                            fmt.setForeground(QBrush(QColor('white')))
                        self.calendar.setDateTextFormat(qdate, fmt)
                    except ValueError:
                        pass
        except Exception as e:
            logger.error(f'update_calendar_deadlines: {e}', exc_info=True)

    def _on_date_click(self, date):
        try:
            date_str = date.toString('yyyy-MM-dd')
            tasks = database.get_all_tasks()
            task_names = [t[1] for t in tasks if t[2] == date_str]
            if task_names:
                self.lbl_date.setText(f'<b>{date.toString("dddd, d MMMM yyyy")}</b><br>Задачи: {", ".join(task_names)}')
            else:
                self.lbl_date.setText(f'{date.toString("dddd, d MMMM yyyy")}<br>Нет задач')
        except Exception as e:
            logger.error(f'on_date_click: {e}', exc_info=True)
