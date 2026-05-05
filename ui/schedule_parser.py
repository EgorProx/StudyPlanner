import logging
import re
import urllib.request
from datetime import datetime, timedelta
from html.parser import HTMLParser
import database

logger = logging.getLogger(__name__)


class ScheduleParserBase:
    def __init__(self):
        self.parsed_data = []

    def parse(self, source_data):
        raise NotImplementedError('Subclasses must implement parse() method')

    def validate_entry(self, entry):
        required = ['subject_name', 'day_of_week', 'start_time']
        for field in required:
            if field not in entry:
                return False, f'Missing required field: {field}'
            val = entry[field]
            if val is None or (isinstance(val, str) and val.strip() == ''):
                return False, f'Missing required field: {field}'
        if 'week_type' not in entry:
            entry['week_type'] = 'both'
        valid_days = range(7)
        if entry['day_of_week'] not in valid_days:
            return False, 'Invalid day_of_week'
        valid_week_types = ['even', 'odd', 'both']
        if entry['week_type'] not in valid_week_types:
            return False, 'Invalid week_type'
        return True, 'OK'

    def to_database_format(self, entry, subject_id_map):
        subject_name = entry.get('subject_name', '')
        subject_id = subject_id_map.get(subject_name)
        if not subject_id:
            return None
        return {
            'subject_id': subject_id,
            'day_of_week': entry['day_of_week'],
            'week_type': entry['week_type'],
            'start_time': entry['start_time'],
            'end_time': entry.get('end_time', ''),
            'room': entry.get('room', ''),
            'lesson_type': entry.get('lesson_type', ''),
            'group_name': entry.get('group_name', '')
        }

    def import_to_database(self, entries, create_missing_subjects=False):
        from database import add_subject, add_schedule_entry, get_all_subjects
        subjects = get_all_subjects()
        subject_id_map = {s[1].strip().lower(): s[0] for s in subjects}
        existing_entries = {
            (row[1], row[2], row[3], row[4], row[5] or '', row[6] or '', row[7] or '', row[8] or '')
            for row in database.get_schedule()
        }
        imported = 0
        errors = []
        for entry in entries:
            valid, msg = self.validate_entry(entry)
            if not valid:
                errors.append(f'Invalid entry: {msg}')
                continue
            subject_name = entry.get('subject_name', '').strip()
            subject_key = subject_name.lower()
            if subject_key not in subject_id_map:
                if create_missing_subjects:
                    add_subject(subject_name, entry.get('teacher', ''), entry.get('room', ''), '')
                    subjects = get_all_subjects()
                    subject_id_map = {s[1].strip().lower(): s[0] for s in subjects}
                else:
                    errors.append(f'Subject not found: {subject_name}')
                    continue
            db_entry = self.to_database_format(entry, {subject_name: subject_id_map[subject_key]})
            if db_entry:
                entry_key = (
                    db_entry['subject_id'],
                    db_entry['day_of_week'],
                    db_entry['week_type'],
                    db_entry['start_time'],
                    db_entry.get('end_time', '') or '',
                    db_entry.get('room', '') or '',
                    db_entry.get('lesson_type', '') or '',
                    db_entry.get('group_name', '') or ''
                )
                if entry_key in existing_entries:
                    continue
                add_schedule_entry(**db_entry)
                existing_entries.add(entry_key)
                imported += 1
        return imported, errors


class _SfuTimetableHTMLExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.current_table = None
        self.current_row = None
        self.current_cell = None
        self.in_timetable = False
        self.bold_level = 0
        self.em_level = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'table':
            classes = attrs_dict.get('class', '')
            if 'timetable' in classes.split():
                self.in_timetable = True
                self.current_table = []
        elif self.in_timetable and tag == 'tr':
            self.current_row = []
        elif self.in_timetable and tag in ('td', 'th') and self.current_row is not None:
            self.current_cell = {
                'tag': tag,
                'colspan': int(attrs_dict.get('colspan', '1') or 1),
                'text_parts': [],
                'bold_parts': [],
                'em_parts': []
            }
        elif self.current_cell is not None and tag == 'br':
            self._append_text('\n')
        elif self.current_cell is not None and tag == 'b':
            self.bold_level += 1
        elif self.current_cell is not None and tag == 'em':
            self.em_level += 1

    def handle_endtag(self, tag):
        if self.current_cell is not None and tag in ('td', 'th'):
            self.current_cell['text'] = self._normalize_text(''.join(self.current_cell['text_parts']))
            self.current_cell['bold'] = self._normalize_text(''.join(self.current_cell['bold_parts']))
            self.current_cell['em'] = self._normalize_text(''.join(self.current_cell['em_parts']))
            self.current_row.append(self.current_cell)
            self.current_cell = None
        elif self.in_timetable and tag == 'tr':
            if self.current_table is not None and self.current_row:
                self.current_table.append(self.current_row)
            self.current_row = None
        elif self.in_timetable and tag == 'table':
            if self.current_table:
                self.tables.append(self.current_table)
            self.current_table = None
            self.in_timetable = False
        elif self.current_cell is not None and tag == 'b' and self.bold_level:
            self.bold_level -= 1
        elif self.current_cell is not None and tag == 'em' and self.em_level:
            self.em_level -= 1

    def handle_data(self, data):
        if self.current_cell is not None:
            self._append_text(data)

    def _append_text(self, text):
        self.current_cell['text_parts'].append(text)
        if self.bold_level:
            self.current_cell['bold_parts'].append(text)
        if self.em_level:
            self.current_cell['em_parts'].append(text)

    @staticmethod
    def _normalize_text(text):
        lines = [' '.join(line.split()) for line in text.splitlines()]
        return '\n'.join(line for line in lines if line)


