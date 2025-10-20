.PHONY: help test test-verbose test-coverage test-specific clean install install-dev run-review run-fixer format lint docker-build-test docker-test docker-clean

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

test: ## Run all tests
	venv/bin/pytest -v

test-verbose: ## Run tests with verbose output and show print statements
	venv/bin/pytest -vv -s

test-coverage: ## Run tests with coverage report
	venv/bin/pytest --cov=. --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "Coverage report generated in htmlcov/index.html"

test-specific: ## Run specific test file (usage: make test-specific FILE=test_main.py)
	venv/bin/pytest -v $(FILE)

test-main: ## Run tests for code_review_agent only
	venv/bin/pytest -v test_main.py

test-fixer: ## Run tests for test_fixer only
	venv/bin/pytest -v test_test_fixer.py

test-watch: ## Run tests in watch mode (requires pytest-watch)
	venv/bin/ptw -- -v

clean: ## Clean up generated files (cache, coverage, etc.)
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@echo "Cleaned up generated files"

install: ## Install production dependencies
	venv/bin/pip install -r requirements.txt

install-dev: ## Install all dependencies including test dependencies
	venv/bin/pip install -r requirements.txt
	venv/bin/pip install -r requirements-test.txt

install-all: install-dev ## Alias for install-dev

setup-venv: ## Create virtual environment and install dependencies
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt && pip install -r requirements-test.txt
	@echo ""
	@echo "Virtual environment created! Activate with: source venv/bin/activate"

run-review: ## Run code review agent in interactive mode
	venv/bin/python code_review_agent.py --model sonnet

run-review-file: ## Review a specific file (usage: make run-review-file FILE=test_fixer.py)
	venv/bin/python code_review_agent.py --file $(FILE)

run-fixer: ## Run test fixer on current directory
	venv/bin/python test_fixer.py

run-fixer-path: ## Run test fixer on specific path (usage: make run-fixer-path PATH=test_main.py)
	venv/bin/python test_fixer.py $(PATH)

format: ## Format code with black (if installed)
	@which black > /dev/null && black . || echo "black not installed, skipping format"

lint: ## Lint code with flake8 (if installed)
	@which flake8 > /dev/null && flake8 . --max-line-length=120 --exclude=.git,__pycache__,.pytest_cache || echo "flake8 not installed, skipping lint"

check: lint test ## Run linting and tests

db-reset: ## Reset the projects database
	rm -f projects.db
	@echo "Database reset"

all: clean install-dev test ## Clean, install dependencies, and run tests

docker-build-test: ## Build Docker test image
	docker build -f Dockerfile.test -t code-review-agent-test .

docker-test: docker-build-test ## Run tests in Docker container
	docker run --rm code-review-agent-test

docker-clean: ## Remove Docker test image
	docker rmi code-review-agent-test 2>/dev/null || true
	@echo "Docker test image cleaned"
