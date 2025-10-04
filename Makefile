.PHONY: help install start-infra stop-infra init-db run-api run-consumer dev clean

help:
	@echo "HAR File Processing API"
	@echo ""
	@echo "Available commands:"
	@echo "  make install      - Install dependencies using uv"
	@echo "  make start-infra  - Start Docker infrastructure (Kafka, PostgreSQL, MinIO, Redis)"
	@echo "  make stop-infra   - Stop Docker infrastructure"
	@echo "  make init-db      - Initialize database with extensions and tables"
	@echo "  make run-api      - Run FastAPI server"
	@echo "  make run-consumer - Run Kafka consumer worker"
	@echo "  make dev          - Start infrastructure and initialize database"
	@echo "  make clean        - Stop infrastructure and clean volumes"

install:
	@echo "Installing dependencies..."
	uv sync

start-infra:
	@echo "Starting infrastructure..."
	docker-compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@echo "✓ Infrastructure started"
	@echo ""
	@echo "Services:"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  MinIO API: localhost:9000"
	@echo "  MinIO Console: http://localhost:9001"
	@echo "  Kafka: localhost:9092"
	@echo "  Redis: localhost:6379"

stop-infra:
	@echo "Stopping infrastructure..."
	docker-compose down

init-db:
	@echo "Initializing database..."
	uv run python scripts/init_db.py

run-api:
	@echo "Starting FastAPI server..."
	uv run python app/main.py

run-consumer:
	@echo "Starting Kafka consumer..."
	uv run python app/consumer.py

dev: start-infra
	@echo "Waiting for services to initialize..."
	@sleep 10
	@make init-db
	@echo ""
	@echo "✅ Development environment ready!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Copy .env.example to .env and add your OpenAI API key"
	@echo "  2. Run 'make run-api' in one terminal"
	@echo "  3. Run 'make run-consumer' in another terminal"
	@echo ""
	@echo "API will be available at: http://localhost:8000"
	@echo "API docs: http://localhost:8000/docs"

clean:
	@echo "Cleaning up..."
	docker-compose down -v
	@echo "✓ Infrastructure stopped and volumes removed"
