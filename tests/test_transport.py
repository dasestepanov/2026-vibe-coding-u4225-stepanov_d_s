"""Проверки Telegram-обработчиков без сетевых запросов."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from bot import handle, reminders
from service import Service

class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_private_command_and_group_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = Service(Path(tmp)/'test.db')
            message = SimpleNamespace(text='/add Проверка',reply_text=AsyncMock())
            update = SimpleNamespace(effective_chat=SimpleNamespace(id=1,type='private'),effective_user=SimpleNamespace(id=1),effective_message=message)
            context = SimpleNamespace(application=SimpleNamespace(bot_data={'service':service}))
            await handle(update,context)
            self.assertIn('добавлена',message.reply_text.call_args.args[0])
            update.effective_chat.type='group'
            await handle(update,context)
            self.assertIn('приватный',message.reply_text.call_args.args[0])
            self.assertEqual(service.execute(1,1,'/stats'),'Всего задач: 1. Завершено: 0.')
    async def test_reminder_sends_and_marks(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=Service(Path(tmp)/'test.db')
            service.execute(1,10,'/add Дедлайн')
            with service.connect() as con:
                con.execute("UPDATE tasks SET due='2020-01-01T00:00:00+00:00'")
            context=SimpleNamespace(application=SimpleNamespace(bot_data={'service':service}),bot=SimpleNamespace(send_message=AsyncMock()))
            await reminders(context)
            context.bot.send_message.assert_awaited_once()
            self.assertEqual(context.bot.send_message.call_args.args[0],10)
            self.assertEqual(len(service.due_tasks()),0)
    async def test_network_failure_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=Service(Path(tmp)/'test.db')
            service.execute(1,10,'/add Дедлайн')
            with service.connect() as con:
                con.execute("UPDATE tasks SET due='2020-01-01T00:00:00+00:00'")
            context=SimpleNamespace(application=SimpleNamespace(bot_data={'service':service}),bot=SimpleNamespace(send_message=AsyncMock(side_effect=TimeoutError)))
            await reminders(context)
            self.assertEqual(len(service.due_tasks()),1)
