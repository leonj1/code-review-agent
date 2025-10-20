# Code Review Agent

A sophisticated AI-powered code review system using Claude with specialized sub-agents for comprehensive analysis.

## Features

### Code Review Agent (code_review_agent.py)
- **9 Specialized Sub-Agents** analyzing different aspects:
  - CorrectnessAgent - Logical errors and bugs
  - SecurityAgent - Security vulnerabilities
  - PerformanceAgent - Performance bottlenecks
  - StyleAgent - Code readability and style
  - RobustnessAgent - Error handling and resilience
  - StructureAgent - Architecture and design patterns
  - TestingAgent - Test quality and completeness
  - CoverageAgent - Test coverage analysis
  - DocumentationAgent - Documentation quality

### Test Fixer Agent (test_fixer.py)
- **Automatically fixes failing tests** through iterative analysis
- **Intelligent stopping conditions** to prevent infinite loops
- **Service pattern architecture** for testability

## Architecture

### Service Pattern for Testability

The project uses dependency injection to make the code testable:

```
IClaudeService (interface)
    ├── ClaudeServiceImpl (production)
    └── FakeClaudeService (testing)
```

This allows:
- Easy unit testing without API calls
- Mocking Claude responses
- Faster test execution
- Predictable test behavior

## Installation

### Using Virtual Environment (Recommended)

```bash
# Create venv and install all dependencies
make setup-venv

# Activate the virtual environment
source venv/bin/activate

# Run tests
make test
```

### Using Make (System-wide)

```bash
# Install production dependencies
make install

# Install all dependencies (including test dependencies)
make install-dev

# Install and run tests
make all
```

### Manual Installation

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt
```

## Quick Start with Make

```bash
# Show all available commands
make help

# Install dependencies and run tests
make all

# Run tests
make test

# Run code review on a file
make run-review-file FILE=test_fixer.py

# Run test fixer
make run-fixer
```

## Usage

### Code Review Agent

```bash
# Using Make
make run-review                              # Interactive mode
make run-review-file FILE=path/to/file.py   # Review specific file

# Using Python directly
python code_review_agent.py --model sonnet
python code_review_agent.py --file path/to/file.py
python code_review_agent.py --file test_fixer.py --stats true
```

### Test Fixer Agent

```bash
# Using Make
make run-fixer                          # Fix tests in current directory
make run-fixer-path PATH=test_main.py  # Fix specific test file

# Using Python directly
python test_fixer.py                    # Fix tests in current directory
python test_fixer.py test_main.py      # Fix specific test file
python test_fixer.py --max-iterations 10  # Custom safety limit
python test_fixer.py --model opus        # Use different model
```

### Test Fixer: Agent-Driven Stopping

The test fixer uses an **intelligent, agent-driven approach** instead of arbitrary limits.

#### How It Works

After each fix attempt, Claude analyzes:
- **Progress tracking**: Are failures decreasing?
- **Pattern detection**: Are we repeating the same failed approaches?
- **Strategy assessment**: Do we have alternative strategies to try?
- **Solvability analysis**: Is this problem fixable with available information?

Based on this analysis, **Claude decides** whether to continue or stop.

#### Example Agent Decision

```
CONTINUE: I'll try a different approach - using mock objects instead of
real dependencies, which should resolve the initialization errors.

or

STOP: We've attempted 3 different mocking strategies and the same
import error persists. This appears to be a dependency issue that
requires manual investigation of the project setup.
```

#### Safety Stopping Conditions

While the agent makes primary decisions, these safety conditions override:

1. **Success**: All tests pass ✅
2. **Safety limit**: 20 iterations (rarely hit, agent stops before this)
3. **Breaking changes**: Test count drops significantly
4. **User interruption**: Ctrl+C

#### Benefits Over Fixed Iteration Limits

✅ **Intelligent decisions**: Agent recognizes when it's stuck vs. when it has new ideas
✅ **Learns from history**: Previous attempts inform future strategies
✅ **Avoids repetition**: Won't try the same failed approach twice
✅ **Natural stopping**: Stops when truly stuck, not at arbitrary limits
✅ **Better success rate**: Can try more approaches when making progress

## Running Tests

### Using Make (Recommended)

```bash
# Run all tests
make test

