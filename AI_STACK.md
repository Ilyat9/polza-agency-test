# AI-Стек и процесс разработки

---

## IDE и инструменты

**Основное:**
- **Cursor** (AI-first IDE на базе VS Code)
- **VS Code** (для code review и git workflows)

**Зачем Cursor:**
- Inline AI suggestions во время кодинга
- Cmd+K для instant refactoring
- AI chat с контекстом всего проекта
- Автогенерация тестов

---

## AI-плагины и модели

### Модели

**Claude 3.5 Sonnet** (основная):
- Применение: Python код, архитектурные решения, документация
- Почему: минимум галлюцинаций, хорошо понимает контекст, сильный в reasoning
- Где: Cursor встроенный chat, также через API для прототипов

**GPT-4o** (вспомогательная):
- Применение: быстрый lookup библиотек, brainstorming, research
- Почему: faster than Claude для простых queries
- Где: веб-интерфейс ChatGPT

### Что делаю с AI, что — сам

**AI генерирует:**
- Boilerplate код (docstrings, type hints, imports)
- Wrapper-функции для внешних API (Telegram, DNS)
- Базовые тесты (pytest fixtures)
- Документацию (README секции, комментарии)

**Я делаю сам:**
- Архитектурные решения (выбор n8n vs Zapier, requests vs aiogram)
- Бизнес-логика (warmup schedule, rate limiting strategy)
- Trade-off analysis (стоимость vs надёжность)
- Debugging сложных багов (SMTP handshake, IP rotation logic)

**Процесс:**
1. Придумываю архитектуру на бумаге / в уме
2. AI пишет скелет кода (классы, функции, типы)
3. Я дополняю логику, убираю лишнее
4. AI помогает с edge cases и error handling
5. Я ревьюю финальный код построчно

---

## MCP (Model Context Protocol)

**Используемые MCP servers:**

1. **filesystem** — чтение/запись файлов проекта
2. **brave-search** — поиск документации библиотек
3. **github** — работа с репозиториями

**Зачем MCP:**
- AI видит всю структуру проекта
- Может читать `.env.example`, `requirements.txt` для контекста
- Не нужно копипастить код в чат

**Примеры использования:**
- "Посмотри на email_validator.py и добавь rate limiting"
- "Найди в документации dnspython как правильно обрабатывать NXDOMAIN"
- "Создай .env.example на базе существующего .env"

---

## .cursorrules / System Instructions

**Используемые правила:**

```yaml
# .cursorrules
rules:
  - "Always use Type Hints (PEP 484)"
  - "Pydantic for validation, not raw dicts"
  - "Functions: max 50 lines, single responsibility"
  - "Prefer composition over inheritance"
  - "Google-style docstrings for public functions"
  - "Explicit error handling, no silent failures"
  - "Enums for status/state (not magic strings)"
  - "Readability > premature optimization"
  - "Wrap external APIs in try/except with specific errors"
  - "Use logging module, not print()"
```

**Самые полезные правила:**

1. **"Always use Type Hints"** — AI генерирует сразу типизированный код, экономит время на рефакторинг
2. **"Enums for status/state"** — AI не делает magic strings типа `if status == "valid"`, делает `if status == ValidationStatus.VALID`
3. **"Functions max 50 lines"** — AI не генерирует monolithic функции на 200 строк
4. **"Explicit error handling"** — AI всегда добавляет try/except с конкретными exception типами

**Пример инструкции для конкретной задачи:**

```
System: You are a Python backend engineer focused on automation.
Prefer simple, maintainable code over clever solutions.
Use requests library for HTTP calls (not aiogram or telebot).
Always add logging statements for debugging.
When handling SMTP, always call smtp.quit() before smtp.close().
```

---

## Процесс разработки (High-Speed Development)

### Типичный workflow

**Задача:** Добавить retry logic в Telegram sender

**Шаги:**

1. **Формулирую задачу AI:**
   ```
   Add retry logic to tg_sender.py:
   - Max 3 attempts
   - Exponential backoff: 2s, 4s, 8s
   - Handle 429 (rate limit) with Retry-After header
   - Handle 502/503 (transient errors)
   ```

