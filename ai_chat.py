import logging
import json
import re
import urllib.request
import urllib.error
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QLineEdit, QTextEdit,
                             QFrame, QMessageBox, QSplitter, QDialog,
                             QFormLayout, QListWidget, QInputDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QTextCursor, QFont, QTextCharFormat

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions'


def load_custom_models():
    import database
    raw = database.get_setting('openrouter_models', '[]')
    try:
        models = json.loads(raw)
        if isinstance(models, list):
            return models
    except json.JSONDecodeError:
        pass
    return []


def save_custom_models(models):
    import database
    database.save_setting('openrouter_models', json.dumps(models, ensure_ascii=False))


def simple_markdown_to_html(text):
    lines = text.split('\n')
    result = []
    in_code_block = False
    code_lang = ''
    code_lines = []
    in_list = False

    for line in lines:
        if line.startswith('```'):
            if in_code_block:
                code_html = '<pre style="background:#1e1e1e;color:#d4d4d4;padding:8px;border-radius:4px;margin:4px 0;"><code>'
                code_html += '\n'.join(code_lines)
                code_html += '</code></pre>'
                result.append(code_html)
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
                code_lang = line[3:].strip()
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        if not line.strip():
            if in_list:
                result.append('</ul>')
                in_list = False
            result.append('<br>')
            continue

        if re.match(r'^(\d+[.)]\s|[-*+]\s)', line):
            if not in_list:
                result.append('<ul>')
                in_list = True
            content = re.sub(r'^(\d+[.)]\s|[-*+]\s)', '', line)
            content = _format_inline_markdown(content)
            result.append(f'<li>{content}</li>')
            continue

        if in_list:
            result.append('</ul>')
            in_list = False

        if line.startswith('### '):
            result.append(f'<h4>{line[4:]}</h4>')
        elif line.startswith('## '):
            result.append(f'<h3>{line[3:]}</h3>')
        elif line.startswith('# '):
            result.append(f'<h3>{line[2:]}</h3>')
        elif line.startswith('> '):
            result.append(f'<blockquote style="border-left:3px solid #999;margin:4px 0;padding-left:8px;color:#666;">{line[2:]}</blockquote>')
        elif line.startswith('---'):
            result.append('<hr>')
        else:
            result.append(_format_inline_markdown(line))

    if in_code_block:
        code_html = '<pre style="background:#1e1e1e;color:#d4d4d4;padding:8px;border-radius:4px;margin:4px 0;"><code>'
        code_html += '\n'.join(code_lines)
        code_html += '</code></pre>'
        result.append(code_html)

    if in_list:
        result.append('</ul>')

    html = '\n'.join(result)

    # LaTeX-style math: \[ ... \] and \( ... \)
    html = re.sub(r'\\\[(.*?)\\\]', r'<div style="text-align:center;font-style:italic;padding:4px 0;">\1</div>', html, flags=re.DOTALL)
    html = re.sub(r'\\\((.*?)\\\)', r'<i>\1</i>', html)

    # Boxed content
    html = re.sub(r'\\boxed\{(.*?)\}', r'<span style="border:1px solid #999;padding:1px 4px;">\1</span>', html)

    return html


def _format_inline_markdown(text):
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    text = re.sub(r'`([^`]+)`', r'<code style="background:#f0f0f0;padding:1px 3px;border-radius:2px;">\1</code>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = text.replace('\n', '<br>')
    return text


class ModelManageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Управление моделями')
        self.resize(500, 400)
        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        self._refresh_list()
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton('Добавить')
        btn_add.clicked.connect(self._add_model)
        btn_delete = QPushButton('Удалить')
        btn_delete.clicked.connect(self._delete_model)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_delete)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _refresh_list(self):
        self.list_widget.clear()
        for model in load_custom_models():
            self.list_widget.addItem(f'{model["name"]}  ({model["id"]})')

    def _add_model(self):
        name, ok = QInputDialog.getText(self, 'Новая модель', 'Название модели (как будет отображаться):')
        if not ok or not name.strip():
            return
        model_id, ok = QInputDialog.getText(self, 'Новая модель', 'ID модели с OpenRouter\n(например: tencent/hy3-preview:free):')
        if not ok or not model_id.strip():
            return
        models = load_custom_models()
        models.append({'id': model_id.strip(), 'name': name.strip()})
        save_custom_models(models)
        self._refresh_list()

    def _delete_model(self):
        current = self.list_widget.currentRow()
        if current < 0:
            return
        models = load_custom_models()
        if 0 <= current < len(models):
            models.pop(current)
            save_custom_models(models)
            self._refresh_list()


class AIChatWorker(QThread):
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, api_key, model, messages):
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.messages = messages

    def run(self):
        try:
            payload = json.dumps({
                'model': self.model,
                'messages': self.messages,
                'stream': False
            }).encode('utf-8')

            req = urllib.request.Request(
                OPENROUTER_API_URL,
                data=payload,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'http://localhost',
                    'X-Title': 'StudyPlanner'
                },
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode('utf-8'))
                content = data['choices'][0]['message']['content']
                self.response_received.emit(content)

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='replace')
            try:
                error_data = json.loads(error_body)
                msg = error_data.get('error', {}).get('message', str(e))
            except:
                msg = f'HTTP {e.code}: {error_body[:200]}'
            self.error_occurred.emit(msg)
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.finished.emit()


class AIChatWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.conversation = []
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        header = QLabel('<h2>ИИ-ассистент (OpenRouter)</h2>')
        layout.addWidget(header)

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel('Модель:'))

        self.model_combo = QComboBox()
        top_layout.addWidget(self.model_combo, 1)

        self.btn_manage_models = QPushButton('Модели')
        self.btn_manage_models.clicked.connect(self.manage_models)
        top_layout.addWidget(self.btn_manage_models)

        self.btn_clear = QPushButton('Очистить')
        self.btn_clear.clicked.connect(self.clear_chat)
        top_layout.addWidget(self.btn_clear)

        layout.addLayout(top_layout)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setPlaceholderText('Задайте вопрос ассистенту...')
        splitter.addWidget(self.chat_area)

        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 5, 0, 0)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText('Введите сообщение...')
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field, 1)

        self.btn_send = QPushButton('Отправить')
        self.btn_send.clicked.connect(self.send_message)
        input_layout.addWidget(self.btn_send)

        splitter.addWidget(input_widget)
        splitter.setSizes([500, 50])

        layout.addWidget(splitter, 1)

        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: gray; font-size: 11px;')
        layout.addWidget(self.status_label)

    def _refresh_model_combo(self):
        self.model_combo.clear()
        models = load_custom_models()
        for m in models:
            self.model_combo.addItem(m['name'], m['id'])
        if self.model_combo.count() == 0:
            self.model_combo.addItem('Нет моделей', '')

    def manage_models(self):
        dialog = ModelManageDialog(self)
        dialog.exec()
        self._refresh_model_combo()
        saved = self.get_saved_model()
        if saved:
            idx = self.model_combo.findData(saved)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)

    def load_settings(self):
        self.api_key = self.get_api_key()
        self._refresh_model_combo()
        saved_model = self.get_saved_model()
        if saved_model:
            idx = self.model_combo.findData(saved_model)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
        self.input_field.setFocus()

    def get_api_key(self):
        import database
        return database.get_setting('openrouter_api_key', '')

    def get_saved_model(self):
        import database
        return database.get_setting('openrouter_model', '')

    def save_model(self, model_id):
        import database
        database.save_setting('openrouter_model', model_id)

    def send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return

        api_key = self.get_api_key()
        if not api_key:
            QMessageBox.warning(self, 'Ошибка', 'Сначала введите API-ключ OpenRouter в настройках')
            return

        model_id = self.model_combo.currentData()
        if not model_id:
            QMessageBox.warning(self, 'Ошибка', 'Добавьте модель через кнопку «Модели»')
            return

        self.input_field.clear()
        self.input_field.setEnabled(False)
        self.btn_send.setEnabled(False)

        self.conversation.append({'role': 'user', 'content': text})
        self._append_message('Вы', simple_markdown_to_html(text), '#007bff')

        self.status_label.setText('Думаю...')
        self.status_label.setStyleSheet('color: #ff8c00; font-size: 11px;')

        self.save_model(model_id)

        self.worker = AIChatWorker(api_key, model_id, list(self.conversation))
        self.worker.response_received.connect(self._on_response)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _append_message(self, sender, html_text, color):
        cursor = self.chat_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = cursor.charFormat()
        fmt.setForeground(QColor(color))
        bold_font = QFont()
        bold_font.setBold(True)
        fmt.setFont(bold_font, QTextCharFormat.FontPropertiesInheritanceBehavior.FontPropertiesSpecifiedOnly)
        cursor.setCharFormat(fmt)
        cursor.insertText(f'{sender}:\n')

        cursor.insertHtml(html_text)
        cursor.insertText('\n\n')

        self.chat_area.setTextCursor(cursor)
        self.chat_area.ensureCursorVisible()

    def _on_response(self, content):
        self.conversation.append({'role': 'assistant', 'content': content})
        self._append_message('Ассистент', simple_markdown_to_html(content), '#28a745')

    def _on_error(self, error_msg):
        self._append_message('Ошибка', error_msg, '#dc3545')

    def _on_finished(self):
        self.input_field.setEnabled(True)
        self.btn_send.setEnabled(True)
        self.status_label.setText('Готов')
        self.status_label.setStyleSheet('color: gray; font-size: 11px;')
        self.input_field.setFocus()

    def clear_chat(self):
        self.conversation = []
        self.chat_area.clear()
        self.status_label.setText('')


class APIKeyDialog:
    @staticmethod
    def show(parent=None):
        import database
        current_key = database.get_setting('openrouter_api_key', '')
        key, ok = QInputDialog.getText(
            parent,
            'API-ключ OpenRouter',
            'Введите API-ключ OpenRouter:\n(можно получить на https://openrouter.ai/keys)',
            text=current_key
        )
        if ok:
            database.save_setting('openrouter_api_key', key.strip())
            return True
        return False
