# Deploying Vexen

Vexen runs as **one container**: the website and the API share one address. You need three things, and the
whole setup takes about 20 minutes.

| You need | Where | Cost |
| --- | --- | --- |
| A database | MongoDB Atlas | Free (512 MB) |
| An AI key | Anthropic Console | Pay as you go, a few cents per AI request |
| A host for the container | Render (recommended) | $7 a month, always on |

When you are done you have a public `https://…onrender.com` address with the website, sign-up, the dashboard
and the API that agents call.

---

## 1. The database: MongoDB Atlas (free)

1. Sign up at <https://www.mongodb.com/cloud/atlas/register> (no card needed).
2. **Create** a cluster, pick the **Free** option, provider **AWS**, region **Oregon (us-west-2)** to sit next to
   Render's Oregon region, and press **Create**.
3. Create a database user (the setup wizard offers it, or **Database Access → Add New Database User**):
   password authentication, a long password made of letters and numbers only, role **Read and write to any
   database**. Keep the password; you need it in a minute.
4. **Network Access → Add IP Address → Allow access from anywhere** (`0.0.0.0/0`). Render does not have a fixed
   address until the service exists; section 5 shows how to tighten this afterwards.
5. **Database → Connect → Drivers**, copy the connection string. It looks like
   `mongodb+srv://USER:<db_password>@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority`.
   Replace `<db_password>` **including the angle brackets** with your password. That is your **`MONGO_URL`**.

## 2. The AI key: Anthropic

1. Open <https://platform.claude.com> (the Anthropic Console). Optional but tidy: create a workspace called
   "Vexen" under **Settings → Workspaces** (its ID, `wrkspc_…`, is in the ID column), so Vexen's usage and limits
   stay separate. Then **API keys → Create key**, inside that workspace, with the expiration set to **Never**
   (an expired key shows up as "rejected"). Copy the key (it starts with `sk-ant-`) and add some credit under
   **Billing**. That is your **`ANTHROPIC_API_KEY`**. If your key is not tied to a single workspace, also set
   **`ANTHROPIC_WORKSPACE_ID`** to the workspace's ID, or every AI request is refused.
2. **Set a monthly spend limit** (Console → **Settings → Spend limits**). Anyone can sign up on a public Vexen,
   so this is your safety net. The server adds its own limits: 20 rule drafts and 40 helper
   questions per person per 5 minutes, at most 8 AI requests at once, and a ceiling of **500 AI requests per
   24 hours across everyone** (`AI_DAILY_CALL_LIMIT`; each typically costs a few cents). Raise it as you grow, or
   set it to `0` to turn it off. That count lives in memory and starts again from zero whenever the service
   restarts or redeploys, so treat it as a brake; the Console spend limit is the hard stop.

This is the only AI key Vexen has. A key from another provider is refused at startup with a message saying so,
and Vexen only ever talks to `api.anthropic.com`.

## 3. The host: Render

1. Sign in at <https://dashboard.render.com> with GitHub.
2. Press **Deploy to Render** in the [README](../README.md), or: **New → Blueprint**, connect the
   `action-guard` repository, and leave the Blueprint path empty. Render reads [`render.yaml`](../render.yaml).
3. Render asks for two values: **`MONGO_URL`** and **`ANTHROPIC_API_KEY`**. Paste them. The signing secret
   (`JWT_SECRET`) and `API_KEY_PEPPER` are generated for you. Add a card if Render asks (the plan is $7 a month).
4. Press **Deploy Blueprint**. The first build takes 5 to 8 minutes. Later pushes to `main` redeploy automatically.

The plan in `render.yaml` is `0.5c-512mb`, always on. A `free` plan exists for trying things out, but it stops
after 15 minutes without visitors (the first visit then waits about a minute), pauses the email worker and
blocks outgoing email ports, so it is not suitable for real use.

## 4. Check that it works

Open your address, `https://<name>.onrender.com`.

- `/api/health` shows `"status":"ok"`.
- `/api/ready` shows `"database":"ok"` and `"ai":"ready"`. If `ai` says something else, see Troubleshooting.
- Sign up, open **Rules**, and write a rule in plain English. That is the Anthropic-backed rule writer.
- The **Ask for help** button is visible in the app. It is hidden when the AI key is not working.

## 5. Tighten and extend (all optional)

**Restrict the database to Render.** In Render open your service → **Connect → Outbound** and copy the listed IP
ranges. In Atlas **Network Access**, add them and delete the `0.0.0.0/0` entry. Check `/api/ready` afterwards.

**Your own domain.** In Render: service → **Settings → Custom Domains**, add it, and create the DNS records it
shows. Then add an environment variable **`PUBLIC_APP_URL=https://your.domain`** so links in emails use it.

