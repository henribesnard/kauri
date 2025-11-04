.PHONY: help install dev test clean docker-build docker-up docker-down migrate lint format

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	pip install -r requirements.txt
	python -m spacy download fr_core_news_md

dev: ## Run development server
	uvicorn app.main:app --reload --port 8003

worker: ## Run OCR worker
	python -m app.workers.ocr_worker

test: ## Run tests
	pytest tests/ -v

test-cov: ## Run tests with coverage
	pytest tests/ --cov=app --cov-report=html --cov-report=term

lint: ## Run linting
	flake8 app tests
	mypy app

format: ## Format code
	black app tests
	isort app tests

migrate: ## Run database migrations
	alembic upgrade head

migrate-create: ## Create new migration
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

docker-build: ## Build Docker images
	docker-compose build

docker-up: ## Start Docker containers
	docker-compose up -d

docker-down: ## Stop Docker containers
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

docker-restart: ## Restart Docker containers
	docker-compose restart

clean: ## Clean cache files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

init: ## Initialize project (first time setup)
	cp .env.example .env
	@echo "Please edit .env with your configuration"
	python -m venv venv
	@echo "Run 'source venv/bin/activate' to activate virtual environment"
	@echo "Then run 'make install' to install dependencies"
