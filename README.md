# Conduit with Docker Compose

This repository containerizes the Conduit application, a Medium-like blogging platform. It consists of an Angular 17 frontend served by nginx, a Django 1.10.5 REST backend served by gunicorn, and a PostgreSQL 16 database. Docker Compose builds and runs all three services, keeps database data in a named volume, restarts the containers after an unexpected exit, and publishes only port `8282` to the outside world.

## Table of contents

- [Prerequisites](#prerequisites)
- [Quickstart](#quickstart)
- [Project structure](#project-structure)
- [Usage](#usage)
  - [Configuration](#configuration)
  - [Images and startup](#images-and-startup)
  - [Run and manage Conduit](#run-and-manage-conduit)
  - [Logs](#logs)
  - [Persistence and restarts](#persistence-and-restarts)
  - [Testing](#testing)
  - [Deployment](#deployment)
  - [Backend development](#backend-development)
- [Extras for the reviewers](#extras-for-the-reviewers)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Docker with the Compose plugin (Docker Desktop works for local testing).
- Git.
- An available TCP port `8282` on the host.
- For deployment, a cloud VM with Docker and access to port `8282` through its firewall and network rules.

## Quickstart

All commands use Bash (on Windows: Git Bash or WSL) and run from the repository root.

1. Clone the repository and change into it:

   ```bash
   git clone https://github.com/FriggemannMichael/Conduit.git
   cd Conduit
   ```

2. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

3. Open `.env` and replace the placeholders for `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD` with long random values. You can generate them with:

   ```bash
   openssl rand -hex 32
   ```

   If you open the application through an IP address or domain other than `localhost`, add it to `DJANGO_ALLOWED_HOSTS`, for example `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,<your_ip>`.


4. Validate the Compose configuration, then build and start the services:

   ```bash
   docker compose config --quiet
   docker compose up -d --build --wait
   docker compose ps
   ```

5. Open `http://<your_ip>:8282` (locally: `http://localhost:8282`), register a user, and create an article.

> [!CAUTION]
> `.env` contains the Django secret key and the database password and is ignored by Git. Never commit it, never put real values into `.env.example`, and never share them in an issue or log.

The first start builds both images (the Angular build takes a few minutes) and initializes the database volume. Subsequent starts are much faster.

## Project structure

| Path                                  | Purpose                                                                                                         |
|---------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| `docker-compose.yaml`                 | Defines the `frontend`, `backend`, and `db` services, environment, port, named volumes, healthcheck, and restart policies. |
| `.env.example`                        | Lists all variables with placeholders. Copy it to `.env` before starting Compose.                               |
| `frontend/`                           | Angular 17 application source.                                                                                  |
| `frontend/Dockerfile`                 | Multi-stage build: `node:20-alpine` builds the app, `nginx:1.27-alpine` serves it.                               |
| `frontend/nginx.conf`                 | Serves the Angular app and proxies `/api/` and `/admin/` to the backend; serves Django static files at `/static/`. |
| `backend/`                            | Django 1.10.5 REST API source.                                                                                  |
| `backend/Dockerfile`                  | Multi-stage build on `python:3.6-slim`; runs gunicorn as a non-root user.                                        |
| `backend/entrypoint.sh`               | Waits for the database, runs migrations and `collectstatic`, then starts gunicorn.                               |
| `backend/Dockerfile.dev`              | Development image for running tests (see [Backend development](#backend-development)).                          |
| `frontend/.dockerignore`, `backend/.dockerignore` | Keep dependencies, build output, secrets, and Git data out of the build context.                    |
| `.gitignore`                          | Excludes `.env`, Python and Node artifacts, IDE files, and exported logs from Git.                              |
| `.github/workflows/`                  | CI, quality, and deployment workflows (see [Extras](#extras-for-the-reviewers)).                                |
| `docs/Conduit Container Checkliste.pdf` | Project submission requirements and verification checklist.                                                   |
| `README.md`                           | Setup, operation, configuration, testing, and deployment instructions.                                          |

The local `.env` file is not tracked. Docker manages the `postgres_data` and `staticfiles` volumes outside the repository.

## Usage

### Configuration

Compose reads these variables from `.env` in the repository root:

| Variable               | Default in Compose     | Effect                                                                                       |
|------------------------|------------------------|----------------------------------------------------------------------------------------------|
| `DJANGO_SECRET_KEY`    | none, **required**     | Django secret key used to sign sessions and tokens. Compose refuses to start without it.     |
| `DJANGO_DEBUG`         | `False`                | Enables Django debug pages when set to `True`. Keep `False` on a public VM.                  |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1`  | Comma-separated host names or IPs that Django accepts. Add `<VM_IP>` or your domain on a VM. |
| `POSTGRES_DB`          | `conduit`              | Database name, used by the `db` service and the backend.                                     |
| `POSTGRES_USER`        | `conduit`              | Database user, used by the `db` service and the backend.                                     |
| `POSTGRES_PASSWORD`    | none, **required**     | Database password, used by the `db` service and the backend.                                 |
| `POSTGRES_HOST`        | `db`                   | Host name of the database. `db` is the Compose service name.                                 |
| `POSTGRES_PORT`        | `5432`                 | Port of the database inside the Compose network.                                             |
| `CONDUIT_PORT`         | `8282`                 | Host port published by the `frontend` service.                                               |
| `DJANGO_SUPERUSER_USERNAME` | `admin`           | User name of the optional superuser created on backend start.                                |
| `DJANGO_SUPERUSER_EMAIL`    | empty              | Email of the optional superuser. No superuser is created while it is empty.                  |
| `DJANGO_SUPERUSER_PASSWORD` | empty              | Password of the optional superuser. No superuser is created while it is empty.               |

Only the `frontend` service publishes a port. To use another host port, set `CONDUIT_PORT` in `.env`, then use that port in the browser and in the VM firewall rules. The backend (`8000`) and the database (`5432`) are only reachable inside the Compose network.

Postgres reads `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` only when the `postgres_data` volume is empty. Changing them later does not modify the existing database; set them **before the first start**.

If `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD` are set, the backend entrypoint creates a superuser after the migrations, so you can log in at `http://<your_ip>:8282/admin/`. It is created only if no user with that email exists yet; changing the password in `.env` later does not update an existing superuser.

### Images and startup

Both Dockerfiles use multi-stage builds to keep the final images small:

- **Frontend:** `node:20-alpine` installs the dependencies with `npm ci` and builds the Angular app. Only the build output is copied into `nginx:1.27-alpine`, which listens on port `80`.
- **Backend:** a builder stage installs the Python dependencies into a virtual environment with `uv`. The runtime stage copies only that environment and the application code, runs as the non-root user `appuser`, and exposes port `8000` (`APP_PORT`).

nginx is the single entry point. It serves the Angular app, forwards `/api/` and `/admin/` to `backend:8000` with the original `Host` header (so `DJANGO_ALLOWED_HOSTS` works), and serves the Django static files from the shared `staticfiles` volume at `/static/`. The frontend therefore calls the API with the relative path `/api`, and no backend URL has to be configured.

On every start the backend entrypoint:

1. waits until the database accepts connections (up to 30 attempts),
2. runs `python manage.py migrate`,
3. runs `python manage.py collectstatic`,
4. starts the WSGI server **gunicorn** (not the Django development server).

Compose starts the services in order: `db` first, `backend` once the database healthcheck (`pg_isready`) reports healthy, then `frontend`.

### Run and manage Conduit

Run each command separately from the repository root:

```bash
docker compose up -d --build --wait
docker compose ps
docker compose logs -f backend
docker compose restart
docker compose down
```

Press `Ctrl+C` to stop following a log; the containers continue running. `docker compose down` removes the containers and the network but keeps the named volumes. Start them again with `docker compose up -d`. After changing source code, add `--build` so Compose rebuilds the images.

### Logs

Show the logs of all services or of a single one:

```bash
docker compose logs
docker compose logs -f backend
```

Save the logs to a file for later use:

```bash
mkdir -p logs
docker compose logs --no-color backend > logs/backend.txt
docker compose logs --no-color frontend > logs/frontend.txt
docker compose logs --no-color db > logs/db.txt
```

The `logs/` folder is ignored by Git.

> [!TIP]
> gunicorn writes its logs to **stderr**. `docker logs <container> > file.txt` only redirects stdout, so the file stays almost empty. Use `docker compose logs` as shown above, or add `2>&1`: `docker logs <container> > file.txt 2>&1`. The container names are shown by `docker compose ps`.

### Persistence and restarts

The `postgres_data` volume stores the database at `/var/lib/postgresql/data`. The `staticfiles` volume is filled by the backend's `collectstatic` and mounted read-only into the frontend, where nginx serves it.

All services use `restart: unless-stopped`, so Docker restarts them after their main process exits while Docker is running. A deliberately stopped container stays stopped until you start it again. The database gets a `stop_grace_period` of two minutes to shut down cleanly.

To verify persistence, create an article, run `docker compose down` followed by `docker compose up -d`, then confirm that you can still sign in and find the article.

> [!CAUTION]
> Do not add `-v` to `docker compose down` when you need to keep the data. `down -v` removes the named volumes and deletes the database. Back up the `postgres_data` volume before any destructive change.

### Testing

Check the Compose structure and the running services:

```bash
docker compose config --quiet
docker compose ps
docker compose top backend | grep gunicorn
curl -fsS -o /dev/null -w "%{http_code}\n" http://localhost:8282/
curl -fsS http://localhost:8282/api/tags
```

Open `http://<your_ip>:8282`, register a user, create and edit an article, add a comment, follow a profile, and change the profile picture in the settings. Test a saved article after recreating the containers as described above.

To test the automatic restart, end the main process inside a container and watch it come back with `docker compose ps`:

```bash
docker compose exec frontend kill 1
docker compose exec db kill 1
docker compose exec backend python -c "import os; os.kill(1, 15)"
```

The slim Python image has no `kill` command, so the backend uses Python instead. A manual `docker kill` or `docker compose stop` is not a valid test of `unless-stopped`, because Docker treats it as a manual stop.

### Deployment

The VM needs Docker with the Compose plugin and an inbound rule for TCP port `8282`. Create a **VM-local** `.env` once in the deployment folder (`~/conduit`), based on `.env.example`, with new random secrets and `<VM_IP>` in `DJANGO_ALLOWED_HOSTS`. This file is never overwritten by a deployment.

The workflow `.github/workflows/deployment.yaml` deploys automatically on every push to `main` and can also be started manually. It first runs the CI and quality workflows, then copies the repository to the VM over SSH, runs `docker compose up -d --build --wait` there, and checks that `/` and `/api/tags` answer on port `8282`. It uses the GitHub environment `production` with these secrets:

| Secret       | Content                                                              |
|--------------|----------------------------------------------------------------------|
| `VM_HOST`    | `<VM_IP>` or host name of the VM.                                    |
| `VM_USER`    | SSH user on the VM. The user must be a member of the `docker` group. |
| `VM_SSH_KEY` | Private key of a dedicated deploy key without a passphrase.          |

Visit `http://<VM_IP>:8282` and verify registration, navigation, persistence after a restart, and automatic container recovery. Local data is **not** transferred to the VM.

> [!CAUTION]
> Port `8282` serves plain HTTP. Keep real passwords, SSH keys, tokens, user names, IP addresses, and other sensitive VM details out of this repository. Store them in the VM-local `.env` or in GitHub secrets.

### Backend development

> [!CAUTION]
> The backend uses Django 1.10.5, which only runs on Python 3.6. Python 3.6 is
> end-of-life since December 2021, so it is not installed locally. Development
> runs in a dev container instead (`backend/Dockerfile.dev`, Python 3.6 + uv),
> which uses the same base image as the production image.

Build the dev image:

```bash
docker build -f backend/Dockerfile.dev -t conduit-backend-dev backend
```

Run the tests (the `pwd -W` part converts the path for Git Bash on Windows, Linux uses `pwd`):

```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W 2>/dev/null || pwd)/backend:/app" conduit-backend-dev
```

Run the linter:

```bash
uvx ruff check --no-cache backend
```

The 33 pytest warnings are Django 1.10 deprecation notices and can be ignored.

## Extras for the reviewers

- **CI workflow** (`.github/workflows/ci.yml`): on pushes to `develop` and pull requests to `main`, lints the backend with ruff, runs pytest in the dev image, and runs a full Compose smoke test (build, start, check `/` and `/api/tags`, verify that gunicorn is running).
- **Quality workflow** (`.github/workflows/quality.yml`): lints all workflows with actionlint and scans the repository for leaked secrets with Gitleaks.
- **Deploy workflow** (`.github/workflows/deployment.yaml`): deploys to the VM over SSH after CI and quality pass (see [Deployment](#deployment)).
- **Backend image hardening:** non-root user, database wait in the entrypoint, automatic migrations and `collectstatic`, `.env` variables required by Compose (`${VAR:?}`) instead of insecure defaults.
- **Single public port:** nginx reverse proxy for `/api/`, `/admin/`, and `/static/`; the backend and database are not published.
- **Fixes in the upstream code** that were needed for a working application:
  - The theme stylesheet from a dead CDN is bundled locally.
  - The default avatar from a dead CDN is served from the backend's own static files.
  - Creating an article failed because of a trailing slash in `POST /api/articles/`.
  - `/api/user` returned no default avatar for the current user.
  - The profile picture and the password from the settings page were not saved.

## Troubleshooting

- **Compose reports missing variables:** Create `.env` beside `docker-compose.yaml` and set `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD`. Run `docker compose config --quiet` again.
- **`Bad Request (400)` from the API:** The host name or IP in the browser is missing in `DJANGO_ALLOWED_HOSTS`. Add it to `.env` and run `docker compose up -d`.
- **`502 Bad Gateway` right after the start:** The backend is still running migrations. Wait a few seconds and check `docker compose logs backend`.
- **Changing database credentials does not take effect:** Postgres reads the initialization variables only for an empty data volume. Do not delete `postgres_data` to apply a change unless you intend to discard the database and have a backup.
- **Port `8282` is unavailable:** Set another port in `CONDUIT_PORT` in `.env`, restart the setup, and use the new port in the browser and VM network rules.
- **Conduit is unreachable on the VM:** Check `docker compose ps`, the logs, the published port, and the inbound firewall and cloud network rules.
- **A container stays stopped after `docker kill` or `docker compose stop`:** That is a manual stop. Start it again with `docker compose up -d`.
