# Makefile for NearbyTix - Common Docker commands

.PHONY: help build up down restart logs shell test migrate clean

help: ## Show this help message
	@echo "NearbyTix - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build all Docker containers
	docker-compose build

up: ## Start all services
	docker-compose up -d

start: ## Start all services (alias for up)
	docker-compose up -d

down: ## Stop all services
	docker-compose down

stop: ## Stop all services (alias for down)
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## View logs from all services
	docker-compose logs -f

logs-api: ## View logs from API service
	docker-compose logs -f api

logs-db: ## View logs from database service
	docker-compose logs -f db

logs-celery: ## View logs from Celery worker
	docker-compose logs -f celery_worker

shell: ## Open shell in API container
	docker-compose exec api bash

db-shell: ## Open PostgreSQL shell
	docker-compose exec db psql -U nearbytix_user -d nearbytix

test: ## Run tests
	docker-compose exec api pytest tests/ -v

test-cov: ## Run tests with coverage
	docker-compose exec api pytest tests/ --cov=app --cov-report=html --cov-report=term

migrate: ## Run database migrations
	docker-compose exec api alembic upgrade head

migrate-create: ## Create a new migration (use: make migrate-create MSG="description")
	docker-compose exec api alembic revision --autogenerate -m "$(MSG)"

clean: ## Stop and remove all containers, volumes, and networks
	docker-compose down -v

clean-build: ## Clean and rebuild everything
	docker-compose down -v
	docker-compose build --no-cache
	docker-compose up -d

ps: ## Show status of all services
	docker-compose ps

dev: ## Start services and view logs
	docker-compose up --build

install-dev: ## Install development dependencies in container
	docker-compose exec api pip install -r requirements-dev.txt
