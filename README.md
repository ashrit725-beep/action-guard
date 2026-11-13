# Vexen

**Security for AI agents.** Vexen sits between an AI agent and the things it can touch. Every action an
agent tries gets one of three answers: **Allowed**, **Blocked** or **Needs your OK**. The decision is made on
the server, starts from "no", and is written to a tamper-evident history.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ashrit725-beep/action-guard)

It is one website and one server in one container: the marketing site, the sign-in and dashboard, and the API
that agents call, all at one address.

| Part | What it is | Where |
| --- | --- | --- |
| Website and app | React (Create React App, Tailwind, shadcn/ui) | [`frontend/`](frontend) |
| Server and API | FastAPI, MongoDB, one process | [`backend/`](backend) |
| Agent SDK | One file an agent developer puts in front of an action | [`sdk/python/vexen.py`](sdk/python/vexen.py) |
| Container | Builds the site, then serves it with the API | [`Dockerfile`](Dockerfile) |

## AI: Anthropic only

Two features use AI: the plain-English **rule writer** and the in-app **helper**. Both run on Anthropic's
Claude (`claude-opus-5-5`) and nothing else.

- The only AI credential is **`ANTHROPIC_API_KEY`**, an Anthropic API key (it starts with `sk-ant-`).
- A key from any other provider is refused at startup with a plain explanation, and nothing is sent.
- Requests go to `https://api.anthropic.com` and nowhere else. `ANTHROPIC_BASE_URL`,
  `ANTHROPIC_AUTH_TOKEN` and `ANTHROPIC_CUSTOM_HEADERS` in the environment are ignored, so nothing can
  redirect the traffic or swap the credential.
- Anthropic itself has the last word: at startup the server asks the API whether it accepts the key, and a
  key that is refused switches the AI features off instead of failing on every click.
- Every model call goes through one file, [`backend/vexen/llm.py`](backend/vexen/llm.py). A test fails if the
  backend imports another provider's SDK, any HTTP or socket client, or a second Anthropic client, or if
  anything other than that file reads the `ANTHROPIC_*` settings.

Without a key the product still works; the rule writer and the helper are simply switched off. The agent keys
that begin with `vex_sk_live_` are Vexen's own credentials for agents, not an AI provider's.

## Deploy it

[`docs/DEPLOY.md`](docs/DEPLOY.md) is the step-by-step guide (about 20 minutes): a free MongoDB Atlas database,
an Anthropic key, and Render. The short version:

1. Create a MongoDB Atlas free cluster and copy its connection string.
2. Create an Anthropic API key.
3. Press **Deploy to Render** above, paste the two values when asked, and wait for the first build.

Run it on exactly **one** instance: the rate limits and the email worker live inside the process.

## Run it on your computer

You need Python 3.12, Node 22 with Yarn 1, and MongoDB (`mongod`, or `docker run -p 27017:27017 mongo:7`).

```bash
# 1. build the website once; the server serves it
cd frontend && yarn install && yarn build && cd ..

# 2. start the server (it looks for the website when it starts, so build first)
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env              # then set JWT_SECRET (python scripts/gen_secrets.py) and, for AI, ANTHROPIC_API_KEY
uvicorn server:app --reload --port 8000        # open http://localhost:8000
```

For live reload while you change the website, run its dev server next to the API instead
(open http://localhost:3000). Add `CORS_ORIGINS=http://localhost:3000` to `backend/.env` and restart the server:

```bash
cd frontend && REACT_APP_BACKEND_URL=http://localhost:8000 yarn start
```

Or build the container exactly as it is deployed:

```bash
docker build -t vexen .
docker run -p 8000:10000 --add-host=host.docker.internal:host-gateway --env-file backend/.env \
  -e MONGO_URL=mongodb://host.docker.internal:27017 -e PUBLIC_APP_URL=http://localhost:8000 vexen
# then open http://localhost:8000 (inside a container, 127.0.0.1 is the container itself, so MONGO_URL
# points at the host; the image also needs PUBLIC_APP_URL, as it is built for production)
```

## Tests

```bash
(cd backend && python -m pytest -n 0)                        # unit tests, no database or network needed
VEXEN_BASE=http://127.0.0.1:8000 python tests/smoke_e2e.py   # end to end, from this folder, against a running server
```

GitHub Actions runs both on every push to `main` and every pull request, builds the website with warnings as
errors, builds the Docker image and checks the running container. The smoke test turns the AI checks on when the server has a working
Anthropic key and checks that they are cleanly off when it has not.

## Configuration

Everything is an environment variable; [`backend/.env.example`](backend/.env.example) lists them all with
notes. The ones that matter:

| Variable | |
| --- | --- |
| `MONGO_URL`, `DB_NAME` | The database. Required. |
| `JWT_SECRET` | Signs sessions and emailed links. Required, 32+ characters. |
| `API_KEY_PEPPER` | Strengthens stored agent keys. Set once, never change. |
| `ANTHROPIC_API_KEY` | The only AI credential. Optional; without it the AI features are off. |
| `ANTHROPIC_WORKSPACE_ID` | Only for an Anthropic key that is not tied to one workspace (`wrkspc_…`). |
| `AI_DAILY_CALL_LIMIT` | Ceiling on AI requests per 24 hours across all users (default 500; `0` = none). |
| `PUBLIC_APP_URL` | The site's address, used in emails. Automatic on Render and Railway. |
| `SMTP_*`, `VAPID_*` | Email alerts and phone notifications. Optional. |

The server refuses to start, with a plain message, if the database address or the signing secret is missing
or unusable. `/api/health` answers instantly for the host's health check; `/api/ready` also asks the database
and reports whether the AI is ready.

## Repository map

```
backend/            FastAPI server (vexen/ holds the code, tests/ the unit tests)
  vexen/llm.py      the one door to the AI provider: Anthropic only
  vexen/site.py     serves the built website next to the API
frontend/           the website and app (React)
sdk/python/         the agent SDK
tests/smoke_e2e.py  end-to-end check against a running server
Dockerfile          website + server in one image
render.yaml         one-click setup for Render
docs/DEPLOY.md      deployment guide
```

`deck/`, `memory/` and `.demovideo/` hold fundraising and demo material. They are not part of the product and
are not shipped in the container.
