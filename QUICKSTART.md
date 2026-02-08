# Quick Start Guide

> Пошаговая инструкция по развёртыванию Polza Outreach Toolkit за 10 минут

---

## Установка

### Вариант 1: Локальная установка (Python)

#### Шаг 1: Клонирование и настройка окружения

```bash
# Перейти в директорию проекта
cd polza-outreach-toolkit

# Создать виртуальное окружение
python -m venv venv

# Активировать окружение
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt
```

#### Шаг 2: Конфигурация

```bash
# Скопировать шаблон переменных окружения
cp .env.example .env

# Отредактировать .env файл
nano .env
```

**Обязательные переменные:**

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

**Как получить:**

1. **TELEGRAM_BOT_TOKEN:**
   - Открыть [@BotFather](https://t.me/BotFather) в Telegram
   - Отправить `/newbot`
   - Следовать инструкциям
   - Скопировать токен

2. **TELEGRAM_CHAT_ID:**
   - Написать боту любое сообщение
   - Открыть `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Найти `"chat":{"id":123456789}`

#### Шаг 3: Проверка работоспособности

```bash
# Тест Email Validator
python scripts/email_validator.py data/emails_sample.txt

# Тест Telegram Sender
python scripts/tg_sender.py data/message_sample.txt
```

**Ожидаемый результат:**

```
Validating 6 emails...

✅ test@gmail.com        → Catch-all (Risky)
❌ invalid.email         → Invalid (Syntax)
✅ admin@example.com     → Valid
...

Results saved to: validation_results_1707350400.txt
```

---

## Использование

### Email Validator

#### Базовая валидация

```bash
# Создать файл с email-адресами
cat > my_emails.txt << EOF
user1@gmail.com
user2@yahoo.com
admin@example.com
EOF

# Запустить валидацию
python scripts/email_validator.py my_emails.txt
```

#### Продвинутые опции

```bash
# JSON output для интеграции с API
python scripts/email_validator.py emails.txt \
  --format json \
  --output results.json

# Настройка rate limiting (для больших списков)
python scripts/email_validator.py emails.txt \
  --rate-limit 3.0

# Комбинированный пример
python scripts/email_validator.py emails.txt \
  --format json \
  --output validation_$(date +%Y%m%d).json \
  --rate-limit 2.5
```

**Параметры:**

- `--format` — формат вывода (`txt` или `json`)
- `--output` — путь к файлу результатов (по умолчанию auto-generated)
- `--rate-limit` — задержка между проверками в секундах (по умолчанию 2.0)

#### Интерпретация результатов

**Статусы валидации:**

| Статус | Значение | Действие |
|--------|----------|----------|
| `Valid` | Адрес существует | ✅ Использовать для outreach |
| `Catch-all (Risky)` | Домен принимает все адреса | ⚠️ Проверить дополнительно |
| `Invalid (Syntax)` | Некорректный формат | ❌ Удалить из списка |
| `Invalid (No MX)` | Нет MX-записей | ❌ Удалить из списка |
| `Invalid (Mailbox Not Found)` | Ящик не существует | ❌ Удалить из списка |
| `Timeout` | Превышено время ожидания | ⚠️ Повторить проверку |
| `Connection Refused` | Порт 25 заблокирован | 🔧 Использовать VPS/proxy |

### Telegram Sender

#### Базовая отправка

```bash
# Создать файл с сообщением
echo "✅ Email validation completed successfully!" > message.txt

# Отправить в Telegram
python scripts/tg_sender.py message.txt
```

#### Отправка из произвольного файла

```bash
# Создать notification
cat > notification.txt << EOF
📊 Daily Report

Emails validated: 1,250
Valid: 823 (65.8%)
Invalid: 427 (34.2%)

Status: ✅ Ready for outreach
EOF

# Отправить
python scripts/tg_sender.py notification.txt
```

---

## REST API

### Запуск API-сервера

```bash
# Запуск в фоновом режиме
python api.py &

# Проверка статуса
curl http://localhost:5000/health
```

**Ожидаемый ответ:**

```json
{
  "status": "ok",
  "service": "email-validator-api",
  "version": "2.0"
}
```

### Использование API

#### Email Validation

```bash
# Валидация одного адреса
curl -X POST http://localhost:5000/validate \
  -H "Content-Type: application/json" \
  -d '{
    "emails": ["test@gmail.com"]
  }'

