# Task Manager

A full-stack Django app for project & task management with
role-based access, file submissions, project chat, and direct
messaging. One Django server serves both the REST API and the web UI
at the same URL — nothing else to run, deploy, or configure
separately. Built to run on Railway.

## Features

- **Web UI**: a single-page frontend (`templates/index.html`) served
  directly by Django at `/` — sign up, log in, create projects, add
  members, create/assign/update tasks, upload deliverables, chat,
  and view the dashboard, all by clicking around, no API client needed
- **Auth**: signup/login/refresh via JWT (`djangorestframework-simplejwt`)
- **Roles**: only admins can create projects (the creator automatically
  becomes that project's admin); admins assign members and tasks.
  Regular members can only update the status/priority of tasks
  assigned to them and cannot create/delete tasks or manage membership.
  **Nobody can self-register as admin by simply picking it** — see
  "Controlling who can become an admin" below.
- **Deliverable submissions**: each project member can upload a file
  (up to 1GB), a GitHub/repo link, an optional live demo link, and a
  description for the project they're on. Re-submitting updates their
  existing submission rather than creating a new one. Project admins
  and teammates can see everyone's submission
- **Project chat**: a group chat per project, open to every admin and
  member of that project (polls every 4s for new messages)
- **Direct messages**: any user can message any other user in the
  system directly, regardless of whether they share a project, with
  a conversation list and unread counts
- **Tasks**: create, assign, update status/priority, due dates,
  automatic overdue detection
- **Dashboard**: per-user and per-project task counts by status,
  overdue tasks, upcoming tasks
- **Kanban board**: toggle any project's Tasks tab between a list
  view and a drag-and-drop board (To Do / In Progress / Done)
- **Notifications**: a bell in the top bar shows real notifications
  (you were assigned a task) plus live-computed "due soon" reminders
  (assigned tasks due within 24h) — no cron/background job needed
- **Unread badges**: the Messages nav item shows your unread DM count
- **Account & passwords**: change your password from the app, or
  reset a forgotten one via an emailed link (prints to the server
  console by default in dev — see below for real SMTP)
- SQLite locally, Postgres in production (auto-detected via `DATABASE_URL`)

## Tech stack

Django 5.2 - Django REST Framework - SimpleJWT - django-filter -
WhiteNoise (static files) - Gunicorn - dj-database-url

---

## Local setup

```bash
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                # edit if needed
python manage.py migrate
python manage.py createsuperuser    # optional, for /admin/
python manage.py seed_demo          # optional: creates demo admin/member/project/tasks
python manage.py runserver
```

Open **http://127.0.0.1:8000/** in your browser — that's the app.
Sign up, or log in with a demo account if you ran `seed_demo`. The
raw API lives under `/api/...` (see reference below) and `/admin/`
is the Django admin.

Demo accounts created by `seed_demo` (username / password):
- `admin_demo` / `DemoPass123!` (project admin)
- `member_demo` / `DemoPass123!` (project member)

---

## API reference

All endpoints are under `/api/`. Authenticated requests need:
`Authorization: Bearer <access_token>`.

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/signup/` | Register (`username`, `email`, `password`, `password2`, optional `role`) |
| POST | `/api/auth/login/` | Get `access` + `refresh` JWT tokens |
| POST | `/api/auth/login/refresh/` | Refresh an access token |
| GET/PATCH | `/api/auth/me/` | Current user's profile |
| GET | `/api/auth/users/` | List all users (for assigning tasks/members/DMs) |

### Projects
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/projects/` | List projects you're a member of |
| POST | `/api/projects/` | Create a project — **admins only** (you become its admin) |
| GET | `/api/projects/{id}/` | Project detail incl. member list |
| PATCH/DELETE | `/api/projects/{id}/` | Edit/delete (project admins only) |
| GET | `/api/projects/{id}/members/` | List members |
| POST | `/api/projects/{id}/members/` | Add a member (`user_id`, `role`) -- admins only |
| PATCH | `/api/projects/{id}/members/{user_id}/` | Change a member's role -- admins only |
| DELETE | `/api/projects/{id}/members/{user_id}/` | Remove a member -- admins only |

### Tasks
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/tasks/` | List tasks (filters: `?project=`, `?status=`, `?assigned_to=`, `?mine=true`, `?overdue=true`) |
| POST | `/api/tasks/` | Create a task -- project admins only |
| GET | `/api/tasks/{id}/` | Task detail |
| PATCH | `/api/tasks/{id}/` | Update -- admins can edit everything; members can only change `status`/`priority` on tasks assigned to them |
| DELETE | `/api/tasks/{id}/` | Delete -- project admins only |

### Submissions (deliverables)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/submissions/?project={id}` | List submissions for a project (admins see everyone's; members see their own) |
| POST | `/api/submissions/` (multipart) | Create/update **your own** submission -- fields: `project`, `file` (≤1GB, optional), `repo_link`, `live_link`, `description` |
| PATCH | `/api/submissions/{id}/` | Update your own submission |
| DELETE | `/api/submissions/{id}/` | Delete -- owner or project admin only |

### Chat
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/chat/project-messages/?project={id}` | Full message history for a project (members/admins only) |
| POST | `/api/chat/project-messages/` | Post a message -- body: `{"project": id, "content": "..."}` |
| GET | `/api/chat/direct-messages/?with={user_id}` | Full DM thread with that user (marks their messages read) |
| POST | `/api/chat/direct-messages/` | Send a DM -- body: `{"recipient_id": id, "content": "..."}` |
| GET | `/api/chat/conversations/` | Everyone you've DM'd, with last message + unread count |

### Notifications
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/notifications/` | Real notifications + live "due soon" reminders, newest first |
| GET | `/api/notifications/unread-count/` | `{unread_notifications, due_soon}` counts for badges |
| POST | `/api/notifications/{id}/read/` | Mark one real notification as read |
| POST | `/api/notifications/read-all/` | Mark all your real notifications as read |

### Account
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/password/change/` | Change your password while logged in -- body: `current_password`, `new_password`, `new_password2` |
| POST | `/api/auth/password/reset/` | Request a reset link by email -- body: `email` (always returns a generic success message) |
| POST | `/api/auth/password/reset/confirm/` | Set a new password -- body: `uid`, `token`, `new_password`, `new_password2` |

### Dashboard
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/dashboard/` | Task counts by status, overdue/upcoming tasks, per-project breakdown |

---

## Deploying to Railway

### Option A -- Railway CLI

```bash
npm i -g @railway/cli
railway login
cd taskmanager
railway init
railway add           # choose "Database" -> "PostgreSQL" to provision Postgres
railway up
```

### Option B -- Railway dashboard (GitHub)

1. Push this project to a GitHub repo.
2. On railway.app: **New Project -> Deploy from GitHub repo**, pick the repo.
3. **New -> Database -> PostgreSQL** in the same project. Railway
   automatically injects `DATABASE_URL` into your app service.
4. On your app service, open **Variables** and add:
   - `SECRET_KEY` -- a long random string (e.g. `python -c "import secrets; print(secrets.token_urlsafe(50))"`)
   - `DEBUG` -- `False`
   - `ALLOWED_HOSTS` -- leave unset (the app auto-adds Railway's public domain), or set explicitly, e.g. `your-app.up.railway.app`
5. Railway detects Python via Nixpacks and uses the included
   `Procfile` / `railway.json`, which:
   - runs `python manage.py migrate` before each deploy
   - runs `collectstatic`
   - starts `gunicorn taskmanager.wsgi`
6. Once deployed, open **Settings -> Networking -> Generate Domain**
   to get a public URL.
7. Create an admin user on the live app:
   ```bash
   railway run python manage.py createsuperuser
   ```
   (or run `railway run python manage.py seed_demo` for demo data).

### A note on uploaded files in production

Submission files are stored on local disk (`MEDIA_ROOT`) and served
directly by Django, which works fine for demoing/grading this app.
**Railway's filesystem is ephemeral** -- files will be lost on
redeploy or restart. For durable production storage, swap in a
service like AWS S3 or Cloudflare R2 (e.g. via `django-storages`) and
point `MEDIA_URL`/`STORAGES["default"]` at it instead.

### Verifying the live deployment

```bash
curl https://<your-app>.up.railway.app/health/
# {"status": "healthy"}
```

Then exercise the API the same way as locally, replacing
`http://127.0.0.1:8000` with your Railway URL, or just open the URL
in a browser to use the web UI directly.

---

## Project layout

```
taskmanager/
├── accounts/       # custom User model (role: admin/member), auth endpoints
├── projects/       # Project + ProjectMembership (per-project roles), permissions
├── tasks/          # Task model, RBAC-aware viewset, dashboard view
├── submissions/    # per-member project deliverables (file/links/description)
├── chat/           # project group chat + any-to-any direct messages
├── templates/
│   └── index.html  # the frontend — served by Django at "/"
├── taskmanager/    # settings, root urls, wsgi/asgi
├── requirements.txt
├── Procfile        # release (migrate) + web (gunicorn) processes
├── railway.json    # Railway build/deploy config
├── nixpacks.toml   # ensures collectstatic runs at build time
└── runtime.txt
```

## Controlling who can become an admin

The signup form does **not** let people choose "Admin" for themselves.
Every plain signup creates a `member` account. There are three ways
to get an admin account, all of which require you (the operator) to
act:

1. **Invite code (optional).** Set `ADMIN_SIGNUP_CODE` in your `.env`
   (locally) or as a Railway service variable (in production) to some
   secret string. Anyone who enters that exact code in the signup
   form's "Admin invite code" field becomes an admin; anyone who
   leaves it blank or gets it wrong becomes a regular member. Leave
   this variable unset/blank to disable self-service admin signup
   entirely.
2. **CLI promotion.** `python manage.py promote_admin <username>`
   flips an existing user to admin (`--demote` flips them back).
3. **Django admin panel.** Log into `/admin/` as a superuser
   (`python manage.py createsuperuser`) and edit the user's `role`
   field directly.

## Notes on the RBAC design

- Only users with the **global** `role` of `admin` can create
  projects; the creator is automatically added as that project's
  admin via `ProjectMembership`.
- **`ProjectMembership.role`** is scoped per project: the same
  person can be an admin on one project and a plain member on
  another.
- Project admins manage membership, tasks, and can see every
  member's submission; members can view everything in their
  projects, submit/update their own deliverable, chat, and update
  the status/priority of tasks assigned to them -- nothing else.
- Direct messaging is completely separate from project membership --
  any two users in the system can message each other.
