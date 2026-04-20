# Async Payments Service

Микросервис асинхронного процессинга платежей на FastAPI + PostgreSQL + RabbitMQ (FastStream) с Outbox pattern, idempotency, retry и DLQ.

## Что реализовано

- `POST /api/v1/payments` с обязательными `X-API-Key` и `Idempotency-Key`
- `GET /api/v1/payments/{payment_id}`
- Outbox pattern (`payments` + `outbox` в одной транзакции)
- Relay, публикующий outbox-события в очередь
- Consumer:
  - эмуляция gateway (2-5 сек, 90% success / 10% fail)
  - обновление статуса платежа
  - webhook с retry (3 попытки, задержки 1s/2s/4s)
  - отправка в DLQ при окончательном фейле нотификации

## Запуск

```bash
docker compose up --build
```

Сервисы:
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- RabbitMQ UI: `http://localhost:15672` (`guest/guest`)

## Полный тест-план в Postman

### 0) Подготовка Postman Environment

Создай Environment с переменными:
- `baseUrl = http://localhost:8000`
- `apiKey = super-secret-key`
- `idemKey = {{guid}}` (или руками UUID)
- `paymentId =` (пусто)
- `webhookUrl = https://webhook.site/<your-id>`

### 1) Healthcheck

**GET** `{{baseUrl}}/healthz`

Ожидание:
- `200`
- `{"status":"ok"}`

### 2) Создание платежа (happy path)

**POST** `{{baseUrl}}/api/v1/payments`

Headers:
- `X-API-Key: {{apiKey}}`
- `Idempotency-Key: {{idemKey}}`
- `Content-Type: application/json`

Body:
```json
{
  "amount": 1500.50,
  "currency": "RUB",
  "description": "Order #1001",
  "metadata": {"order_id": "1001", "customer_id": "c-1"},
  "webhook_url": "{{webhookUrl}}"
}
```

Ожидание:
- `202 Accepted`
- есть `payment_id`, `status=pending`, `created_at`

Сохрани `payment_id` в переменную `paymentId`.

### 3) Идемпотентный повтор с тем же body

Повтори тот же запрос с тем же `Idempotency-Key` и тем же body.

Ожидание:
- `200 OK`
- тот же `payment_id`

### 4) Конфликт идемпотентности

Повтори с тем же `Idempotency-Key`, но измени body (например `amount`).

Ожидание:
- `409 Conflict`
- `detail: "Idempotency key already used with different payload"`

### 5) Проверка статуса платежа

**GET** `{{baseUrl}}/api/v1/payments/{{paymentId}}`

Headers:
- `X-API-Key: {{apiKey}}`

Ожидание:
- сразу после создания: чаще `pending`
- через 2-10 сек: `succeeded` или `failed`
- `processed_at` заполнится после обработки

### 6) Проверка аутентификации

#### 6.1 Нет API-ключа
- Удали `X-API-Key`
- Ожидание: `422` (header required)

#### 6.2 Неверный API-ключ
- `X-API-Key: bad-key`
- Ожидание: `401`, `Invalid API key`

### 7) Валидация входных данных (границы)

#### 7.1 `amount <= 0`
- `amount: 0`
- Ожидание: `422`

#### 7.2 Неизвестная валюта
- `currency: GBP`
- Ожидание: `422`

#### 7.3 Пустое описание
- `description: ""`
- Ожидание: `422`

#### 7.4 Невалидный URL webhook
- `webhook_url: "not-url"`
- Ожидание: `422`

### 8) Проверка 404

**GET** `{{baseUrl}}/api/v1/payments/00000000-0000-0000-0000-000000000000`

Ожидание:
- `404 Payment not found`

### 9) Webhook + retry + DLQ (пограничный сценарий)

Цель: проверить, что webhook не доставился и сообщение ушло в DLQ.

#### Шаги:
1. Создай платеж с `webhook_url: https://example.com/always-fails` (или любой URL, который стабильно вернет не-2xx/ошибку).
2. Подожди ~10-20 сек.
3. Открой RabbitMQ UI -> Queues.
4. Проверь очередь `payments.dlq`: должна увеличиться на 1 сообщение.

Ожидание:
- В БД статус платежа все равно `succeeded/failed` по результату gateway-эмуляции.
- DLQ отражает провал именно этапа нотификации.

### 10) Проверка, что обработка асинхронная

Сделай `POST /payments`, замерь время ответа.

Ожидание:
- API возвращает быстро (без ожидания 2-5 сек gateway)
- статус меняется позже через consumer

## Полезные команды

```bash
docker compose logs -f api
docker compose logs -f relay
docker compose logs -f consumer
docker compose down -v
```

## Примечания

- В этом варианте `Idempotency-Key` уникален глобально.
- Результат платежа (`succeeded/failed`) не откатывается из-за недоставленного webhook; проблемы нотификации уходят в DLQ.
