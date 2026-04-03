# LLM Arena Backend

## Overview
This backend powers the API for LLM Arena, a platform for blind evaluation and direct exploration of large language models.

The main flow is:
- a user starts a battle with one prompt
- the backend sends that prompt to two different models
- the frontend shows the answers as anonymous response A and response B
- the user can continue the same battle with additional prompts across multiple turns
- the user votes on the full conversation transcript, not just the opening turn
- the backend stores the battle, turns, responses, and vote for later analysis
- the project also includes a direct chat flow where the user selects a Vezilka model and chats with it normally

There are two arena modes:
- standard arena battles
- experimental arena battles

Experimental arena battles are authenticated and user-owned. They let the system sample inference parameters such as temperature, top-p, top-k, frequency penalty, and presence penalty, persist those sampled values for the entire battle, and reveal them only after voting. Experimental battles also support user-authored response improvements for the latest turn without overwriting the original model output.

The project is focused on evaluating Macedonian fine-tuned LLMs alongside global providers.

## Tech Stack
- Django
- Django REST Framework
- PostgreSQL
- DRF Spectacular for API docs
- LangChain integrations for model providers
- JWT authentication with `djangorestframework-simplejwt`
- Google OAuth
- GitHub OAuth

## Quick Start
### Run with Docker
From inside this folder:

```bash
docker compose up --build
```

This starts:
- backend on `http://localhost:8000`
- postgres on `localhost:5432`

The backend container waits for Postgres and runs setup automatically on startup.

That startup flow also:
- seeds the database with the required initial data
- creates a default superuser with username `admin` and password `admin`

After the first cold start, you can disable this automatic setup behavior by setting `AUTO_START_SETUP=false`.

### Setup Commands
The project includes two useful management commands for local setup and reset flows.

`setup_project`
- prepares the project for normal use
- runs the setup sequence that seeds the required base data
- creates the default admin user when needed

Example:

```bash
conda run -n adstract-backend python manage.py setup_project --full-auto
```

`hardreset`
- drops and recreates the working database state for a fresh start
- is useful during heavy schema changes or when you want a clean seeded environment again
- runs the project setup flow again after resetting

Example:

```bash
conda run -n adstract-backend python manage.py hardreset
```

`AUTO_START_SETUP`
- this env flag controls whether the backend container automatically runs the setup flow on startup
- when `AUTO_START_SETUP=true`, container startup will run the setup logic automatically
- when `AUTO_START_SETUP=false`, the backend starts without auto-running setup, and you can run `setup_project` or `hardreset` manually

Typical usage:
- first local Docker boot: leave `AUTO_START_SETUP=true`
- later boots on an already prepared environment: set `AUTO_START_SETUP=false`

### Environment
Use `.env.example` as the template and create a local `.env` file.

Important variables:
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`
- `FINKI_BASE_URL`
- `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`
- `JWT_REFRESH_TOKEN_LIFETIME_DAYS`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI`
- `GITHUB_OAUTH_CLIENT_ID`
- `GITHUB_OAUTH_CLIENT_SECRET`
- `GITHUB_OAUTH_REDIRECT_URI`

## API Endpoints

For detailed endpoint specifications and descriptions, see the files in [api_docs](/Users/itonkdong/Work/Fax/INSOK/llm-arena/llm-arena-backend/api_docs):
- [llm-arena.openapi.yaml](/Users/itonkdong/Work/Fax/INSOK/llm-arena/llm-arena-backend/api_docs/llm-arena.openapi.yaml) for the arena endpoints
- [chat.openapi.yaml](/Users/itonkdong/Work/Fax/INSOK/llm-arena/llm-arena-backend/api_docs/chat.openapi.yaml) for the chat endpoints

## Authentication

The backend uses first-party JWT authentication.

- Google and GitHub OAuth are used for login
- the backend exchanges provider auth codes for user identity

Ownership rules:
- chat sessions always require authentication and belong to one user
- experimental arena battles require authentication and belong to one user
- standard arena battles can be anonymous
- if a logged-in user creates a standard arena battle, that battle becomes user-owned

## Admin Features

The Django admin includes:
- model/provider management and activation controls
- experimental sampling spec management
- agent prompt management
- battle inspection with:
  - turns and per-side responses
  - response diagnostics such as tokens, latency, finish reason, and raw metadata
  - response improvements for experimental battles
- human votes and LLM judge votes
- an admin action that lets staff judge selected battles with an active model acting as an LLM judge


## Project Purpose
This service is responsible for:
- selecting two LLMs for a battle
- sending every turn prompt to both models
- anonymizing and returning the full transcript snapshot
- storing turns, responses, metadata, and final conversation votes
- storing optional experimental configurations and response improvements
- exposing direct chat endpoints for chosen Vezilka models
- storing chat sessions and chat messages
- handling OAuth login and JWT issuance
- exposing leaderboard and model-related API endpoints

The backend is designed around blind comparison, multi-turn battle conversations, experimental parameterized evaluation, direct Vezilka chat and persistent storage of evaluation results.

## Local Compose Services
The local [docker-compose.yml](/Users/itonkdong/Work/Fax/INSOK/llm-arena/llm-arena-backend/docker-compose.yml) in this folder starts only:
- `backend`
- `db`

This is useful when you want to run the frontend separately or connect an already running frontend to the backend API.

## Production Docker
For a deployment-style backend image, use [Dockerfile.deployment](/Users/itonkdong/Work/Fax/INSOK/llm-arena/llm-arena-backend/Dockerfile.deployment#L1).

It:
- installs the backend dependencies
- copies the Django project into the image
- runs migrations on container startup
- starts the backend with the current deployment startup command

## Project Context
This project was developed as part of the Vezilka project under the guidance of Assistant Teachers Ema Pandilova and Dimitar Peshevski.

The student developers are:
- Andrea Stevanoska
- Viktor Kostadinoski
- Gorazd Filipovski

All contributors listed above are from the Faculty of Computer Science and Engineering (FINKI), Skopje.

FINKI also developed, trained, and fine-tuned all Vezilka models used in this broader project context.
