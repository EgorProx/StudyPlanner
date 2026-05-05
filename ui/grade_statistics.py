import logging
from PyQt6.QtGui import QColor
import database

logger = logging.getLogger(__name__)


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
