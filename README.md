# PriceTrackerBot 🛒

Telegram-бот для отслеживания цен на Ozon и Wildberries.

## Возможности
- 📊 Отслеживание цен на товары
- 🔔 Уведомления о снижении цены
- 🎯 Установка целевой цены
- 📋 Список отслеживаемых товаров

## Команды
- `/start` — запуск бота
- `/add` — добавить товар (отправь ссылку)
- `/list` — список товаров
- `/remove` — удалить товар
- `/target` — установить целевую цену
- `/help` — справка

## Технологии
- Python 3
- pyTelegramBotAPI
- SQLite
- Requests

## Установка и запуск
```bash
pip install pyTelegramBotAPI requests
python tracker_bot.py
