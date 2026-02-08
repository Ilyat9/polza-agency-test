# Архитектура для 1200 Email-Аккаунтов

**Задача:** Обслуживать 1200 email-адресов для аутрич-кампаний с минимальной стоимостью и достаточной надёжностью.

**Цель:** ~60,000 писем/день (50 писем/аккаунт), inbox rate 75-85%, стоимость ~$335/мес.

---

## Инфраструктура

### Серверы и сеть

**Главный orchestrator (n8n):**
- Hetzner CX31: 2 vCPU, 4GB RAM, 80GB SSD
- $10/мес
- Развёртывание: Docker Compose (n8n + PostgreSQL + Redis)
- Зачем: управление всеми workflow — warmup, рассылки, мониторинг

**Sending nodes (8 VPS):**
- Contabo VPS S: 4 vCPU, 8GB RAM, 200GB SSD
- $6/мес × 8 = $48/мес
- По 150 аккаунтов на ноду
- Каждая нода = Postfix SMTP + Python scripts для отправки
- Datacenter IP включён

**Proxy pool:**
- 150 residential 4G IP (IPRoyal / Soax)
- $1.30/IP × 150 = $195/мес
- Распределение: 8 аккаунтов на 1 IP
- Зачем: ротация при падении reputation, warmup чистых IP

**Итого инфраструктура:** $10 + $48 + $195 = **$253/мес**

---

### Email-аккаунты

**Доменная стратегия:**

- 40 доменов bulk-закупка (Namecheap): $10/год каждый
- $400/год = $33/мес + буфер = **$40/мес**
- Распределение: 30 аккаунтов на домен
- Ротация: каждые 3 месяца покупка новых, старые в cooldown

**SMTP hosting:**
- Postfix на каждой sending node
- Включено в VPS, доп. затрат нет
- Альтернатива: отдельный VPS для централизованного Postfix — $30/мес

**DNS настройка:**
- Cloudflare (бесплатно) для управления DNS
- Автоматизация через API: DMARC, SPF, DKIM
- Скрипт на Python для массовой настройки

**Итого email:** $40 (домены) + $30 (Postfix VPS) = **$70/мес**

**Альтернатива (premium):**
Gmail Workspace / Outlook 365 = $6/аккаунт × 1200 = $7,200/мес — экономически нецелесообразно для аутрича.

---

### Мониторинг

**Google Postmaster API (бесплатно):**
- Domain reputation score
- Spam rate
- IP reputation
- Delivery errors

**MXToolbox Monitoring ($99/год):**
- Blacklist monitoring (100+ lists)
- Real-time alerts
- DMARC/SPF/DKIM validation

**Итого мониторинг:** $99/год ≈ **$10/мес**

**Общая стоимость:** $253 + $70 + $10 = **$333/мес** ≈ **$335-350/мес**

---

## Ротация и лимиты

### IP rotation

**3 тира:**

1. **Tier 1 (Clean IPs)** — residential proxies для новых аккаунтов
   - Warmup первые 2 недели
   - 50 IP в активной ротации
   - Стоимость: $65/мес

2. **Tier 2 (Warmed IPs)** — datacenter IP с нод
   - Основной outreach
   - Included в VPS

3. **Tier 3 (Burned IPs)** — карантин
   - Cooldown 30-60 дней
   - Только internal warmup

**Триггеры ротации:**

- Spam rate > 5% → пауза аккаунта, смена IP
- Reputation < 70% → смена IP в течение 24 часов
- Blacklist hit → карантин, submit delisting request

### Email limits

**Per account:**
- 50 писем/день в production
- Warmup schedule:
  - Неделя 1: 5/день (internal only)
  - Неделя 2: 10/день (50% internal)
  - Неделя 3: 20/день (70% external)
  - Неделя 4: 35/день
  - Неделя 5+: 50/день (full capacity)

**Общий warmup:** 35 дней от регистрации до полной нагрузки.

**Per IP:**
- Max 10 аккаунтов на residential IP
- Max 500 писем/день/IP
- Текущее: 1200 аккаунтов ÷ 150 IP = 8 аккаунтов/IP → запас 20%

### Domain rotation

- 50 доменов закуплены (10 в резерве)
- Ротация каждые 3 месяца
- Aging strategy: новые домены начинают с warmup, старые уходят в cooldown
- Cloudflare API для автоматической настройки DNS

---

## Распределение нагрузки

### n8n Workflows

**Workflow 1: Email Warmup (Cron каждый час, 8:00-20:00)**
```
1. Trigger (hourly)
2. Load warmed accounts from DB (PostgreSQL)
3. For each account:
   - Generate email between own accounts
   - Randomize timing (±15 min jitter)
   - Send via SMTP
   - Mark as opened / replied (simulate engagement)
4. Update warmup stats
```