2. **AI генерирует код:**
   ```python
   def _make_request_with_retry(self, url, method='POST', **kwargs):
       for attempt in range(self.max_retries):
           # ... generated code
   ```

3. **Я ревьюю и правлю:**
   - Проверяю edge cases (что если Retry-After отсутствует?)
   - Добавляю logging
   - Упрощаю сложные места

4. **AI генерирует тесты:**
   ```python
   def test_retry_on_502():
       # ... generated test
   ```

5. **Я запускаю и дебажу:**
   - Ловлю баг: забыли обработать ConnectionError
   - Прошу AI: "Add ConnectionError handling to retry logic"
   - AI добавляет, я проверяю

**Время:** задача на 2 часа решена за 30 минут.

### Ускорение через AI

**Без AI:**
- Написать код: 1 час
- Написать docstrings: 20 минут
- Написать тесты: 40 минут
- Написать документацию: 30 минут
- **Итого: 2.5 часа**

**С AI:**
- Написать код (я задаю архитектуру, AI генерирует): 20 минут
- Docstrings (AI auto-generated): 0 минут
- Тесты (AI генерирует): 10 минут
- Документация (AI генерирует, я правлю): 10 минут
- **Итого: 40 минут**

**Ускорение: ~4x**

---

## Что AI НЕ умеет (делаю сам)

1. **Понимать бизнес-контекст**
   - "Почему warmup 35 дней, а не 7?" — AI не знает email deliverability nuances
   - "Почему n8n, а не Zapier?" — AI не понимает cost optimization для агентства

2. **Debugging сложных багов**
   - "Почему IP попадает в blacklist после 50 проверок?" — нужно знать SMTP best practices
   - "Почему Telegram отдаёт 502 только иногда?" — нужно понимать Cloudflare архитектуру

3. **Архитектурные trade-offs**
   - "Async vs sequential для email validation?" — AI скажет "async быстрее", но не учтёт сложность поддержки
   - "PostgreSQL vs Redis для state?" — AI не понимает операционные затраты

4. **Code review на production-readiness**
   - "Достаточно ли 3 retries для Telegram?" — нужен опыт с API
   - "Правильно ли обрабатываем 5xx коды SMTP?" — нужно знать RFC 5321

---

## Философия использования AI

**AI — это ускоритель, не замена мышлению.**

- AI генерирует код → я решаю, что генерировать
- AI предлагает решения → я выбираю лучшее
- AI объясняет библиотеки → я принимаю архитектурные решения
- AI пишет тесты → я определяю, что тестировать

**Правило 80/20:**
- 80% времени AI делает рутину (boilerplate, docstrings, simple functions)
- 20% времени я делаю критичное (архитектура, сложная логика, debugging)

**Результат:**
- Фокус на решении проблемы, а не на синтаксисе
- Быстрые итерации (MVP за часы, не дни)
- Больше времени на обдумывание, меньше на кодинг

---

## Честно про ограничения

**Что AI не заменит:**

- **Опыт** — AI не знает, что SMTP QUIT критичен, пока я не скажу
- **Контекст** — AI не понимает, что Polza Agency нужна дешевизна, а не красота кода
- **Интуицию** — AI не чувствует, когда архитектура становится overengineered

**Где AI особенно полезен:**

- Интеграция с новыми API (Telegram, Postmaster)
- Генерация однотипного кода (валидаторы, парсеры)
- Написание документации
- Рефакторинг (добавить type hints, разбить функцию)

**Где AI бесполезен:**

- Понимание бизнес-требований
- Debugging production incidents
- Выбор между конкурирующими решениями
- Оценка стоимости и рисков

---

## Итого

**Stack:**
- Cursor + Claude 3.5 Sonnet (основа)
- VS Code (ревью)
- GPT-4o (research)

**MCP:**
- filesystem, brave-search, github

**.cursorrules:**
- Type hints, enums, explicit errors, max 50 lines/function

**Ускорение:**
- 4x быстрее разработка
- Фокус на архитектуре, а не на boilerplate

**Философия:**
- AI ускоряет рутину
- Я делаю архитектуру и принимаю решения
- Код всегда ревьюю сам построчно

---

**Built with Claude 3.5 Sonnet, but thought through by human**
