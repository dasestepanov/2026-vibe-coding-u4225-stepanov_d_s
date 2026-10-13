"""Бизнес-логика: одинаковая для Telegram и автономных проверок."""
import csv
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

HELP = '''TaskMate — помощник для задач команды.
/add Текст | высокий/обычный/низкий | YYYY-MM-DD HH:MM
Срок необязателен, время московское.
/list — открытые задачи; /history — последние 7 дней
/done ID — завершить; /delete ID — удалить свою задачу
/team Имя или отдел — справочник
/feedback 1-5 | отзыв — обратная связь
/stats — моя статистика; /help — справка'''

class Service:
    def __init__(self, db='data/bot.db', employees='data/employees.csv'):
        Path(db).parent.mkdir(parents=True, exist_ok=True)
        self.db, self.employees = str(db), employees
        with self.connect() as con:
            con.executescript('''
            CREATE TABLE IF NOT EXISTS tasks (
              id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, chat_id INTEGER NOT NULL,
              text TEXT NOT NULL, priority INTEGER NOT NULL, due TEXT,
              done INTEGER DEFAULT 0, reminded INTEGER DEFAULT 0,
              created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS feedback (
              id INTEGER PRIMARY KEY, user_id INTEGER, rating INTEGER, text TEXT, created TEXT);
            ''')

    def connect(self):
        con = sqlite3.connect(self.db)
        con.row_factory = sqlite3.Row
        return con

    def execute(self, user, chat, message):
        command, _, args = message.partition(' ')
        command = command.split('@')[0].lower()
        args = args.strip()
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as con:
            if command in ('/start', '/help'):
                return HELP
            if command == '/add':
                parts = [p.strip() for p in args.split('|')]
                if not parts[0] or len(parts[0]) > 500 or len(parts) > 3:
                    return 'Укажите текст до 500 символов: /add Подготовить отчёт | высокий'
                priorities = {'высокий': 0, 'обычный': 1, 'низкий': 2}
                priority = parts[1] if len(parts) > 1 else 'обычный'
                if priority not in priorities:
                    return 'Приоритет: высокий, обычный или низкий.'
                due = None
                if len(parts) == 3:
                    try:
                        from zoneinfo import ZoneInfo
                        due_dt = datetime.strptime(parts[2], '%Y-%m-%d %H:%M').replace(tzinfo=ZoneInfo('Europe/Moscow'))
                        if due_dt <= datetime.now(due_dt.tzinfo):
                            return 'Срок должен быть в будущем.'
                        due = due_dt.astimezone(timezone.utc).isoformat()
                    except ValueError:
                        return 'Формат срока: YYYY-MM-DD HH:MM, время московское.'
                cur = con.execute('INSERT INTO tasks(user_id,chat_id,text,priority,due,created) VALUES(?,?,?,?,?,?)', (user, chat, parts[0], priorities[priority], due, now))
                return f'Задача #{cur.lastrowid} добавлена: {parts[0]} ({priority}).'
            if command in ('/list', '/history'):
                query = 'SELECT * FROM tasks WHERE user_id=?'
                if command == '/list':
                    query += ' AND done=0'
                else:
                    query += " AND julianday(created)>=julianday('now','-7 days')"
                rows = con.execute(query + ' ORDER BY done,priority,id LIMIT 30', (user,)).fetchall()
                if not rows:
                    return 'Задач нет. Добавьте первую через /add.'
                labels = ['высокий', 'обычный', 'низкий']
                return '\n'.join(f"{'✓' if r['done'] else '○'} #{r['id']} [{labels[r['priority']]}] {r['text']}" + (f" · срок {self.local_due(r['due'])}" if r['due'] else '') for r in rows)
            if command in ('/done', '/delete'):
                if not args.isdigit():
                    return f'Укажите номер задачи: {command} 1'
                sql = 'UPDATE tasks SET done=1 WHERE id=? AND user_id=? AND done=0' if command == '/done' else 'DELETE FROM tasks WHERE id=? AND user_id=?'
                changed = con.execute(sql, (int(args), user)).rowcount
                return ('Задача завершена.' if command == '/done' else 'Задача удалена.') if changed else 'Открытая задача не найдена или принадлежит другому пользователю.'
            if command == '/team':
                try:
                    with open(self.employees, encoding='utf-8-sig', newline='') as f:
                        reader = csv.DictReader(f)
                        if not {'name','department','role','email'}.issubset(reader.fieldnames or []):
                            return 'Ошибка структуры справочника. Сообщите администратору.'
                        rows = [r for r in reader if args.casefold() in (r['name'] + ' ' + r['department']).casefold()][:20]
                    return '\n'.join(f"{r['name']} — {r['department']}, {r['role']}\n{r['email']}" for r in rows) or 'Сотрудники не найдены.'
                except (OSError, UnicodeError, csv.Error):
                    return 'Справочник временно недоступен. Попробуйте позже.'
            if command == '/feedback':
                rating, sep, text = args.partition('|')
                if not sep or rating.strip() not in ('1','2','3','4','5') or not 1 <= len(text.strip()) <= 1000:
                    return 'Формат: /feedback 5 | Что понравилось и что улучшить (до 1000 символов).'
                con.execute('INSERT INTO feedback(user_id,rating,text,created) VALUES(?,?,?,?)', (user, int(rating), text.strip(), now))
                return 'Спасибо! Отзыв сохранён.'
            if command == '/stats':
                row = con.execute('SELECT COUNT(*) total,COALESCE(SUM(done),0) done FROM tasks WHERE user_id=?', (user,)).fetchone()
                return f"Всего задач: {row['total']}. Завершено: {row['done']}."
            return 'Неизвестная команда. Используйте /help.'

    @staticmethod
    def local_due(due):
        from zoneinfo import ZoneInfo
        return datetime.fromisoformat(due).astimezone(ZoneInfo('Europe/Moscow')).strftime('%d.%m.%Y %H:%M МСК')

    def due_tasks(self):
        with self.connect() as con:
            return con.execute('SELECT * FROM tasks WHERE done=0 AND reminded=0 AND due<=?', (datetime.now(timezone.utc).isoformat(),)).fetchall()

    def mark_reminded(self, task_id):
        with self.connect() as con:
            con.execute('UPDATE tasks SET reminded=1 WHERE id=?', (task_id,))
