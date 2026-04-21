# notifications.py
import sys
import os
import logging
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QSystemTrayIcon, QMenu, QMessageBox, QDialog,
                             QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QListWidget, QListWidgetItem, QApplication)
from PyQt6.QtCore import QTimer, Qt, QDate
from PyQt6.QtGui import QIcon, QAction
import database

logger = logging.getLogger(__name__)


class NotificationDialog(QDialog):
    """Диалог с уведомлениями о приближающихся дедлайнах"""

    def __init__(self, notifications, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Уведомления")
        self.resize(500, 400)
        self.notifications = notifications

        layout = QVBoxLayout(self)

        # Заголовок
        header = QLabel(f"<h2>У вас {len(notifications)} уведомлений</h2>")
        layout.addWidget(header)

        # Список уведомлений
        self.list_widget = QListWidget()
        for notif in notifications:
            item_text = f"[{notif['urgency']}] {notif['title']}\n"
            item_text += f"   Предмет: {notif['subject'] or 'Без предмета'} | Срок: {notif['due_date']}"
            list_item = QListWidgetItem(item_text)

            # Цвет в зависимости от срочности
            if notif['urgency'] == 'СЕГОДНЯ':
                list_item.setForeground(Qt.GlobalColor.red)
            elif notif['urgency'] == 'ЗАВТРА':
                list_item.setForeground(Qt.GlobalColor.darkYellow)
            else:
                list_item.setForeground(Qt.GlobalColor.darkGreen)

            self.list_widget.addItem(list_item)

        layout.addWidget(self.list_widget)

        # Кнопки
        btn_layout = QHBoxLayout()

        btn_refresh = QPushButton("Обновить")
        btn_refresh.clicked.connect(self.refresh)
        btn_layout.addWidget(btn_refresh)

        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def refresh(self):
        self.close()
        # Пересоздаем диалог с новыми данными
        new_notifications = NotificationManager.check_deadlines()
        if new_notifications:
            dialog = NotificationDialog(new_notifications, self.parent())
            dialog.exec()
        else:
            QMessageBox.information(self.parent(), "Уведомления", "Нет новых уведомлений")


class NotificationManager:
    """Менеджер уведомлений для Study Planner"""

    def __init__(self, parent_window=None):
        self.parent = parent_window
        self.tray_icon = None
        self.timer = None
        self.last_check_date = None
        self.checked_tasks_today = set()  # Чтобы не повторять уведомления

    def initialize(self):
        """Инициализация системы уведомлений"""
        logger.info("Инициализация NotificationManager")

        # Создаем иконку в трее
        self.tray_icon = QSystemTrayIcon(self.parent)
        # Используем стандартную иконку, так как нет кастомной
        self.tray_icon.setIcon(self.parent.style().standardIcon(
            self.parent.style().StandardPixmap.SP_ComputerIcon))

        # Контекстное меню для трея
        tray_menu = QMenu()

        show_action = QAction("Показать окно", self.parent)
        show_action.triggered.connect(self.parent.show)
        tray_menu.addAction(show_action)

        check_action = QAction("Проверить дедлайны", self.parent)
        check_action.triggered.connect(self.manual_check)
        tray_menu.addAction(check_action)

        tray_menu.addSeparator()

        quit_action = QAction("Выход", self.parent)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)

        # Показываем иконку
        self.tray_icon.show()

        # Настраиваем таймер для автоматической проверки (каждые 30 минут)
        self.timer = QTimer(self.parent)
        self.timer.timeout.connect(self.auto_check)
        self.timer.start(30 * 60 * 1000)  # 30 минут в миллисекундах

        # Проверяем при запуске (с задержкой, чтобы окно успело загрузиться)
        QTimer.singleShot(5000, self.initial_check)

        logger.info("NotificationManager инициализирован")

    def on_tray_activated(self, reason):
        """Обработка клика по иконке в трее"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.parent.show()
            self.parent.raise_()
            self.parent.activateWindow()

    def show_tray_message(self, title, message, icon=QSystemTrayIcon.MessageIcon.Information):
        """Показывает всплывающее уведомление"""
        if self.tray_icon and self.tray_icon.supportsMessages():
            self.tray_icon.showMessage(title, message, icon, 10000)  # 10 секунд

    @staticmethod
    def check_deadlines():
        """Проверяет дедлайны и возвращает список уведомлений"""
        notifications = []

        try:
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)
            week_later = today + timedelta(days=7)

            # Получаем все активные невыполненные задачи
            tasks = database.get_all_tasks(status_filter='active')

            for task in tasks:
                task_id, title, due_date_str, subject_name, status, completed = task

                # Пропускаем выполненные
                if completed:
                    continue

                if not due_date_str:
                    continue

                try:
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                    days_until = (due_date - today).days

                    if days_until < 0:
                        # Просрочено
                        notifications.append({
                            'id': task_id,
                            'title': title,
                            'due_date': due_date_str,
                            'subject': subject_name,
                            'urgency': 'ПРОСРОЧЕНО',
                            'days': days_until
                        })
                    elif days_until == 0:
                        # Сегодня
                        notifications.append({
                            'id': task_id,
                            'title': title,
                            'due_date': due_date_str,
                            'subject': subject_name,
                            'urgency': 'СЕГОДНЯ',
                            'days': 0
                        })
                    elif days_until == 1:
                        # Завтра
                        notifications.append({
                            'id': task_id,
                            'title': title,
                            'due_date': due_date_str,
                            'subject': subject_name,
                            'urgency': 'ЗАВТРА',
                            'days': 1
                        })
                    elif days_until <= 3:
                        # Через 2-3 дня
                        notifications.append({
                            'id': task_id,
                            'title': title,
                            'due_date': due_date_str,
                            'subject': subject_name,
                            'urgency': f'ЧЕРЕЗ {days_until} ДНЯ',
                            'days': days_until
                        })

                except ValueError:
                    logger.warning(f"Неверный формат даты: {due_date_str}")
                    continue

        except Exception as e:
            logger.error(f"Ошибка при проверке дедлайнов: {e}", exc_info=True)

        # Сортируем: сначала просроченные, потом по срочности
        urgency_order = {'ПРОСРОЧЕНО': 0, 'СЕГОДНЯ': 1, 'ЗАВТРА': 2, 
                        'ЧЕРЕЗ 2 ДНЯ': 3, 'ЧЕРЕЗ 3 ДНЯ': 4}
        notifications.sort(key=lambda x: urgency_order.get(x['urgency'], 99))

        return notifications

    def initial_check(self):
        """Начальная проверка при запуске приложения"""
        logger.info("Начальная проверка дедлайнов")
        notifications = self.check_deadlines()

        if notifications:
            urgent = [n for n in notifications if n['urgency'] in ['ПРОСРОЧЕНО', 'СЕГОДНЯ', 'ЗАВТРА']]

            if urgent:
                # Показываем трей-уведомление
                self.show_tray_message(
                    "Study Planner - Дедлайны",
                    f"У вас {len(urgent)} срочные задачи!",
                    QSystemTrayIcon.MessageIcon.Warning
                )

                # Показываем диалог с уведомлениями
                dialog = NotificationDialog(notifications, self.parent)
                dialog.exec()
            else:
                # Только трей для менее срочных
                self.show_tray_message(
                    "Study Planner",
                    f"У вас {len(notifications)} задач на этой неделе",
                    QSystemTrayIcon.MessageIcon.Information
                )

    def auto_check(self):
        """Автоматическая проверка по таймеру"""
        logger.debug("Автоматическая проверка дедлайнов")

        today = datetime.now().date()

        # Сбрасываем проверенные задачи, если день сменился
        if self.last_check_date != today:
            self.checked_tasks_today.clear()
            self.last_check_date = today

        notifications = self.check_deadlines()

        # Фильтруем уже показанные сегодня
        new_notifications = []
        for n in notifications:
            if n['id'] not in self.checked_tasks_today and n['urgency'] in ['ПРОСРОЧЕНО', 'СЕГОДНЯ']:
                new_notifications.append(n)
                self.checked_tasks_today.add(n['id'])

        if new_notifications:
            self.show_tray_message(
                "Study Planner - Срочно!",
                f"{len(new_notifications)} задач требуют внимания!",
                QSystemTrayIcon.MessageIcon.Critical
            )

    def manual_check(self):
        """Ручная проверка по запросу пользователя"""
        logger.info("Ручная проверка дедлайнов")
        notifications = self.check_deadlines()

        if notifications:
            dialog = NotificationDialog(notifications, self.parent)
            dialog.exec()
        else:
            QMessageBox.information(self.parent, "Уведомления", 
                                   "Нет активных задач с дедлайнами на ближайшую неделю")

    def show_menu_notification(self):
        """Показывает уведомления при клике на меню"""
        self.manual_check()

    def cleanup(self):
        """Очистка при закрытии"""
        if self.timer:
            self.timer.stop()
        if self.tray_icon:
            self.tray_icon.hide()
