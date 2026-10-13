# Деплой: Docker + VPS

Выбран постоянно работающий worker с long polling. Webhook не используется.
Публичный HTTP-сервер для такой архитектуры не нужен.

1. На VPS с Docker клонировать репозиторий и перейти в папку.
2. Скопировать `.env.example` в `.env`, записать настоящий BOT_TOKEN.
3. Выполнить `docker compose up -d --build`.
4. Выполнить `docker compose ps` и `docker compose logs --tail=50 bot`.
5. В Telegram проверить `/start`, добавление, список, срок через две минуты,
   напоминание, завершение, справочник и отзыв.
6. Перезапустить `docker compose restart bot`, убедиться, что задачи сохранились.
7. Наблюдать несколько часов; сохранить длительность наблюдения, логи ошибок,
   `docker stats --no-stream`, скриншоты Telegram. Не раскрывать токен.
8. Обновление: `git pull`, затем `docker compose up -d --build`.

Volume bot-data хранит БД и справочник. Если CSV обновлён, существующий volume
не заменит его автоматически: скопируйте обновлённый CSV в контейнер командой
`docker compose cp data/employees.csv bot:/app/data/employees.csv`.

Этот документ — инструкция, а не подтверждение проведённого деплоя.
