# Архитектура для 1200 Email-Аккаунтов

**Цель:** Обслуживать 1200 email-адресов для аутрич-кампаний — ~60,000 писем/день (50 писем/аккаунт), inbox rate 75-85%, стоимость ~$350/мес.

---

## Инфраструктура

### Серверы

**Orchestrator (n8n):**
- Hetzner CX31: 2 vCPU, 4GB RAM — $10/мес
- Docker Compose (n8n + PostgreSQL + Redis)
- Управление всеми workflows: warmup, рассылки, мониторинг

**Sending Nodes (8 VPS):**
- Contabo VPS S: 4 vCPU, 8GB RAM — $6/мес × 8 = $48/мес
- По 150 аккаунтов на ноду
- Postfix SMTP + Python скрипты для отправки

**Proxy Pool:**
- 150 residential 4G IP (IPRoyal / Soax) — $1.30/IP = $195/мес
- Распределение: 8 аккаунтов на 1 IP
- Ротация при падении reputation

**Стоимость инфраструктуры:** $10 + $48 + $195 = **$253/мес**

---

### Email-домены

**Домены:**
- 40 доменов (Namecheap bulk): $10/год = $33/мес
- 30 аккаунтов на домен
- Ротация каждые 3 месяца

**SMTP:**
- Postfix на каждой sending node или централизованный VPS — $30/мес
- DNS через Cloudflare (бесплатно): DMARC, SPF, DKIM

**Стоимость email:** $33 + $30 = **$63/мес**

---

### Мониторинг

**Google Postmaster API (бесплатно):**
- Domain reputation score
- Spam rate, IP reputation, delivery errors

**MXToolbox Monitoring ($99/год ≈ $10/мес):**
- Blacklist monitoring (100+ lists)
- Real-time alerts, DMARC/SPF/DKIM validation

**Итого:** **$10/мес**

**ОБЩАЯ СТОИМОСТЬ:** $253 + $63 + $10 = **$326/мес** ≈ **$350/мес с буфером**

---

## Лимиты и ротация

### Email лимиты

**Per аккаунт:**
- 50 писем/день в production
- Warmup: 35 дней от регистрации до полной нагрузки
  - Неделя 1-2: 5-10/день (internal только)
  - Неделя 3-4: 20-35/день (mix internal/external)
  - Неделя 5+: 50/день (full capacity)

**Per IP:**
- Max 10 аккаунтов на residential IP
- Max 500 писем/день/IP
- Текущее: 1200 ÷ 150 = 8 аккаунтов/IP (20% запас)

### Автоматическая ротация

**Триггеры:**
- Spam rate > 5% → пауза аккаунта, смена IP
- Reputation < 70% → смена IP в течение 24 часов
- Blacklist hit → карантин 30-60 дней, delisting request

**IP rotation:**
- 50 IP в активной ротации (residential для новых аккаунтов)
- Datacenter IP с VPS для warmed accounts
- Burned IP → cooldown 30-60 дней

**Domain rotation:**
- 40 активных доменов + 10 в резерве
- Новые домены начинают с warmup
- Старые уходят в cooldown каждые 3 месяца

---

## Распределение нагрузки

### n8n Workflows

**Warmup (Cron hourly):**
- Load warmed accounts из PostgreSQL
- Generate emails между своими аккаунтами
- Randomize timing (±15 min jitter)
- Simulate engagement (open/reply)

**Outreach Campaign:**
- Load leads → Filter valid emails → AI personalization (Claude API)
- Distribute across 1200 accounts (round-robin)
- Rate limit: 50/day/account
- Track: pixel + redirect links

**Monitoring (Cron 6h):**
- Query Google Postmaster + MXToolbox
- Parse reputation data
- If reputation < 70%: pause account, trigger rotation, Telegram alert

### Load Balancing

- PostgreSQL: состояние аккаунтов (reputation, send count, last send)
- n8n: round-robin при распределении писем
- Каждая node обрабатывает свою часть (150 аккаунтов)
- Redis queue для retry failed sends

**Bottlenecks:**
- n8n capacity: 10,000+ workflow executions/день ✅
- PostgreSQL write: при необходимости — read replica
- Network: 1Gbps на VPS = 0.5% использования ✅

---

## Ключевые риски и решения

| Риск | Решение |
|------|---------|
| **Блокировка порта 25** | Использовать Hetzner/Contabo (порт 25 открыт). Fallback: SMTP relay SendGrid. |
| **IP warmup срыв** | Строгий warmup schedule. Мониторинг spam rate ежедневно. Auto rollback при spike. |
| **Catch-all домены** | Whitelist известных провайдеров. Метка "Risky" вместо "Valid". Email-finder API для важных лидов. |
| **Single point of failure** | Weekly backup workflow definitions в Git. UptimeRobot мониторинг. Failover node (+$20/мес). |

---

## Масштабирование

**От 1200 до 5000 аккаунтов:**

| Компонент | 1200 аккаунтов | 5000 аккаунтов | Прирост |
|-----------|---------------|----------------|---------|
| VPS nodes | 8 | 33 | +$150/мес |
| Proxies | 150 IP | 500 IP | +$455/мес |
| Domains | 40 | 125 | +$85/мес |
| **Итого** | $350/мес | $1,040/мес | +$690/мес |

**Cost per email:**
- 1200 аккаунтов: $350 ÷ 60,000 = **$0.0058/письмо**
- 5000 аккаунтов: $1,040 ÷ 250,000 = **$0.0042/письмо**

Экономия на масштабе начинается с 3000+ аккаунтов.

---

## Итого

✅ **Масштабируемая архитектура** для 1200 email-аккаунтов  
✅ **Автоматизация** через n8n workflows  
✅ **Мониторинг** и автоматическая ротация при проблемах  
✅ **Стоимость** ~$350/мес против Gmail Workspace $7,200/мес (в 20 раз дешевле)  
✅ **Production-ready** с warmup, rate limiting, retry logic  

**Built for Polza Agency outreach operations**
