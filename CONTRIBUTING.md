# Contributing

## Overview
Thank you for contributing to the LLM Arena backend.

This folder contains the Django backend for:
- blind multi-turn arena battles
- conversation-level voting
- direct chat with selected Vezilka models

## Before You Start
- read the local [README.md](/Users/itonkdong/Work/Fax/INSOK/llm-arena/llm-arena-backend/README.md)
- use `.env.example` as the template
- never commit secrets or real API keys

## Development Flow
- make focused changes
- keep API behavior and admin behavior intentional
- update docs when setup, endpoints, or product semantics change
- prefer small, reviewable pull requests

## Docker And Environment
- use the local `docker-compose.yml` when working on backend plus Postgres

## Code Guidelines
- preserve the current Django app structure
- keep admin changes readable and deliberate
- avoid unrelated refactors in the same change
- keep migration and setup behavior easy to follow

## Pull Requests
- explain what changed and why
- mention any env, migration, setup, or API impact
- call out known gaps or follow-up work

## Security
- do not commit `.env` files
- rotate leaked keys immediately
- verify Docker build context and `.dockerignore` before publishing images