# Run with verbose output
make test-verbose

# Run with coverage report
make test-coverage

# Run specific test file
make test-specific FILE=test_main.py

# Run only code review agent tests
make test-main

# Run only test fixer tests
make test-fixer

# Show all available targets
make help
```

### Using pytest directly

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest test_main.py

# Run with coverage
pytest --cov=. --cov-report=html
```

### Using Docker

Run tests in an isolated Docker container:

```bash
# Build and run tests in one command
make docker-test

# Or build and run separately
make docker-build-test
docker run --rm code-review-agent-test

# Clean up Docker image
make docker-clean
```

This ensures tests run in a clean, reproducible environment with all dependencies properly installed.

## Project Structure

```
code-review-agent/
├── code_review_agent.py       # Code review orchestrator
├── test_fixer.py              # Automatic test fixer
├── claude_service.py          # Service interface & implementations
├── test_main.py               # Unit tests for code_review_agent
├── test_test_fixer.py         # Unit tests for test_fixer
├── requirements.txt           # Production dependencies
├── requirements-test.txt      # Test dependencies
├── projects.db                # Project tracking database
├── Makefile                   # Build automation
├── Dockerfile.test            # Docker image for running tests
├── .dockerignore              # Docker ignore patterns
└── README.md                  # This file
```

## Makefile Reference

The Makefile provides convenient shortcuts for common tasks:

### Testing
- `make test` - Run all tests
- `make test-verbose` - Run tests with detailed output
- `make test-coverage` - Generate coverage report
- `make test-main` - Test code_review_agent only
- `make test-fixer` - Test test_fixer only
- `make test-specific FILE=<file>` - Test specific file

### Installation
- `make install` - Install production dependencies
- `make install-dev` - Install all dependencies (including dev)
- `make all` - Clean, install, and test

### Running Agents
- `make run-review` - Start code review agent (interactive)
- `make run-review-file FILE=<file>` - Review specific file
- `make run-fixer` - Run test fixer on current directory
- `make run-fixer-path PATH=<path>` - Fix specific test path

### Maintenance
- `make clean` - Remove generated files (cache, coverage, etc.)
- `make db-reset` - Reset projects database
- `make format` - Format code with black (if installed)
- `make lint` - Lint code with flake8 (if installed)
- `make check` - Run lint + tests

### Docker
- `make docker-build-test` - Build Docker test image
- `make docker-test` - Build and run tests in Docker
- `make docker-clean` - Remove Docker test image

### Help
- `make help` - Show all available targets

## Example: Testing with FakeClaudeService

```python
import asyncio
from claude_service import FakeClaudeService
from code_review_agent import main

async def test_code_review():
    # Create fake service with mock responses
    mock_responses = [
        {"type": "text", "content": "Analysis complete"}
    ]
    fake_service = FakeClaudeService(mock_responses=mock_responses)

    # Test main() with dependency injection
    await main(claude_service=fake_service)

    # Verify queries sent
    queries = fake_service.get_queries()
    assert len(queries) == 1
    assert "review" in queries[0]

asyncio.run(test_code_review())
```

## Design Principles

### Dependency Injection
- Main functions accept optional service parameters
- Enables testing without external dependencies
- Follows SOLID principles

### Interface Segregation
- `IClaudeService` defines clean contract
- Multiple implementations for different use cases
- Easy to extend with new implementations

### Single Responsibility
- Each agent has one specific focus area
- Service layer handles only Claude communication
- Clear separation of concerns

## Benefits of This Architecture

1. **Testability**: Full unit test coverage without API calls
2. **Flexibility**: Easy to swap implementations
3. **Maintainability**: Clear interfaces and separation
4. **Reliability**: Tests run fast and deterministically
5. **Extensibility**: Simple to add new agent types

## Contributing

When adding new features:

1. Define interfaces for external dependencies
2. Create both real and fake implementations
3. Write unit tests using fake implementations
4. Document stopping conditions for loops
5. Follow existing patterns for consistency

## License

MIT License - feel free to use and modify as needed.