**Workflow 2: Outreach Campaign**
```
1. Load leads from Google Sheets
2. Filter: only valid emails (via validation API)
3. AI personalization (Claude API)
4. Distribute across 1200 accounts (round-robin)
5. Rate limit: 50/day/account
6. Send via SMTP (each node = 150 accounts)
7. Track: pixel + redirect links
```

**Workflow 3: Reputation Monitoring (Cron каждые 6 часов)**
```
1. Query Google Postmaster API
2. Query MXToolbox blacklists
3. Parse reputation data
4. If reputation < 70%:
   - Pause account
   - Trigger IP rotation
   - Send Telegram alert
5. Update dashboard
```

### Load balancing

- PostgreSQL хранит состояние аккаунтов (reputation, send count, last send time)
- n8n делает round-robin при распределении писем
- Каждая sending node обрабатывает свою часть (150 аккаунтов)
- Redis queue для retry failed sends

**Bottlenecks:**

1. **n8n capacity:** 10,000+ workflow executions/день — достаточно
2. **PostgreSQL write throughput:** при необходимости — read replica
3. **Network bandwidth:** 1Gbps на VPS = 0.5% использования при 5000 писем/час — не bottleneck

---

## Риски и способы закрытия

### Риск 1: Блокировка порта 25

**Проблема:** Большинство cloud providers блокируют исходящий порт 25.

**Решение:**
- Использовать Hetzner / Contabo (порт 25 открыт)
- Для warmup: residential proxies с SOCKS5
- Fallback: SMTP relay через SendGrid ($15/мес за 40k писем, но теряем контроль)

### Риск 2: Catch-all домены

**Проблема:** Gmail, Outlook принимают любые RCPT TO → невозможно проверить существование ящика.

**Решение:**
- Whitelist известных catch-all провайдеров
- Метка "Risky" вместо "Valid"
- Дополнительная проверка через email-finder API ($0.01/email) для важных лидов

### Риск 3: IP warmup срыв

**Проблема:** Слишком быстрый рост объёма → spam classification.

**Решение:**
- Строгое соблюдение warmup schedule
- Мониторинг spam rate ежедневно
- При spike > 3% → пауза на 48 часов
- Automated rollback: если reputation падает, снижаем volume на 50%

### Риск 4: Single point of failure (n8n VPS)

**Проблема:** Если главный orchestrator падает → все workflow останавливаются.

**Решение:**
- Еженедельный backup workflow definitions (экспорт в Git)
- Monitoring: UptimeRobot (бесплатно) с Telegram alerts
- Для HA: failover node + синхронизация через PostgreSQL replication (+$20/мес)

### Риск 5: Deliverability custom domains

**Проблема:** Custom domains имеют inbox rate 70-80% против 90%+ у Gmail.

**Решение:**
- Warmup 35 дней обязателен
- Качественный контент (low spam score)
- Engagement: просить replies, избегать mass templates
- A/B testing subject lines
- Реалистичные ожидания: не 95%, а 75-85%

---

## Масштабирование

**От 1200 до 5000 аккаунтов:**

| Компонент | Текущее | Целевое | Прирост |
|-----------|---------|---------|---------|
| VPS nodes | 8 | 33 | +25 (+$150/мес) |
| Proxies | 150 IP | 500 IP | +350 (+$455/мес) |
| Domains | 40 | 125 | +85 (+$85/мес) |
| **Итого** | $335/мес | $1,025/мес | +$690/мес |

**Cost per email:**
- 1200 аккаунтов: $335 ÷ 60,000 = $0.0058/письмо
- 5000 аккаунтов: $1,025 ÷ 250,000 = $0.0041/письмо

**Вывод:** экономия на масштабе начинается с 3000+ аккаунтов.

---

## Что НЕ делаем

❌ **Kubernetes** — избыточно для 8 нод, Docker Compose достаточно  
❌ **Микросервисы** — монолитный n8n проще и надёжнее  
❌ **Machine Learning для catch-all detection** — ROI низкий, hardcoded whitelist работает  
❌ **Grafana/Prometheus full stack** — Google Postmaster + MXToolbox дешевле и достаточно  
❌ **AWS SES для cold outreach** — агрессивная блокировка при жалобах  

---

## Итоговая стоимость

**Минимальная конфигурация:**

```
Инфраструктура:
  Hetzner CX31 (orchestrator)    $10
  Contabo VPS S × 8              $48
  Residential proxies (150 IP)  $195

Email:
  Domains (40)                   $40
  Postfix VPS                    $30

Monitoring:
  MXToolbox                      $10
  
═══════════════════════════════════
ИТОГО:                          $333/мес
```

**С буфером:** $335-350/мес

**Alternative (premium):**
Gmail Workspace (1200) = $7,200/мес — **в 21 раз дороже**, нецелесообразно.

---

**Built for Polza Agency outreach operations**
