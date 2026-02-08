# Polza Outreach Toolkit

**Тестовое задание для Polza Agency**

---

## Быстрый старт по тестовому заданию

### Установка

```bash
# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Установить зависимости
pip install -r requirements.txt

# Настроить .env
cp .env.example .env
nano .env  # Добавить TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID
```

---

### 1. Email Validator

**Задача:** Проверка списка email-адресов через MX и SMTP handshake.

**Запуск:**

```bash
# Базовая проверка
python scripts/email_validator.py data/emails_sample.txt

# С выводом в JSON
python scripts/email_validator.py emails.txt --format json --output results.json
```

**Результат:**

```
Validating 6 emails...

✅ test@gmail.com        → Catch-all (Risky)
❌ invalid.email         → Invalid (Syntax)
✅ admin@example.com     → Valid
❌ user@noexist.com      → Invalid (No MX)

📊 SUMMARY:
   Total: 6
   Valid: 2
   Invalid: 4

💾 Results saved to: validation_results_1707350400.txt
```

**Статусы валидации:**

- **Домен валиден** → `Valid` — адрес существует
- **Домен отсутствует** / **MX-записи некорректны** → `Invalid (No MX)`
- **Некорректный формат** → `Invalid (Syntax)`
- **Ящик не найден** → `Invalid (Mailbox Not Found)` — домен есть, но user не существует

**Как это работает:**

1. Проверка синтаксиса (RFC 5322)
2. DNS lookup для MX-записей
3. SMTP handshake:
   ```
   CONNECT → EHLO → MAIL FROM → RCPT TO → QUIT → CLOSE
   ```
4. Корректное завершение через `QUIT` (предотвращает IP-бан)
5. Rate limiting между проверками (защита от блокировок)

---

### 2. Telegram Sender

**Задача:** Отправка текста из файла в Telegram-чат через бота.

**Запуск:**

```bash
# Создать сообщение
echo "✅ Email validation complete!" > message.txt

# Отправить
python scripts/tg_sender.py message.txt
```

**Результат:**

```
✅ Message sent successfully!
   Message ID: 12345
```

**Как это работает:**

- Чтение текста из файла
- Отправка через Telegram Bot API
- Retry logic при временных сбоях (502/503)
- Обработка rate limits (429)

---

### 3. Архитектура на 1200 аккаунтов

**Задача:** Предложить архитектуру для обслуживания 1200 email-адресов с минимальной стоимостью.

**Решение:** См. `ARCHITECTURE.md` — полная разбивка с расчётом ~$335/мес.

**Кратко:**

- **Оркестрация:** n8n self-hosted (экономия $1000/год vs Zapier)
- **Инфраструктура:** 8 VPS (Contabo) + 150 residential proxies
- **Email:** 40 custom domains на Postfix VPS (избегаем Gmail $2400/мес)
- **Мониторинг:** Google Postmaster + MXToolbox
- **Warmup:** 35 дней до полной нагрузки

---

### 4. AI-стек

**Задача:** Описать используемые AI-инструменты.

**Решение:** См. `AI_STACK.md` — детали по IDE, моделям, MCP, cursorrules.

**Кратко:**

- **IDE:** Cursor + Claude 3.5 Sonnet
- **Применение:** Генерация boilerplate, API wrappers, docstrings
- **Философия:** AI ускоряет рутину, архитектура — моя

---

## Технические детали

### Почему именно так?

**SMTP QUIT команда:**
Большинство валидаторов пропускают `smtp.quit()` перед закрытием соединения. Серверы трекают незавершенные сессии → после 20-50 проверок IP попадает в blacklist. Решение: явный QUIT перед CLOSE.

**Rate limiting:**
Gmail блокирует после ~20 проверок за минуту. Решение: задержка 2 секунды между проверками (настраивается через `--rate-limit`).

**Telegram retry logic:**
Cloudflare перед Telegram API иногда отдаёт 502/503. Без retry = потеря сообщений. Решение: 3 попытки с экспоненциальным backoff (2s → 4s → 8s).

**Выбор requests вместо aiogram:**
aiogram = 20+ зависимостей + async overhead. Для отправки одного сообщения избыточно. requests = 1 зависимость, делает ровно то, что нужно.

---

## Структура проекта

```
polza-outreach-toolkit/
├── scripts/
│   ├── email_validator.py  # Основной валидатор
│   └── tg_sender.py         # Telegram sender
├── utils/
│   └── logger.py            # Логирование
├── data/
│   ├── emails_sample.txt    # Примеры для теста
│   └── message_sample.txt
├── requirements.txt         # Минимальные зависимости
├── .env.example
├── README.md
├── ARCHITECTURE.md          # Детали архитектуры на 1200 аккаунтов
└── AI_STACK.md              # AI-инструменты и процесс
```

---

## Известные ограничения

**Email Validator:**
- Нет асинхронности — последовательная проверка (для async версии нужен asyncio + connection pool)
- Catch-all detection работает только для известных провайдеров (Gmail, Outlook)
- Требуется VPS с открытым портом 25 (residential IP блокируют SMTP)

**Telegram Sender:**
- Отправка по одному сообщению (для batch нужен прямой Bot API)
- Нет enforce rate limits Telegram (30 msg/sec, 20 msg/min на чат)

**Архитектура:**
- Custom domains имеют ниже trust score чем Gmail/Outlook (inbox rate 75-85% vs 90%+)
- Warmup 35 дней нельзя ускорить без риска spam classification
- Single point of failure на главном n8n VPS (для HA нужен failover +$20/мес)

---

## Дополнительно: Расширенные возможности (опционально)

Если нужна интеграция с n8n или автоматизация workflow:

### REST API

```bash
# Запустить API
python api.py

# Проверить health
curl http://localhost:5000/health

# Валидировать через API
curl -X POST http://localhost:5000/validate \
  -H "Content-Type: application/json" \
  -d '{"emails": ["test@example.com"]}'
```

**Endpoints:**
- `GET /health` — статус сервиса
- `POST /validate` — batch валидация (до 100 emails)
- `POST /telegram/send` — отправка в Telegram

### Docker Deployment

```bash
# Одиночный контейнер
docker build -t polza-toolkit .
docker run -d -p 5000:5000 --env-file .env polza-toolkit

# Полный стек (n8n + PostgreSQL + Redis)
docker-compose up -d
```

**Доступ:**
- n8n: http://localhost:5678
- API: http://localhost:5000

### n8n Integration

Пример workflow:

```
1. Schedule Trigger (daily 9 AM)
2. Google Sheets → Load leads
3. HTTP Request → POST /validate
4. Filter → Only valid emails
5. Loop → Send personalized emails
6. HTTP Request → POST /telegram/send (notify)
```

---

**Built with Claude 3.5 Sonnet for rapid development**