# Валидация нескольких адресов с custom rate limit
curl -X POST http://localhost:5000/validate \
  -H "Content-Type: application/json" \
  -d '{
    "emails": [
      "user1@example.com",
      "user2@gmail.com",
      "invalid.email"
    ],
    "rate_limit": 3.0
  }'
```

**Response example:**

```json
{
  "total": 3,
  "results": [
    {
      "email": "user1@example.com",
      "status": "Valid",
      "valid": true,
      "details": "Email accepted by server",
      "mx_host": "mx.example.com"
    },
    {
      "email": "user2@gmail.com",
      "status": "Catch-all (Risky)",
      "valid": false,
      "details": "Provider uses catch-all policy",
      "mx_host": "gmail-smtp-in.l.google.com"
    },
    {
      "email": "invalid.email",
      "status": "Invalid (Syntax)",
      "valid": false,
      "details": "Invalid email format",
      "mx_host": ""
    }
  ]
}
```

#### Telegram Send

```bash
curl -X POST http://localhost:5000/telegram/send \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Validation complete! 823 valid emails found."
  }'
```

---

## Docker Deployment

### Вариант 2: Развёртывание через Docker

#### Одиночный контейнер (Email Validator + API)

```bash
# Собрать образ
docker build -t polza-toolkit .

# Запустить контейнер
docker run -d \
  --name polza-toolkit \
  -p 5000:5000 \
  --env-file .env \
  polza-toolkit

# Проверить логи
docker logs -f polza-toolkit

# Остановить
docker stop polza-toolkit
```

#### Полный стек (n8n + PostgreSQL + Redis)

```bash
# Создать .env файл с дополнительными переменными
cat > .env << EOF
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# n8n
N8N_ENCRYPTION_KEY=$(openssl rand -hex 32)
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=your_secure_password

# PostgreSQL
DB_PASSWORD=your_db_password
EOF

# Запустить весь стек
docker-compose up -d

# Проверить статус всех сервисов
docker-compose ps
```

**Доступ к сервисам:**

- **n8n:** http://localhost:5678 (admin / your_secure_password)
- **API:** http://localhost:5000
- **PostgreSQL:** localhost:5432 (internal only)
- **Redis:** localhost:6379 (internal only)

#### Управление стеком

```bash
# Просмотр логов всех сервисов
docker-compose logs -f

# Просмотр логов конкретного сервиса
docker-compose logs -f n8n

# Перезапуск сервиса
docker-compose restart n8n

# Остановка стека
docker-compose down

# Полная очистка (включая volumes)
docker-compose down -v
```

---

## Интеграция с n8n

### Настройка n8n workflow

#### 1. Создание базового workflow

1. Открыть n8n: http://localhost:5678
2. Войти (admin / your_secure_password)
3. Создать новый workflow
4. Добавить nodes:

**Пример workflow: Email Validation Pipeline**

```
┌─────────────────────┐
│  Schedule Trigger   │ (Cron: каждый день в 9:00)
│  (Daily 9:00 AM)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Google Sheets      │ (Загрузить leads)
│  (Read leads)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  HTTP Request       │ (POST /validate)
│  (Validate emails)  │
│  URL: http://api:5000/validate
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Function Node      │ (Фильтр: только Valid)
│  (Filter valid)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Google Sheets      │ (Сохранить валидные)
│  (Write results)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  HTTP Request       │ (POST /telegram/send)
│  (Send notification)│
│  URL: http://api:5000/telegram/send
└─────────────────────┘
```

#### 2. Настройка HTTP Request node

**Валидация emails:**

- **Method:** POST
- **URL:** `http://api:5000/validate`
- **Body:**
  ```json
  {
    "emails": {{ $json["emails"] }},
    "rate_limit": 2.0
  }
  ```

**Отправка в Telegram:**

- **Method:** POST
- **URL:** `http://api:5000/telegram/send`
- **Body:**
  ```json
  {
    "message": "Validation complete! {{ $json['total'] }} emails processed."
  }
  ```

#### 3. Function Node для фильтрации

```javascript
// Оставить только валидные emails
const validEmails = items.filter(item => {
  return item.json.status === "Valid";
});

return validEmails.map(item => ({
  json: {
    email: item.json.email,
    mx_host: item.json.mx_host
  }
}));
```

---

## Troubleshooting

### Проблема: Connection Refused при валидации

