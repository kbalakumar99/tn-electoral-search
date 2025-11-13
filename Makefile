.PHONY: install dev prod test clean init-db docker-build docker-run

# Development setup
install:
	python -m venv venv
	./venv/bin/pip install -r requirements.txt

# Install with full PDF processing capabilities
install-full:
	python -m venv venv
	./venv/bin/pip install -r requirements-full.txt

# Initialize database
init-db:
	python scripts/init_db.py

# Populate database with electoral data (preserves existing voter data)  
populate-data:
	python scripts/populate_data.py

# Run development server
dev:
	python scripts/dev_server.py

# Run production server
prod:
	python scripts/run_server.py

# Run tests
test:
	python -m pytest tests/ -v

# Clean up
clean:
	rm -rf __pycache__ app/__pycache__ app/extractors/__pycache__
	rm -rf .pytest_cache
	rm -rf database/*.db database/*.db-shm database/*.db-wal

# Docker commands
docker-build:
	docker build -t tn-electoral-search .

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

# Help
help:
	@echo "Available commands:"
	@echo "  install       - Create virtual environment and install core dependencies"
	@echo "  install-full  - Create virtual environment and install full dependencies (includes PDF import)"
	@echo "  init-db       - Initialize database with schema and populate with electoral data"
	@echo "  populate-data - Populate database with electoral data (preserves voter data)"
	@echo "  dev           - Run development server with auto-reload"
	@echo "  prod          - Run production server"
	@echo "  test          - Run tests"
	@echo "  clean         - Clean up cache and database files"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-run    - Run with Docker Compose"
	@echo "  docker-stop   - Stop Docker containers"