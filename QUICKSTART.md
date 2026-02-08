# Quick Start Guide

> Пошаговая инструкция по развёртыванию Polza Outreach Toolkit за 5 минут

---

## 🚀 Установка за 5 минут

### Шаг 1: Установка зависимостей

```bash
# Перейти в директорию проекта
cd polza-outreach-toolkit

# Создать виртуальное окружение
python -m venv venv

# Активировать окружение
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Установить зависимости
pip install -r requirements.txt
```

### Шаг 2: Конфигурация Telegram

```bash
# Скопировать шаблон
cp .env.example .env

# Отредактировать .env
nano .env
```

**Что добавить в .env:**

```env
# 1. Создать бота: https://t.me/BotFather → /newbot
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# 2. Получить chat ID: написать боту → https://api.telegram.org/bot<TOKEN>/getUpdates
TELEGRAM_CHAT_ID=123456789
```

### Шаг 3: Тест работоспособности

```bash
# Тест Email Validator (async)
python scripts/email_validator.py data/emails_sample.txt

# Тест Telegram Sender
python scripts/tg_sender.py data/message_sample.txt
```

**✅ Ожидаемый результат:**

```
🚀 Validating 6 emails (async, max 50 concurrent)...
Validating emails: 100%|████████| 6/6 [00:03<00:00,  1.89 email/s]

📊 SUMMARY:
   Total: 6
   Time: 3.18s (1.9 emails/sec)
   Valid: 2 (33.3%)
   Catch-all (Risky): 2 (33.3%)
   Invalid: 2 (33.3%)

💾 Results saved to: validation_results_1707350400.txt
```

---

## 📋 Использование

### Email Validator

#### Базовая валидация

```bash
# Создать файл с email
cat > my_emails.txt << EOF
user1@gmail.com
user2@yahoo.com
admin@example.com
EOF

# Запустить (async, 50 concurrent)
python scripts/email_validator.py my_emails.txt
```

#### Высокая производительность

```bash
# 100 одновременных проверок (для больших списков)
python scripts/email_validator.py emails.txt --concurrent 100

# Больше retry попыток (для нестабильных сетей)
python scripts/email_validator.py emails.txt --retries 5

# JSON output
python scripts/email_validator.py emails.txt \
  --format json \
  --output results.json
```

**Параметры:**

| Флаг | Описание | Default |
|------|----------|---------|
| `--concurrent` | Макс. одновременных проверок | 50 |
| `--retries` | Макс. попыток при ошибке | 3 |
| `--format` | Формат вывода (txt/json) | txt |
| `--output` | Путь к файлу результатов | auto |

#### Интерпретация результатов

| Статус | Действие |
|--------|----------|
| ✅ Valid | Использовать для outreach |
| ⚠️ Catch-all (Risky) | Проверить дополнительно |
| ❌ Invalid (Syntax) | Удалить |
| ❌ Invalid (No MX) | Удалить |
| ❌ Mailbox Not Found | Удалить |
| ⏱️ Timeout | Повторить с `--retries 5` |
| 🚫 Connection Refused | Нужен VPS с портом 25 |

### Telegram Sender

#### Базовая отправка

```bash
# Создать сообщение
cat > notification.txt << EOF
✅ Email validation completed!

📊 Results:
• Valid: 823
• Invalid: 427

Status: Ready for outreach
EOF

# Отправить
python scripts/tg_sender.py notification.txt
```

#### Форматирование

Поддерживается **HTML**:

```html
<b>Bold</b>
<i>Italic</i>
<code>Code</code>
<a href="https://example.com">Link</a>

✅ Emoji работают
📊 Просто вставить
```

### SMTP Monitoring

```bash
# Отчет за последние 24 часа
python utils/logger.py

# За последние 48 часов
python utils/logger.py --hours 48
```

**Вывод:**

```
📊 SMTP MONITORING REPORT (Last 24 hours)
✅ Overall Success Rate: 87.3%
📈 Total Checks: 1,250

⚠️ ROTATION RECOMMENDED for 2 MX hosts:
   • mx-slow.example.com
   • mx-unreliable.provider.net
```

