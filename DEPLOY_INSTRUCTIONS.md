# 🚀 Деплой AL Bot на Render

## 📋 Инструкции по деплою

### 1. Mini App на Render

1. **Зайдите на [render.com](https://render.com)**
2. **Создайте аккаунт** (если нет)
3. **Нажмите "New +" → "Web Service"**
4. **Подключите GitHub репозиторий:**
   - Repository: `leodynamite/al`
   - Branch: `main`
5. **Настройки сервиса:**
   - **Name:** `albot-mini-app`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python albot/mini_app/server.py`
   - **Port:** `8080` (автоматически)
6. **Environment Variables:**
   - `PORT` = `8080` (автоматически)
7. **Нажмите "Create Web Service"**

### 2. Получение URL Mini App

После деплоя вы получите URL вида:
```
https://albot-mini-app-xxxxx.onrender.com
```

### 3. Обновление .env файла

Замените в `.env` файле:
```bash
WEBAPP_URL=https://albot-mini-app-xxxxx.onrender.com
```

### 4. Запуск бота локально

```bash
python3 -m albot.src
```

### 5. Тестирование

1. **В Telegram:** `/start`
2. **Проверьте кнопку:** "🚀 Открыть приложение"
3. **Mini App должен открыться** в Telegram

## 🔧 Альтернативный способ (через render.yaml)

Если хотите использовать файл `render.yaml`:

1. **В Render Dashboard:**
2. **"New +" → "Blueprint"**
3. **Выберите репозиторий:** `leodynamite/al`
4. **Render автоматически найдет `render.yaml`**

## 📱 Что получится

- ✅ **Mini App** работает на Render (HTTPS)
- ✅ **Бот** работает локально
- ✅ **Кнопка "Открыть приложение"** открывает Mini App в Telegram
- ✅ **Все функции** Mini App доступны

## 🐛 Если что-то не работает

1. **Проверьте логи** в Render Dashboard
2. **Убедитесь** что URL в `.env` правильный
3. **Перезапустите бота** после изменения `.env`

## 📞 Поддержка

Если нужна помощь - пишите в Telegram!