class SfuScheduleParser(ScheduleParserBase):
    DAY_MAP = {
        'понедельник': 0, 'вторник': 1, 'среда': 2, 'четверг': 3,
        'пятница': 4, 'суббота': 5, 'воскресенье': 6
    }

    LESSON_TYPE_MAP = {
        'лекция': 'Лекция', 'пр. занятие': 'Практика', 'практика': 'Практика',
        'лабораторная': 'Лабораторная', 'лаб. работа': 'Лабораторная',
        'семинар': 'Семинар', 'консультация': 'Консультация',
        'экзамен': 'Экзамен', 'зачет': 'Зачет', 'зачёт': 'Зачет'
    }

    def parse(self, source_data):
        extractor = _SfuTimetableHTMLExtractor()
        extractor.feed(source_data)
        group_name = self._extract_group_name(source_data)
        entries = []
        for table in extractor.tables:
            current_day = None
            for row in table:
                if self._is_day_row(row):
                    current_day = self.DAY_MAP[row[0]['text'].strip().lower()]
                    continue
                if current_day is None or len(row) < 3:
                    continue
                time_match = re.search(r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})', row[1].get('text', ''))
                if not time_match:
                    continue
                start_time, end_time = time_match.group(1), time_match.group(2)
                lesson_cells = row[2:]
                if lesson_cells[0].get('colspan') == 2 or len(lesson_cells) == 1:
                    entry = self._parse_lesson_cell(lesson_cells[0], current_day, 'both', start_time, end_time, group_name)
                    if entry:
                        entries.append(entry)
                    continue
                for week_type, cell in zip(('odd', 'even'), lesson_cells[:2]):
                    entry = self._parse_lesson_cell(cell, current_day, week_type, start_time, end_time, group_name)
                    if entry:
                        entries.append(entry)
        self.parsed_data = entries
        return entries

    def parse_file(self, path):
        for encoding in ('utf-8', 'cp1251'):
            try:
                with open(path, 'r', encoding=encoding) as file:
                    return self.parse(file.read())
            except UnicodeDecodeError:
                continue
        with open(path, 'r', encoding='utf-8', errors='ignore') as file:
            return self.parse(file.read())

    def parse_url(self, url):
        request = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'identity',
                'Connection': 'keep-alive',
                'Referer': 'https://edu.sfu-kras.ru/timetable',
            }
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            charset = response.headers.get_content_charset() or 'utf-8'
            return self.parse(response.read().decode(charset, errors='replace'))

    def _is_day_row(self, row):
        return len(row) == 1 and row[0].get('tag') == 'th' and row[0].get('text', '').strip().lower() in self.DAY_MAP

    def _parse_lesson_cell(self, cell, day_of_week, week_type, start_time, end_time, group_name):
        text = cell.get('text', '').strip()
        if not text:
            return None
        subject_name = self._extract_subject_name(cell)
        if not subject_name:
            return None
        return {
            'subject_name': subject_name, 'day_of_week': day_of_week, 'week_type': week_type,
            'start_time': start_time, 'end_time': end_time,
            'room': self._extract_room(text), 'lesson_type': self._extract_lesson_type(text),
            'group_name': group_name, 'teacher': self._extract_teacher(cell)
        }

    def _extract_subject_name(self, cell):
        bold_text = cell.get('bold', '').strip()
        if bold_text:
            return bold_text.splitlines()[0].strip()
        text = cell.get('text', '').strip()
        return re.sub(r'\s*\([^)]*\).*$', '', text.splitlines()[0]).strip() if text else ''

    def _extract_teacher(self, cell):
        em_text = cell.get('em', '').strip()
        return em_text.splitlines()[0].strip() if em_text else ''

    def _extract_lesson_type(self, text):
        match = re.search(r'\(([^)]*)\)', text)
        if not match:
            return ''
        raw_type = match.group(1).strip().lower()
        return self.LESSON_TYPE_MAP.get(raw_type, match.group(1).strip())

    def _extract_room(self, text):
        for line in text.splitlines()[1:]:
            lowered = line.lower()
            if lowered in ('синхронно', 'асинхронно'):
                continue
            if 'ауд' in lowered or 'корпус' in lowered or line == 'ЭИОС':
                return line.strip()
        return ''

    def _extract_group_name(self, source_data):
        text = re.sub(r'<[^>]+>', ' ', source_data)
        text = ' '.join(text.split())
        match = re.search(r'группа\s+([^()]+?)(?:\s*\(|\s*</h3>|$)', text, flags=re.IGNORECASE)
        return match.group(1).strip() if match else ''


class WeekCalculator:
    @staticmethod
    def get_semester_start():
        from database import get_setting
        start_str = get_setting('semester_start', '2025-09-01')
        try:
            return datetime.strptime(start_str, '%Y-%m-%d').date()
        except:
            return datetime(2025, 9, 1).date()

    @staticmethod
    def get_week_type(date=None):
        if date is None:
            date = datetime.now()
        if hasattr(date, 'date'):
            date_obj = date.date()
        else:
            date_obj = date
        semester_start = WeekCalculator.get_semester_start()
        days_since = (date_obj - semester_start).days
        if days_since < 0:
            week_number = 0
        else:
            week_number = days_since // 7 + 1
        return 'even' if week_number % 2 == 0 else 'odd'

    @staticmethod
    def get_current_week_parity():
        return WeekCalculator.get_week_type()

    @staticmethod
    def format_week_type(week_type):
        mapping = {'even': 'Четная', 'odd': 'Нечетная', 'both': 'Каждая'}
        return mapping.get(week_type, week_type)