**Симптомы:**
```
🚫 Connection refused for test@gmail.com (port 25 blocked)
```

**Причина:** Большинство ISP и cloud providers блокируют исходящий порт 25.

**Решение:**

1. **Использовать VPS с открытым портом 25:**
   - Hetzner
   - Contabo
   - DigitalOcean (Business аккаунт)

2. **Использовать SOCKS5 proxy:**
   ```bash
   # Через SSH tunnel
   ssh -D 1080 user@your-vps.com
   
   # Настроить proxy в коде (требует модификации)
   ```

### Проблема: SMTP timeout

**Симптомы:**
```
⏱️ Timeout: admin@slow-server.com
```

**Причина:** Медленный или перегруженный SMTP-сервер.

**Решение:**

1. Увеличить timeout (по умолчанию 5s):
   ```python
   # В email_validator.py
   validator = EmailValidator(timeout=10)
   ```

2. Использовать `--rate-limit` для распределения нагрузки:
   ```bash
   python scripts/email_validator.py emails.txt --rate-limit 5.0
   ```

### Проблема: Telegram 401 Unauthorized

**Симптомы:**
```
❌ Failed to send message: Unauthorized
→ Invalid bot token. Check TELEGRAM_BOT_TOKEN in .env
```

**Решение:**

1. Проверить токен в .env:
   ```bash
   cat .env | grep TELEGRAM_BOT_TOKEN
   ```

2. Получить новый токен у [@BotFather](https://t.me/BotFather):
   ```
   /newbot → следовать инструкциям
   ```

3. Обновить .env и перезапустить:
   ```bash
   nano .env
   # Обновить TELEGRAM_BOT_TOKEN
   python scripts/tg_sender.py message.txt
   ```

### Проблема: High memory usage

**Симптомы:**
```
Процесс занимает 500+ MB RAM при валидации 10,000 emails
```

**Причина:** Старая версия без streaming writes.

**Решение:**

Убедиться, что используется актуальная версия с потоковой записью:

```bash
# Проверить версию
head -20 scripts/email_validator.py | grep -i "streaming"

# Должно быть:
# - Streaming file writes (memory efficient)
```

### Проблема: Docker network issues

**Симптомы:**
```
n8n не может достучаться до api:5000
```

**Решение:**

1. Проверить, что все контейнеры в одной сети:
   ```bash
   docker-compose ps
   docker network inspect polza-outreach-toolkit_default
   ```

2. Использовать service name вместо localhost:
   ```
   # Неправильно:
   http://localhost:5000/validate
   
   # Правильно:
   http://api:5000/validate
   ```

---

## Production Checklist

Перед запуском в production убедитесь:

### Безопасность

- [ ] `.env` файл добавлен в `.gitignore`
- [ ] Сгенерирован случайный `N8N_ENCRYPTION_KEY`
- [ ] Установлен сложный пароль для n8n Basic Auth
- [ ] PostgreSQL доступен только внутри Docker network
- [ ] API использует rate limiting (если публичный)

### Мониторинг

- [ ] Настроены Telegram алерты для критических ошибок
- [ ] Логи ротируются (не заполняют диск)
- [ ] Добавлен health check endpoint в monitoring
- [ ] Настроен backup PostgreSQL (если используется для хранения важных данных)

### Производительность

- [ ] Rate limiting настроен адекватно (`--rate-limit 2.0+`)
- [ ] Для массовых проверок (>10,000) рассмотрена async версия
- [ ] VPS имеет открытый порт 25 для SMTP
- [ ] Proxies настроены для высоконагруженных сценариев

### Масштабируемость

- [ ] Docker volumes используют named volumes (не bind mounts)
- [ ] PostgreSQL настроен на read replicas (для >10k workflow/день)
- [ ] n8n workflow используют queue mode (Redis)
- [ ] Логи пишутся в structured format (JSON) для анализа

---

## Дополнительные ресурсы

### Документация

- **README.md** — полное описание архитектуры и технических решений
- **API Documentation** — `/api.py` (inline docstrings)
- **n8n Docs** — https://docs.n8n.io

### Поддержка

**Автор:** Technical Growth Engineer  
**Email:** См. контакты в README.md  

### Обратная связь

Если обнаружили баг или хотите предложить улучшение:

1. Создать issue в репозитории
2. Написать в Telegram (см. контакты)
3. Отправить pull request

---

**Готовы к работе? Начните с установки и тестирования на примерах данных!**