---

## 🐳 Docker (опционально)

### Одиночный контейнер

```bash
# Собрать
docker build -t polza-toolkit .

# Запустить
docker run -d \
  --name polza-toolkit \
  -p 5000:5000 \
  --env-file .env \
  polza-toolkit

# Проверить
docker logs -f polza-toolkit
```

### Полный стек (n8n + PostgreSQL + Redis)

```bash
# Настроить переменные окружения
cat >> .env << EOF

N8N_ENCRYPTION_KEY=$(openssl rand -hex 32)
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=your_password
DB_PASSWORD=your_db_password
EOF

# Запустить
docker-compose up -d

# Доступ:
# - n8n: http://localhost:5678
# - API: http://localhost:5000
```

---

## 🔧 REST API

### Запуск

```bash
python api.py
# Доступ: http://localhost:5000
```

### Примеры

**Validate Emails:**

```bash
curl -X POST http://localhost:5000/validate \
  -H "Content-Type: application/json" \
  -d '{
    "emails": ["test@example.com", "user@gmail.com"],
    "max_concurrent": 50,
    "max_retries": 3
  }'
```

**Send Telegram:**

```bash
curl -X POST http://localhost:5000/telegram/send \
  -H "Content-Type: application/json" \
  -d '{
    "text": "✅ Validation complete!"
  }'
```

**Get Stats:**

```bash
curl http://localhost:5000/stats?hours=24
```

---

## 🛠️ Troubleshooting

### Проблема: Connection Refused

**Симптомы:**
```
🚫 Connection refused (port 25 blocked)
```

**Решение:**
1. Использовать VPS с открытым портом 25:
   - ✅ Hetzner
   - ✅ Contabo
   - ✅ DigitalOcean (Business)
   - ❌ AWS, GCP, Azure (блокируют порт 25)

2. Или использовать SOCKS5 proxy через VPS

### Проблема: SMTP Timeout

**Симптомы:**
```
⏱️ Timeout для 30% проверок
```

**Решение:**

```bash
# Увеличить retry
python scripts/email_validator.py emails.txt --retries 5

# Снизить concurrent
python scripts/email_validator.py emails.txt --concurrent 25
```

### Проблема: Telegram Unauthorized

**Симптомы:**
```
❌ Failed to send message: Unauthorized
```

**Решение:**
1. Проверить `TELEGRAM_BOT_TOKEN` в `.env`
2. Получить новый токен у @BotFather
3. Убедиться, что написали боту хотя бы одно сообщение

---

## 📊 Производительность

### Async vs Sync

| Emails | Sync | Async (50 concurrent) | Ускорение |
|--------|------|----------------------|-----------|
| 10     | 24s  | 3.2s                 | 7.5x      |
| 50     | 118s | 8.7s                 | 13.6x     |
| 100    | 235s | 14.2s                | 16.5x     |
| 500    | 1175s | 62.3s               | 18.9x     |

### Рекомендации

**Малые списки (< 100):**
```bash
python scripts/email_validator.py emails.txt --concurrent 50
```

**Средние списки (100-500):**
```bash
python scripts/email_validator.py emails.txt --concurrent 75
```

**Большие списки (500+):**
```bash
python scripts/email_validator.py emails.txt --concurrent 100 --retries 2
```

---

## 🎯 Production Checklist

Перед запуском в production:

- [ ] `.env` в `.gitignore`
- [ ] Telegram credentials настроены
- [ ] VPS с открытым портом 25
- [ ] Rate limiting настроен (`--concurrent` не > 100)
- [ ] Мониторинг настроен (проверка `python utils/logger.py`)
- [ ] Backup strategy для результатов
- [ ] Логи ротируются (не заполняют диск)

---

## 📚 Дополнительно

- **README.md** — Полная документация
- **ARCHITECTURE.md** — Архитектура для 1200 аккаунтов
- **AI_STACK.md** — AI-инструменты и процесс

---

**Готово! Начните с тестирования на примерах данных.**

```bash
python scripts/email_validator.py data/emails_sample.txt
python scripts/tg_sender.py data/message_sample.txt
```
