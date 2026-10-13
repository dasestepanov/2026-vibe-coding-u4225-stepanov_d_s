"""Telegram transport. Секреты загружаются только из окружения."""
import logging
import os
from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from telegram.error import Forbidden, BadRequest
from service import Service

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
# HTTP-клиент не должен записывать URL с токеном в журнал.
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        await update.effective_message.reply_text('Для личных задач откройте приватный чат с ботом.')
        return
    service = context.application.bot_data['service']
    response = service.execute(update.effective_user.id, update.effective_chat.id, update.effective_message.text)
    # Telegram ограничивает длину одного сообщения.
    for offset in range(0, len(response), 3500):
        await update.effective_message.reply_text(response[offset:offset+3500])

async def reminders(context):
    service = context.application.bot_data['service']
    for task in service.due_tasks():
        try:
            await context.bot.send_message(task['chat_id'], f"Напоминание: срок задачи #{task['id']} наступил.\n{task['text']}")
            service.mark_reminded(task['id'])
        except (Forbidden, BadRequest):
            service.mark_reminded(task['id'])
            logger.warning('Reminder destination unavailable')
        except Exception:
            logger.warning('Reminder delivery failed; will retry')

async def error(update, context):
    # Не выводим содержимое исключения: оно может содержать сетевой URL.
    logger.error('Update failed: %s', type(context.error).__name__)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text('Временная ошибка. Попробуйте ещё раз.')

async def setup(app):
    await app.bot.set_my_commands([BotCommand(cmd, desc) for cmd, desc in [
        ('add','Добавить задачу'),('list','Открытые задачи'),('history','История за неделю'),
        ('done','Завершить задачу'),('delete','Удалить задачу'),('team','Справочник'),
        ('feedback','Оставить отзыв'),('stats','Моя статистика'),('help','Справка')]])

def build_app(token):
    app = Application.builder().token(token).post_init(setup).build()
    app.bot_data['service'] = Service(os.getenv('DB_PATH','data/bot.db'), os.getenv('EMPLOYEES_PATH','data/employees.csv'))
    app.add_handler(MessageHandler(filters.TEXT, handle))
    app.add_error_handler(error)
    app.job_queue.run_repeating(reminders, interval=30, first=5)
    return app

if __name__ == '__main__':
    token = os.getenv('BOT_TOKEN')
    if not token or token == 'your_bot_token_here':
        raise SystemExit('Задайте BOT_TOKEN в .env (см. .env.example).')
    build_app(token).run_polling(drop_pending_updates=False)
