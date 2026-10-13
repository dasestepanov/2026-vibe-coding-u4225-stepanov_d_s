import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from service import Service

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/'test.db'
        self.s = Service(self.path)
    def tearDown(self):
        self.tmp.cleanup()
    def test_lifecycle_and_persistence(self):
        self.assertIn('#1', self.s.execute(1,1,'/add Отчёт | высокий'))
        self.assertIn('Отчёт', Service(self.path).execute(1,1,'/list'))
        self.assertIn('завершена',self.s.execute(1,1,'/done 1'))
        self.assertIn('Задач нет', self.s.execute(1,1,'/list'))
        self.assertIn('✓', self.s.execute(1,1,'/history'))
    def test_isolation(self):
        self.s.execute(1,1,'/add Секрет')
        self.assertNotIn('Секрет',self.s.execute(2,2,'/list'))
        self.assertIn('не найдена',self.s.execute(2,2,'/done 1'))
        self.assertIn('не найдена',self.s.execute(2,2,'/delete 1'))
    def test_priority_and_validation(self):
        self.s.execute(1,1,'/add Низкая | низкий')
        self.s.execute(1,1,'/add Высокая | высокий')
        self.assertLess(self.s.execute(1,1,'/list').index('Высокая'),self.s.execute(1,1,'/list').index('Низкая'))
        for msg in ['/add', '/add X | неверный','/add X | обычный | 2020-01-01 00:00','/add X | обычный | abc']:
            self.assertNotIn('добавлена',self.s.execute(1,1,msg))
    def test_csv_and_errors(self):
        self.assertIn('anna@example.com',self.s.execute(1,1,'/team IT'))
        self.assertIn('не найдены',self.s.execute(1,1,'/team xyz'))
        self.s.employees = 'missing.csv'
        self.assertIn('недоступен',self.s.execute(1,1,'/team'))
    def test_feedback(self):
        self.assertIn('Формат', self.s.execute(1,1,'/feedback 9 | x'))
        self.assertIn('сохранён',self.s.execute(1,1,'/feedback 4 | Удобно'))
        with self.s.connect() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM feedback').fetchone()[0],1)
    def test_reminder_persistence(self):
        self.s.execute(1,1,'/add Задача')
        with self.s.connect() as con:
            con.execute('UPDATE tasks SET due=?',((datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(),))
        self.assertEqual(len(self.s.due_tasks()),1)
        self.s.mark_reminded(1)
        self.assertEqual(len(Service(self.path).due_tasks()),0)
    def test_sql_text(self):
        self.s.execute(1,1,"/add '; DROP TABLE tasks; --")
        self.assertIn('DROP TABLE',self.s.execute(1,1,'/list'))

if __name__ == '__main__': unittest.main()
