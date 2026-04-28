# astro-aries-automation

Private automation system for ASTRO ARIES STUDIO.

## Backend

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Run locally:

```bash
uvicorn backend.app:app --reload
```

Required environment variables:

```bash
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
```

## Health check

```bash
curl http://127.0.0.1:8000/health
```

Expected:

```json
{"status":"ok"}
```

## Create order directly

```bash
curl -X POST http://127.0.0.1:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Test",
    "last_name": "Klijent",
    "email": "test@example.com",
    "phone": "+38160000000",
    "instagram_username": "test_astro",
    "service_name": "Natalna Karta + Predikcije",
    "price_rsd": 3300,
    "birth_date": "08.05.1967",
    "birth_time": "10:10",
    "birth_place": "Split, Hrvatska",
    "message": "Test porudzbina",
    "status": "received"
  }'
```

## Orchestrator agent

List registered tasks:

```bash
curl http://127.0.0.1:8000/agents
```

Run order creation through the orchestrator:

```bash
curl -X POST http://127.0.0.1:8000/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "orders.create",
    "payload": {
      "first_name": "Test",
      "email": "test@example.com",
      "service_name": "Natalna Karta + Predikcije",
      "price_rsd": 3300,
      "birth_date": "08.05.1967",
      "birth_time": "10:10",
      "birth_place": "Split, Hrvatska",
      "status": "received"
    }
  }'
```

Current orchestrator tasks:

- `orders.create` — creates an order in the existing Supabase `orders` table.
- `instagram.comment_reply` — placeholder until Meta handler is enabled.
- `email.send` — placeholder until mail handler is enabled.
