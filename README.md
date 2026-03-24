# LLM Arena Backend

## Overview
This backend powers the API for LLM Arena, a blind evaluation platform for comparing large language models through human preference voting.

The main flow is:
- a user submits one prompt
- the backend sends that prompt to two different models
- the frontend shows the answers as anonymous response A and response B
- the user votes for the better answer, or marks them as equal
- the backend stores the battle, responses, and vote for later analysis

The project is focused on evaluating Macedonian fine-tuned LLMs alongside global providers.

## Tech Stack
- Django
- Django REST Framework
- PostgreSQL
- DRF Spectacular for API docs
- LangChain integrations for model providers

## Quick Start
### Run with Docker
From inside this folder:

```bash
docker compose up --build
```

This starts:
- backend on `http://localhost:8000`
- postgres on `localhost:5432`

The backend container waits for Postgres and runs migrations automatically on startup.

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

## API Endpoints
Useful local endpoints:
- `http://localhost:8000/api/docs/` for Swagger UI
- `http://localhost:8000/api/schema/` for the OpenAPI schema
- `http://localhost:8000/api/arena/leaderboard/` for leaderboard data
- `http://localhost:8000/api/arena/battles/` to create a new battle
- `http://localhost:8000/api/arena/battles/<uuid>/vote/` to submit a vote
- `http://localhost:8000/api/arena/models/<model_name>/` for model details

## Project Purpose
This service is responsible for:
- selecting two LLMs for a battle
- sending the same prompt to both models
- anonymizing and returning the responses
- storing prompts, responses, metadata, and votes
- exposing leaderboard and model-related API endpoints

The backend is designed around blind comparison, randomized response ordering, and persistent storage of evaluation results.

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
- starts Gunicorn instead of Django `runserver`
