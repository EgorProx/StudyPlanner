import logging
import database
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QComboBox, QLineEdit, QFileDialog, QTextEdit, QApplication)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

logger = logging.getLogger(__name__)


class SettingsPage:
    def __init__(self, mw):
        self.mw = mw
        self._setup_ui()

    def _setup_ui(self):
        page = self.mw.ui.page_settings
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        layout.addWidget(QLabel('<h2>Настройки</h2>'))
        layout.addWidget(QLabel('Оформление:'))
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(['light', 'dark'])
        self.combo_theme.currentTextChanged.connect(self._change_theme)
        layout.addWidget(self.combo_theme)
        layout.addSpacing(20)
        layout.addWidget(QLabel('Рабочая папка:'))
        path_layout = QHBoxLayout()
        self.edit_path = QLineEdit()
        self.edit_path.setReadOnly(True)
        btn_browse = QPushButton('Обзор...')
        btn_browse.clicked.connect(self._browse_folder)
        path_layout.addWidget(self.edit_path)
        path_layout.addWidget(btn_browse)
        layout.addLayout(path_layout)
        layout.addSpacing(20)
        layout.addWidget(QLabel('OpenRouter API:'))
        api_layout = QHBoxLayout()
        self.edit_api_key = QLineEdit()
        self.edit_api_key.setPlaceholderText('Введите API-ключ OpenRouter...')
        self.edit_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_api_key.textChanged.connect(self._on_api_key_changed)
        api_layout.addWidget(self.edit_api_key)
        self.btn_api_key = QPushButton('Показать/скрыть')
        self.btn_api_key.clicked.connect(self._toggle_api_key_visibility)
        api_layout.addWidget(self.btn_api_key)
        layout.addLayout(api_layout)
        layout.addStretch()

    def load_data(self):
        self.combo_theme.setCurrentText(self.mw.current_theme)
        self.edit_path.setText(self.mw.storage_path)
        self.edit_api_key.setText(database.get_setting('openrouter_api_key', ''))

    def _change_theme(self, theme):
        self.mw.current_theme = theme
        app = QApplication.instance()
        from ui.styles import STYLES
        app.setStyleSheet(STYLES.get(theme, STYLES['light']))
        database.save_setting('theme', theme)
        self.mw.tasks_page.load()

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self.mw, 'Выберите папку')
        if folder:
            self.mw.storage_path = folder
            self.edit_path.setText(folder)
            database.save_setting('path', folder)

    def _on_api_key_changed(self, text):
        database.save_setting('openrouter_api_key', text.strip())

    def _toggle_api_key_visibility(self):
        if self.edit_api_key.echoMode() == QLineEdit.EchoMode.Password:
            self.edit_api_key.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.edit_api_key.setEchoMode(QLineEdit.EchoMode.Password)
