# Mobius

AI-powered personal productivity assistant. Automate social media posts, manage Google Calendar/Gmail, schedule recurring tasks, and chat with multiple AI models — all from one app.

## Architecture

```
┌──────────────┐     WebSocket/REST     ┌──────────────────┐
│  mobius-app   │ ◄──────────────────► │  mobius-server     │
│  Flutter      │                       │  FastAPI + Python  │
│  (mobile/web) │                       │                    │
└──────────────┘                       ├──────────────────┤
                                        │  LiteLLM (AI)     │
                                        │  APScheduler       │
                                        │  Redis + SQLite    │
                                        └──────────────────┘
                                               │
                                    ┌──────────┼──────────┐
                                    ▼          ▼          ▼
                               Google    Twitter    Notion
                               Calendar  Instagram  LinkedIn
                               Gmail
```

## What it does

- **AI Chat** — Talk to Gemini Flash (free), Claude, or GPT-4o. Responses stream in real-time via WebSocket.
- **Integrations** — OAuth-connected to Google (Calendar + Gmail), Twitter/X, Instagram, LinkedIn, and Notion. The AI can post tweets, create calendar events, send emails, etc.
- **Scheduled Automations** — Cron-based tasks that run automatically (e.g., "post a daily summary to Twitter at 9am").
- **Multi-model support** — Users store their own API keys. Gemini Flash works free; Claude and GPT-4o with user-provided keys.
- **Android Accessibility** — Device automation via Android's Accessibility Service (open apps, read screen, tap elements).

## Quick Start

### 1. Server

```bash
cd mobius-server

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your keys (GEMINI_API_KEY, OAuth credentials, etc.)

# Run (SQLite for dev — no Postgres needed)
# Set DATABASE_URL=sqlite+aiosqlite:///./mobius.db in .env
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Verify
curl http://localhost:8000/health
# → {"status": "ok"}
```

### 2. App (Flutter)

```bash
cd mobius-app

# Get dependencies
flutter pub get

# Run on Android emulator, Chrome, or desktop
flutter run -d chrome
flutter run -d emulator-5554
flutter run -d windows  # requires Developer Mode
```

### 3. Test the AI chat via terminal (no Flutter needed)

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass"}'

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Save your Gemini API key
curl -X PUT http://localhost:8000/auth/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider":"gemini","key":"YOUR_GEMINI_KEY"}'

# Chat via WebSocket
python3 -c "
import asyncio, json, websockets
async def chat():
    async with websockets.connect(f'ws://localhost:8000/ws/chat?token=$TOKEN') as ws:
        await ws.send(json.dumps({'message': 'Hello!', 'model': 'gemini-flash'}))
        while True:
            data = json.loads(await ws.recv())
            if data['type'] == 'token': print(data['content'], end='', flush=True)
            elif data['type'] == 'done': break
        print()
asyncio.run(chat())
"
```

## Server API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/auth/register` | POST | Create account |
| `/auth/token` | POST | Login → JWT |
| `/auth/api-keys` | PUT | Store API key (encrypted) |
| `/auth/api-keys` | GET | List stored providers |
| `/ws/chat` | WebSocket | AI chat with streaming |
| `/automations` | GET/POST | List/create automations |
| `/automations/{id}` | DELETE | Delete automation |
| `/oauth/{provider}` | GET | Start OAuth flow |
| `/oauth/{provider}/callback` | GET | OAuth callback |

## Tests

```bash
# Server — 21 tests
cd mobius-server && pytest -v

# App — 22 tests
cd mobius-app && flutter test
```

## Tech Stack

**Server:** Python 3.12, FastAPI, LiteLLM, SQLAlchemy (async), APScheduler, Redis, Fernet encryption

**App:** Flutter, Riverpod, go_router, WebSocket, Dio, Mockito

**AI Models:** Gemini 2.0 Flash (free default), Claude Sonnet, GPT-4o (user key required)

## Project Structure

```
mobius/
├── mobius-server/
│   ├── app/
│   │   ├── main.py              # FastAPI app + scheduler
│   │   ├── core/                 # config, database, redis, security
│   │   ├── api/                  # auth, chat (WebSocket), automations
│   │   ├── agents/               # LiteLLM engine + tool loop
│   │   ├── integrations/         # Google, Twitter, Instagram, LinkedIn, Notion
│   │   └── models/               # User, Conversation, Message, Automation
│   └── tests/                    # 21 tests (pytest-asyncio)
│
├── mobius-app/
│   ├── lib/
│   │   ├── main.dart
│   │   ├── app.dart              # GoRouter + bottom nav (4 tabs)
│   │   ├── core/                 # theme, storage
│   │   ├── features/
│   │   │   ├── auth/             # login/signup + JWT
│   │   │   ├── chat/             # streaming chat + model selector
│   │   │   ├── settings/         # server URL, model, API keys
│   │   │   ├── integrations/     # OAuth status + connect
│   │   │   └── automations/      # CRUD + cron scheduling
│   │   └── services/             # WebSocket, auth, backend client, device agent
│   └── test/                     # 22 tests (flutter_test + mockito)
│
└── README.md
```
