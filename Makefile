# DocSeva development helpers
.PHONY: help install run migrate shell test lint createsuperuser collectstatic docker-build docker-up docker-down

help:
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## Install Python dependencies
	pip install -r requirements.txt

run: ## Start development server (DEBUG=True)
	DEBUG=True python manage.py runserver

migrate: ## Apply database migrations
	python manage.py migrate

makemigrations: ## Create new migrations
	python manage.py makemigrations

shell: ## Open Django shell
	python manage.py shell

test: ## Run test suite
	python manage.py test core --verbosity=2

lint: ## Run ruff linter (install separately: pip install ruff)
	ruff check .

createsuperuser: ## Create a superuser
	python manage.py createsuperuser

collectstatic: ## Collect static files
	python manage.py collectstatic --noinput

check: ## Run Django system checks
	python manage.py check --deploy

docker-build: ## Build Docker image
	docker compose build

docker-up: ## Start all services
	docker compose up -d

docker-down: ## Stop all services
	docker compose down

docker-logs: ## Tail web logs
	docker compose logs -f web
