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

The backend container waits for Postgres and runs setup automatically on startup.

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

For detailed endpoint specifications and descriptions, see the files in [api_docs](/Users/itonkdong/Work/Fax/INSOK/llm-arena/llm-arena-backend/api_docs):
- [llm-arena.openapi.yaml](/Users/itonkdong/Work/Fax/INSOK/llm-arena/llm-arena-backend/api_docs/llm-arena.openapi.yaml) for the arena endpoints
- [chat.openapi.yaml](/Users/itonkdong/Work/Fax/INSOK/llm-arena/llm-arena-backend/api_docs/chat.openapi.yaml) for the chat endpoints

## Project Purpose
This service is responsible for:
- selecting two LLMs for a battle
- sending every turn prompt to both models
- anonymizing and returning the full transcript snapshot
- storing turns, responses, metadata, and final conversation votes
- exposing direct chat endpoints for chosen Vezilka models
- storing chat sessions and chat messages
- exposing leaderboard and model-related API endpoints

The backend is designed around blind comparison, randomized response ordering, multi-turn battle conversations, direct Vezilka chat, and persistent storage of evaluation results.

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
