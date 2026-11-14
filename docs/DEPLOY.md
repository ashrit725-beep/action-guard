# Deploying Vexen

Vexen deploys to **Vercel** as one project: Vercel's CDN serves the website, and the API runs as one Vercel
Function (Python) at the same address. [`vercel.json`](../vercel.json) holds the whole setup, so there is
almost nothing to choose. You need three things, and the setup takes about 20 minutes.

| You need | Where | Cost |
| --- | --- | --- |
| A database | MongoDB Atlas | Free (512 MB) |
| An AI key | Anthropic Console | Pay as you go, a few cents per AI request |
| A host | Vercel | Hobby is free but for personal, non-commercial use only; Pro is $20 a month |

When you are done you have a public `https://<project>.vercel.app` address with the website, sign-up, the
dashboard and the API that agents call. The always-on container (Render, Railway, any Docker host) still works
exactly as before: see [Other hosts](#other-hosts-an-always-on-container) at the end.

## Which Vercel plan

- **Hobby (free)**: Vercel's terms allow it for personal or non-commercial use only. A Hobby account that uses
  more than its included amount is paused, usually for 30 days. Fine for trying Vexen out.
- **Pro ($20 a month)**: needed as soon as Vexen serves a business or its customers. The price covers one member
  who deploys and includes $20 of usage each month; usage beyond that is billed, and a spending alert is on by
  default at $200.
- **Your code and AI training.** On Hobby, and during a Pro trial, Vercel's terms (section 3, "Your Content")
  let Vercel use what you deploy to train AI models. Before the first deploy, open your team's **Settings** and
  switch that off if you do not want it. On a paid Pro plan it is off unless you switch it on.
- What differs for Vexen: the scheduled email run can happen at most **once a day on Hobby**, and as often as
  every minute on Pro (see [Email](#6-email-alerts)). The function's time limit is 300 seconds on both, which
  is what `vercel.json` asks for (the slowest AI request takes up to about 90 seconds). Hobby allows 300 seconds
  only with Fluid compute, so `vercel.json` also switches that on (`"fluid": true`), whatever the project's
  dashboard setting. Function logs are kept for 1 hour on Hobby and 1 day on Pro.

---

## 1. The database: MongoDB Atlas (free)

1. Sign up at <https://www.mongodb.com/cloud/atlas/register> (no card needed).
2. **Create** a cluster, pick the **Free** option, provider **AWS**, region **Oregon (us-west-2)**, and press
   **Create**. That is next to Vercel's Portland region (`pdx1`), where `vercel.json` runs the API. (If your
   cluster is somewhere else, change `"regions"` in `vercel.json` to the nearest
   [Vercel region](https://vercel.com/docs/regions).)
3. Create a database user (the setup wizard offers it, or in the sidebar **Security → Database & Network Access
   → Database Users → Add New Database User**): password authentication, **Autogenerate Secure Password** (letters
   and numbers only) and **Copy** it, role **Read and write to any database**. Leave **Temporary User** and
   **Restrict Access** switched off, then **Add User**. Keep the password; you need it in a minute.
4. **Security → Database & Network Access → IP Access List → Add IP Address**, enter `0.0.0.0/0` (access from
   anywhere; "Add Current IP Address" is not enough) and **Confirm**. Keep it that way: Vercel Functions have no
   fixed outgoing addresses, so Atlas cannot be narrowed down to Vercel (fixed addresses are a paid Pro add-on,
   Static IPs, about $100 a month). The database user's long password is what protects it.
5. **Database → Clusters → Connect → Drivers**, copy the connection string. It looks like
   `mongodb+srv://USER:<db_password>@cluster0.abcde.mongodb.net/`.
   Replace `<db_password>` **including the angle brackets** with your password. That is your **`MONGO_URL`**.

## 2. The AI key: Anthropic

1. Open <https://platform.claude.com> (the Anthropic Console). Optional but tidy: create a workspace called
   "Vexen" under **Settings → Workspaces** (its ID, `wrkspc_…`, is in the ID column), so Vexen's usage and limits
   stay separate. Then **API keys → Create key**, inside that workspace, with the expiration set to **Never**
   (an expired key shows up as "rejected"). Copy the key (it starts with `sk-ant-`) and add some credit under
   **Billing**. That is your **`ANTHROPIC_API_KEY`**. If your key is not tied to a single workspace, also set
   **`ANTHROPIC_WORKSPACE_ID`** to the workspace's ID, or every AI request is refused.
2. **Set a monthly spend limit** (Console → **Settings → Spend limits**). Anyone can sign up on a public Vexen,
   so this is your safety net. The server adds its own limits: 20 rule drafts and 40 helper questions per person
   per 5 minutes, at most 8 AI requests at once, and a ceiling of **500 AI requests per 24 hours**
   (`AI_DAILY_CALL_LIMIT`; each typically costs a few cents; `0` turns it off). Those counts live in the memory of
   each running copy of the server, and on Vercel there can be several copies that come and go (see
   [What is different on Vercel](#7-what-is-different-on-vercel)), so treat them as a brake. The Console spend
   limit is the hard stop.

This is the only AI key Vexen has. A key from another provider is refused with a message saying so, and Vexen
only ever talks to `api.anthropic.com`.

## 3. The secrets

On your computer, in this repository, run:

```bash
python3 backend/scripts/gen_secrets.py
```

It prints fresh values and writes nothing. You need **`JWT_SECRET`**, **`API_KEY_PEPPER`** and **`CRON_SECRET`**.
Keep a copy somewhere safe: `JWT_SECRET` (changing it signs everyone out) and `API_KEY_PEPPER` (changing it stops
every agent key) must stay the same for the life of the database. (The phone-notification keys it prints only
appear when the packages in `backend/requirements.txt` are installed; you can add them later.)

## 4. The host: Vercel

1. Sign in at <https://vercel.com> with your GitHub account.
2. Open <https://vercel.com/new> (on the dashboard: **Add New… → Project**). Under **Import Git Repository**,
   pick your GitHub account and press **Import** next to **`action-guard`**. If it is not in the list, use the
   link below the list to let Vercel's GitHub app see the repository, then come back.
3. On the configuration screen:
   - **Project Name**: anything, for example `vexen` (your address becomes `https://vexen.vercel.app` if that
     name is free).
   - **Framework Preset**: leave it at **Other**. **Root Directory**: leave it at `./`, the top of the
     repository (not `frontend` or `backend`).
   - **Build and Output Settings**: leave them alone. `vercel.json` sets them: install with
     `yarn install --frozen-lockfile` in `frontend/`, build with `sh frontend/vercel-build.sh`, publish
     `frontend/build`.
   - **Environment Variables**: add these (you can paste them all at once into the first **Key** field as
     `NAME=value` lines):

     | Name | Value |
     | --- | --- |
     | `MONGO_URL` | the connection string from step 1 |
     | `DB_NAME` | `vexen` |
     | `JWT_SECRET` | from step 3 |
     | `API_KEY_PEPPER` | from step 3 |
     | `ANTHROPIC_API_KEY` | from step 2 |
     | `CRON_SECRET` | from step 3 |

     Do **not** add `REACT_APP_BACKEND_URL`: the website must call `/api` on its own address.
4. Press **Deploy**. The first build takes about 3 to 5 minutes. From then on, every push to `main` deploys to
   production, and every other branch or pull request gets its own preview deployment.
5. Settings to check once (Project → **Settings**):
   - **Environment Variables**: keep **Enable access to System Environment Variables** switched on (it is by
     default). Vexen reads its own production address from them.
   - Optional: **Build and Deployment → Node.js Version: 22.x**, the version the Docker image and CI use. The
     website also builds on Vercel's newer default, so this only keeps every build on the same version. A
     change applies from the next deployment.
   - On Hobby, the AI-training choice in your **team's** Settings: see [Which Vercel plan](#which-vercel-plan).

`vercel.json` already sets the rest: the API function's region (Portland, `pdx1`), Fluid compute and time limit
(300 seconds), the security headers, caching, the routing of `/api/...` to the function and every page address to
the website, and the daily email run.

## 5. Check that it works

Open your address, `https://<project>.vercel.app`.

- `/api/health` shows `"status":"ok"`. If you get Vercel's own 404 page instead, the API function was not built:
  open the deployment's **Build Logs** and look for `api/index.py`.
- `/api/ready` shows `"database":"ok"` and `"ai":"ready"`. A fresh copy of the API checks the AI key in the
  background, so its very first answer can say `"ai":"unverified"`: reload after a few seconds. If it answers
  **"Vexen is not set up correctly"**, the
  rest of the message says which variable to fix; if it says **"the database did not answer"**, check the
  password and Atlas Network Access (step 1.4). After changing a variable, redeploy (**Deployments → ⋯ →
  Redeploy**): a running deployment keeps the values it started with.
- Sign up, open **Rules**, and write a rule in plain English. That is the Anthropic-backed rule writer.
- The **Ask for help** button is visible in the app. It is hidden when the AI key is not working.
- **Schedules → Cron Jobs** (in the project's sidebar) lists `/api/internal/outbox` (only production
  deployments have it).

For a closer look, these mirror the checks CI runs against the container:

```bash
site=https://<project>.vercel.app
curl -s -o /dev/null -w '%{http_code}\n' $site/approve/abc.def          # 200, the app
curl -s -o /dev/null -w '%{http_code}\n' $site/api/does-not-exist        # 404 (JSON)
curl -s -o /dev/null -w '%{http_code}\n' $site/static/js/missing.js      # 404
curl -s -o /dev/null -w '%{http_code}\n' $site/docs/vexen-cap-table.pdf  # 404 (investor material)
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' $site/api/download/demo-video  # 307 to the file
curl -s -o /dev/null -w '%{http_code}\n' $site/api/internal/outbox       # 401 without the secret
```

## 6. Email alerts

Add `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` and `SMTP_FROM_EMAIL`, then redeploy. For Gmail
use `smtp.gmail.com`, port `587`, and an App Password. Use port 587 or 465.

There is no always-running email worker on Vercel (a function only runs while it answers a request). Instead:

- A request that queues an email (an approval alert, an invitation) sends it **right after its response has
  gone out**, so an agent waiting for a decision never waits for the mail server.
- Any request also checks the queue at most once a minute, which picks up retries after a failed send.
- **Once a day** Vercel calls `/api/internal/outbox` with your `CRON_SECRET` and everything still waiting is
  sent. Without `CRON_SECRET` that address does not exist. On **Pro** you can make it frequent: in
  `vercel.json` change `"schedule": "0 9 * * *"` to `"*/5 * * * *"` (every 5 minutes). On Hobby a schedule that
  runs more than once a day makes the deployment fail.

## 7. What is different on Vercel

Vexen behaves the same, but a serverless host changes a few guarantees. Read this before real customers.

- **Limits are per copy.** Vercel runs as many copies (instances) of the API as traffic needs, and stops them
  when it is quiet. Each copy keeps its own rate-limit counters and its own count toward the 500-a-day AI
  ceiling, and a new copy starts from zero. So the sign-in limits and the AI ceiling are softer than in the
  container. The Anthropic Console spend limit (step 2.2) is what really caps the cost.
- **Email timing.** Mail goes out right after the request that queued it. A failed send is retried by a later
  request or the daily run, so on a quiet Hobby site a retry can wait until the next day.
- **Cold starts.** The first request to a fresh copy waits for the database connection and the index check
  (usually a second or two). Vercel keeps production deployments warm.
- **Logs show full addresses.** Vercel's request logs include signed approval and invitation links. Approval
  links expire after 24 hours and invitation links after 7 days, but keep the people with access to the Vercel
  project to those you trust.
- **Downloads** (`/api/download/...`) send the browser to the file on Vercel's CDN; a function's answer is
  capped at 4.5 MB and the demo video is 18 MB.
- **Previews** get their own address behind a Vercel login (Deployment Protection), and links in emails from a
  preview point at that preview. Give previews their own database so tests never touch real data: **Settings →
  Environment Variables → `DB_NAME`**, set it to `vexen` for **Production** and to `vexen_preview` for
  **Preview**. The daily email run happens on production only.

## 8. Tighten and extend (all optional)

**Your own domain.** **Settings → Domains → Add**, and create the DNS records it shows. Then redeploy once: links
in emails use your domain from then on (Vercel tells Vexen its shortest production domain). Set
**`PUBLIC_APP_URL=https://your.domain`**, for **Production** only, just to pick a different one of your domains
(set for Preview too, it would send links in preview emails to production).

**Phone notifications.** On your computer run
`cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python scripts/gen_secrets.py`,
then add the `VAPID_PUBLIC_KEY` and `VAPID_PRIVATE_KEY` it prints, and set `VAPID_SUBJECT` to `mailto:` plus your
real address.

**Contact form.** Messages from the website's contact page are always saved in the `contact_messages` collection
(Atlas → **Browse Collections**). To also get each one by email, set up email and add
`CONTACT_NOTIFY_EMAIL=you@example.com`.

**Investor documents.** The pitch deck, cap table and one-pager are left out of the website: the build deletes
them (`frontend/vercel-build.sh`) and `.vercelignore` keeps them from being uploaded. To publish them, delete the
three `frontend/public/docs/…` lines at the bottom of [`.vercelignore`](../.vercelignore), set
`SERVE_INVESTOR_DOCS=true`, and redeploy.

**Add or change a variable later:** **Settings → Environment Variables**, then redeploy.

## Before real customers

- **Plan.** Use Pro: Hobby is for personal, non-commercial use only.
- **Backups.** The Atlas free cluster has none. Move to Atlas **Flex** (about $8 a month, daily snapshots) once
  real data matters.
- **Keep the secrets.** `JWT_SECRET` and `API_KEY_PEPPER` must stay the same for the life of the database.
- **Free-cluster limits.** 512 MB of data (the audit history only grows, so watch the cluster's size), 100
  database operations per second (Atlas slows the cluster down above that; each fresh copy of the API runs about
  37 index checks when it starts), 10 GB in and 10 GB out per 7 days, and at most 500 connections (on Vercel
  each copy of the API keeps at most 10, plus a few for monitoring). Atlas **Flex** lifts most of these.

---

## Other hosts: an always-on container

The same code also runs as **one container** that serves the website and the API together, with an email
worker that runs all the time. It is the better fit when you want fixed costs or one process that holds the
rate limits. Whichever host you pick, set `MONGO_URL`, `ANTHROPIC_API_KEY`, `JWT_SECRET` and `API_KEY_PEPPER`;
`DB_NAME` defaults to `vexen`. Run exactly **one** instance: the rate limits and the email worker live inside
the process. `CRON_SECRET` is not needed there.

- **Render** (about $7 a month, always on): sign in at <https://dashboard.render.com> with GitHub, then press
  **Deploy to Render** in the [README](../README.md), or **New → Blueprint** with this repository and an empty
  Blueprint path. Render reads [`render.yaml`](../render.yaml), asks for `MONGO_URL` and `ANTHROPIC_API_KEY`, and
  generates `JWT_SECRET` and `API_KEY_PEPPER` for you. The first build takes 5 to 8 minutes. Render's free plan
  sleeps after 15 minutes, pauses the email worker and blocks outgoing email ports, so it is only for trials.
  To restrict Atlas to Render: service → **Connect → Outbound**, add those ranges in Atlas Network Access and
  delete `0.0.0.0/0`. For your own domain: **Settings → Custom Domains**, then set `PUBLIC_APP_URL`.
- **Railway** (about $5 a month): New Project → Deploy from GitHub → add the variables → **Settings → Networking
  → Generate Domain**, then redeploy. The image needs an address to start and Railway only has one once a domain
  exists (or set `PUBLIC_APP_URL` yourself). [`railway.json`](../railway.json) sets the health check. Make sure
  there is one replica.
- **Anywhere else:** `docker build -t vexen .`, then `docker run -p 8000:10000 --env-file backend/.env vexen` with
  those variables, and `PUBLIC_APP_URL` set to your site's address. The image refuses to start without it, so a
  link in an email can never be built from a request.

## Troubleshooting

| You see | It means |
| --- | --- |
| `/api/...` answers 500: "Vexen is not set up correctly" (Vercel) | The message names the variable to fix. Fix it in Settings → Environment Variables, then redeploy. In the container the same problem stops the server, with the reason in the deploy log (`Setup problem: …`). |
| `MONGO_URL still has a <placeholder>` | Replace `<db_password>` (angle brackets included) with the database user's password. |
| `JWT_SECRET must be at least 32 characters` | Run `python3 backend/scripts/gen_secrets.py` and set the value. |
| `/api/...` answers 503: "the database did not answer", or `/api/ready` shows `"database":"unreachable"` | Wrong password, Atlas Network Access does not allow `0.0.0.0/0`, or the cluster is paused. |
| `/api/health` shows Vercel's 404 page | The API function is missing: check that Root Directory is `./` and that the build log built `api/index.py`. |
| Build log: `PYTHON_REQUIREMENTS_PARSE_ERROR` | `api/requirements.txt` contains something Vercel cannot read, such as a `-r` include. It must list the same pinned lines as `backend/requirements.txt`. |
| The deployment fails because of the cron schedule | On Hobby the schedule in `vercel.json` must run at most once a day. |
| Schedules → Cron Jobs is empty | Cron jobs exist on production deployments only. Deploy `main` once. If it is still empty, check the build log of that deployment for `vercel.json` errors. |
| Emails link to `*.vercel.app` after you added a domain | Redeploy once, or set `PUBLIC_APP_URL`. |
| Emails link to the wrong address | Set `PUBLIC_APP_URL` to your site's address. |
| `/api/ready` → `"ai":"missing_key"` | `ANTHROPIC_API_KEY` is not set. The rest of Vexen works. |
| `/api/ready` → `"ai":"not_an_anthropic_key"` | The value is not a regular Anthropic API key, which starts with `sk-ant-api`. Admin keys (`sk-ant-admin…`), sign-in tokens (`sk-ant-oat…`), keys from other providers and cut-off keys are refused. |
| `/api/ready` → `"ai":"rejected"` | Anthropic refused the key: it was revoked, expired, mistyped or disabled. Replace it and redeploy. |
| `/api/ready` → `"ai":"unverified"`, still after a reload a few seconds later | The start-up check could not settle it: Anthropic was unreachable, or the key needs `ANTHROPIC_WORKSPACE_ID`. If AI requests fail, the log says why (lines starting `Policy generator error` or `Assistant error`): no credit left, a spend limit reached, a missing workspace. |
| `/api/ready` → `"ai":"model_unavailable"` | Anthropic answered "not found": either `ANTHROPIC_WORKSPACE_ID` is wrong or not usable by this key, or the key's workspace cannot use `claude-opus-5-5`. Check both in the Console. |
| `PUBLIC_APP_URL is not set` | Vercel and Render supply the address themselves (on Vercel, keep system environment variables switched on). On Railway no domain exists yet: Generate Domain, then redeploy. Elsewhere set `PUBLIC_APP_URL=https://your.domain`. |
| `413` "That request is too large" | A request body over 256 KB is refused to protect the server. Raise it with `MAX_REQUEST_BYTES` if you really need to (Vercel itself stops at 4.5 MB). |
