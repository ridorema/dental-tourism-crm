# Dental Tourism CRM v1

Multi-tenant Flask CRM for dental tourism clinics with lead capture, call-center workflows, attribution, and integrations-ready communications.

## Architecture (high-level)
- `app/models.py`: Core multi-tenant schema (clinic-scoped entities, soft-delete fields, attribution, communications, conversion events).
- `app/tenancy.py`: tenant guard utilities for scoped queries and protected object loading.
- `app/authz.py`: role + permission decorators.
- `app/api/routes.py`: website lead API + webhook stubs (Meta leads, WhatsApp, Voice).
- `app/communications/routes.py`: inbox, thread composer, click-to-call, call queue, unified timeline.
- `app/integrations/routes.py`: Google Ads offline export + website embed snippet.
- `app/settings/routes.py`: clinic settings, pipeline stages, integration credentials, GDPR, audit logs.
- `app/users/routes.py`: admin user management.
- `app/providers/*`: provider adapter interfaces + stub implementations (default).

## Quick Start
```powershell
cd c:\Users\User\Desktop\dental_crm_mvp
.\env\Scripts\activate
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m flask --app run.py db migrate -m "v1 platform upgrade"
python -m flask --app run.py db upgrade
python -m flask --app run.py seed-demo-data
python -m flask --app run.py run
```

Login example:
- workspace: `tirana-smile`
- email: `tirana-smile+admin@example.com`
- password: `admin12345`

## Website Lead API
Endpoint: `POST /api/v1/leads`
Headers:
- `Content-Type: application/json`
- `X-API-Key: <LEAD_API_KEY>`

Example payload:
```json
{
  "clinic_slug": "tirana-smile",
  "first_name": "Mario",
  "last_name": "Rossi",
  "email": "mario@example.it",
  "phone": "+39333111222",
  "landing_page_url": "https://clinic-site.com/implants",
  "referrer_url": "https://google.com",
  "utm_source": "google",
  "utm_medium": "cpc",
  "utm_campaign": "implants_it",
  "utm_term": "all on 4",
  "utm_content": "ad_variant_1",
  "gclid": "abc123",
  "fbclid": "fb123",
  "company_website": ""
}
```

Response:
```json
{"lead_id": 42}
```

Anti-spam included:
- honeypot (`company_website`)
- in-memory rate limiting
- optional CAPTCHA flag (`ENABLE_CAPTCHA=1`)

## WordPress / Elementor Embed
Use Integrations page (`/integrations`) snippet, or base template:
```html
<form id="crmLeadForm">...</form>
<script>
// Capture utm_* / gclid / fbclid from URL and submit via fetch to /api/v1/leads
</script>
```

Steps:
1. Paste snippet into Elementor HTML widget.
2. Replace `clinic_slug`.
3. Keep hidden UTM/GCLID fields.
4. Set `X-API-Key` to `LEAD_API_KEY`.

## Social Lead Ads Webhook (Stub)
Endpoint: `POST /api/v1/webhooks/meta-leads`
- Stores raw payload in `WebhookEvent` and `LeadPayload`.
- Maps normalized fields to a lead when `clinic_slug` is provided.

## WhatsApp + VoIP Stub Mode
Default `.env`:
- `WHATSAPP_PROVIDER=stub`
- `VOICE_PROVIDER=stub`

Features:
- inbox: `/communications/inbox`
- thread + composer + click-to-call: `/communications/thread/<id>`
- call queue: `/communications/queue`
- softphone placeholder: `/communications/softphone`

No external provider accounts required in stub mode.

## Google Ads Offline Conversions Export
When lead status transitions to `accepted`/`completed`, `ConversionEvent` is created (if gclid exists).

Download CSV:
- `/integrations/google-ads-export.csv`

Columns:
- `gclid`
- `conversion_name`
- `conversion_time`
- `conversion_value`
- `currency`
- `order_id` (lead id)

## Security / Isolation Notes
- All app-facing queries are scoped by `clinic_id` using `TenantGuard`.
- Role/permission checks on protected routes.
- Session security flags configured in `app/config.py`.
- Login attempts logged in `LoginAttempt` and `ActivityLog`.

## Production Notes
- Use Postgres via `DATABASE_URL`.
- Replace stub providers with real adapters in `app/providers/`.
- Replace in-memory rate limiter with Redis-backed limiter.