**Email alerts** (approval requests, invitations). Add `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`,
`SMTP_PASSWORD` and `SMTP_FROM_EMAIL`. For Gmail use `smtp.gmail.com`, port `587`, and an App Password.

**Phone notifications.** On your computer run
`cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python scripts/gen_secrets.py`,
then add the `VAPID_PUBLIC_KEY` and `VAPID_PRIVATE_KEY` it prints, and set `VAPID_SUBJECT` to
`mailto:` plus your real address.

**Add or change a variable later:** service → **Environment**. New variables in `render.yaml` are not asked for
again after the first deploy; add them there.

**Contact form.** Messages from the website's contact page are always saved in the `contact_messages` collection
(Atlas → **Browse Collections**). To also get each one by email, set up the email variables above and add
`CONTACT_NOTIFY_EMAIL=you@example.com`.

**Investor documents.** The pitch deck, cap table and one-pager are not shipped in the image. To publish them,
delete the three `frontend/public/docs/…` lines at the bottom of [`.dockerignore`](../.dockerignore) and set
`SERVE_INVESTOR_DOCS=true`.

## Before real customers

- **Backups.** The Atlas free cluster has none. Move to Atlas **Flex** (about $8 a month, daily snapshots) once
  real data matters.
- **One instance only.** Rate limits and the email worker live inside the process. Do not scale out.
- **Keep the secrets.** `JWT_SECRET` (changing it signs everyone out) and `API_KEY_PEPPER` (changing it stops every
  agent key) must stay the same for the life of the database.
- **Free-cluster limit.** 512 MB. The audit history only grows, so watch the cluster's size.

## Other hosts

The Dockerfile runs anywhere that runs a container and sets `PORT`.

Whichever host you pick, set `MONGO_URL`, `ANTHROPIC_API_KEY`, `JWT_SECRET` and `API_KEY_PEPPER` (only Render
generates the last two for you; make them with `python3 backend/scripts/gen_secrets.py` and keep a copy). `DB_NAME`
defaults to `vexen`.

- **Railway:** New Project → Deploy from GitHub → add those variables → Settings → Generate Domain.
  [`railway.json`](../railway.json) sets the health check. About $5 a month. Make sure there is one replica.
- **Anywhere else:** `docker build -t vexen .`, then `docker run -p 8000:10000 --env-file backend/.env vexen` with those
  variables, and `PUBLIC_APP_URL` set to your site's address. The image refuses to start without it (Render and
  Railway supply an address themselves), so a link in an email can never be built from a request.

## Troubleshooting

| You see | It means |
| --- | --- |
| Deploy log: `Setup problem: MONGO_URL …` | The database address is missing or still has `<db_password>` in it. |
| Deploy log: `the database did not answer` | Wrong password, or Atlas Network Access does not allow Render yet (step 1.4). |
| Deploy log: `JWT_SECRET must be at least 32 characters` | Run `python backend/scripts/gen_secrets.py` and set the value. |
| `/api/ready` → `"ai":"missing_key"` | `ANTHROPIC_API_KEY` is not set. The rest of Vexen works. |
| `/api/ready` → `"ai":"not_an_anthropic_key"` | The value is not an Anthropic API key (it must start with `sk-ant-`). |
| `/api/ready` returns 503 with `"database":"unreachable"` | The server is up but cannot reach MongoDB: check the password, and that Atlas Network Access still lists Render (re-add `0.0.0.0/0` to undo step 5), and that the cluster is not paused. |
| `/api/ready` → `"ai":"rejected"` | Anthropic refused the key: it was revoked, expired, mistyped or disabled. Replace it and redeploy. |
| `/api/ready` → `"ai":"unverified"` | The startup check could not settle it: Anthropic was unreachable, or the key needs `ANTHROPIC_WORKSPACE_ID`. If AI requests fail, the server log says why (lines starting `Policy generator error` or `Assistant error`): no credit left, a spend limit reached, a missing workspace. |
| `/api/ready` → `"ai":"model_unavailable"` | Anthropic answered "not found": either `ANTHROPIC_WORKSPACE_ID` is wrong or not usable by this key, or the key's workspace cannot use `claude-opus-5-5`. Check both in the Console. |
| Emails link to the wrong address | Set `PUBLIC_APP_URL` to your site's address. |
| Deploy log: `PUBLIC_APP_URL is not set` | Only outside Render and Railway: set `PUBLIC_APP_URL=https://your.domain`. |
| `413` "That request is too large" | A request body over 256 KB is refused to protect the small server. Raise it with `MAX_REQUEST_BYTES` if you really need to. |
