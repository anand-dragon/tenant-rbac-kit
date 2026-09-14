COMPOSE = docker compose -f deploy/docker-compose.yml

.PHONY: up down logs migrate seed-roles test lint typecheck fmt

up:
	@test -f deploy/.env || cp deploy/.env.example deploy/.env
	$(COMPOSE) up -d --build
	@echo "waiting for services..."
	@sleep 5
	$(MAKE) migrate

down:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f

migrate:
	$(COMPOSE) exec api uv run alembic -c alembic/alembic.ini upgrade head

seed-roles:
	$(COMPOSE) exec api uv run python -m tenant_rbac_kit.seed_roles

test:
	uv run pytest

lint:
	uv run ruff check .

fmt:
	uv run ruff format .

typecheck:
	uv run mypy src
