# AL Bot (Telegram)

## Быстрый старт

1) Получите токен у `@BotFather`
2) Создайте `.env` в корне проекта (`/Users/leo/AL/.env`):

```
TELEGRAM_BOT_TOKEN=123456:ABC...
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
ALBOT_DATA_DIR=./data
```

3) Установка (Mac):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ./albot
```

4) Запуск:

```bash
python -m albot
```

## Что уже умеет
- /start, /help
- Приём файла (Document) → сохранение в `data/` → вызов LLM (DeepSeek)
- Анкета `/brief` (имя, цель) → вызов LLM (DeepSeek)
- Кнопки: «Принять», «Править», «Тест» (пока заглушки для действий)

## Конфиг LLM
Читается из переменных окружения: `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL` (по умолчанию `https://api.deepseek.com`), `DEEPSEEK_MODEL` (по умолчанию `deepseek-chat`).

## Структура
- `albot/src/bot.py` — Telegram-бот и сценарии
- `albot/src/llm.py` — клиент DeepSeek `/v1/chat/completions`
- `albot/src/config.py` — конфигурация и загрузка `.env`
- `albot/src/integrations.py` — заглушки CRM/Sheets/Calendar


