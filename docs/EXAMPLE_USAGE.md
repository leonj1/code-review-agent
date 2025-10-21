# Test Fixer Agent Team - Example Usage

This document demonstrates how the Test Fixer Agent Team works with a concrete example.

## Scenario: Fixing a Failing Authentication Test

### Initial Failing Test

```python
# tests/test_auth.py
def test_login_with_valid_credentials():
    """Test that login works with valid credentials."""
    result = login("user@example.com", "password123")
    assert result.success is True
    assert result.user_id == 42
```

### Original Implementation (Problematic)

```python
# src/auth.py
import os
import requests

def login(email, password):
    """Login user with email and password."""
    # PROBLEM 1: Function too long (60+ lines)
    # PROBLEM 2: Direct environment variable access
    api_key = os.environ['API_KEY']
    api_url = os.getenv('AUTH_API_URL', 'https://api.example.com')

    # PROBLEM 3: Creates HTTP client inside function
    session = requests.Session()
    session.headers.update({'X-API-Key': api_key})

    # PROBLEM 4: No type hints on arguments
    # PROBLEM 5: No return type specified

    # Validate email format
    if '@' not in email:
        return {'success': False, 'error': 'Invalid email'}

    # Validate password strength
    if len(password) < 8:
        return {'success': False, 'error': 'Password too short'}

    # Check password complexity
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    if not (has_upper and has_lower and has_digit):
        return {'success': False, 'error': 'Password not complex enough'}

    # Make API request
    try:
        response = session.post(
            f'{api_url}/auth/login',
            json={'email': email, 'password': password}
        )
        response.raise_for_status()
        data = response.json()

        # Process response
        user_id = data.get('user_id')
        session_token = data.get('token')
        expires_at = data.get('expires_at')

        # Store session in database (more client creation!)
        import psycopg2
        conn = psycopg2.connect(
            host=os.environ['DB_HOST'],
            database=os.environ['DB_NAME'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD']
        )
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (user_id, token, expires_at) VALUES (%s, %s, %s)",
            (user_id, session_token, expires_at)
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Return result
        return {
            'success': True,
            'user_id': user_id,
            'token': session_token
        }

    except requests.RequestException as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': 'Internal error'}
```

## Running the Agent Team

```bash
python src/test_fixer_agent_team.py --dry-run --verbose
```

## Agent Team Workflow

### Step 1: Run Tests

```
Step 1: Running Tests
Running tests with 'make test'...

FAILED tests/test_auth.py::test_login_with_valid_credentials
```

### Step 2: IdentifyFailingTests Agent

The agent parses the output:

```
Step 2: Identifying Failing Tests

Parsing 1 failing tests...

┌─────────────────────────────────────────────────────────────┐
│                    Failing Tests                            │
├──────────────────┬──────────────────┬────────┬──────────────┤
│ Test File        │ Test Name        │ Error  │ Message      │
├──────────────────┼──────────────────┼────────┼──────────────┤
│ tests/test_auth  │ test_login_with  │ Assert │ Expected     │
│ .py              │ _valid_credent.. │        │ LoginResult  │
└──────────────────┴──────────────────┴────────┴──────────────┘
```

Creates a `FailingTest` model:
```python
FailingTest(
    test_file='tests/test_auth.py',
    test_name='test_login_with_valid_credentials',
    test_class=None,
    test_method='test_login_with_valid_credentials',
    error_type='AssertionError',
    error_message='Expected LoginResult object',
    traceback='...',
    line_number=3
)
```

### Step 3: RefactorAgent Analysis

The agent identifies the function under test (`login`) and runs validation hooks:

```
Step 3: Refactoring Functions

Analyzing test: test_login_with_valid_credentials

┌──────────────────────────────────────────────────────────────┐
│                  Validation Results                          │
├────────────────────┬──────────┬────────────────────────────┤
│ Hook               │ Status   │ Message                    │
├────────────────────┼──────────┼────────────────────────────┤
│ max_function_len   │ ✗ FAILED │ Function has 65 lines,     │
│                    │          │ exceeds maximum of 30      │
├────────────────────┼──────────┼────────────────────────────┤
│ no_env_access      │ ✗ FAILED │ Function reads directly    │
│                    │          │ from environment variables │
├────────────────────┼──────────┼────────────────────────────┤
│ no_client_creation │ ✗ FAILED │ Function creates client    │
│                    │          │ objects: requests, psycopg2│
├────────────────────┼──────────┼────────────────────────────┤
│ typed_arguments    │ ✗ FAILED │ Function arguments are not │
│                    │          │ properly typed or use 'Any'│
├────────────────────┼──────────┼────────────────────────────┤
│ typed_return       │ ✗ FAILED │ Function return type not   │
│                    │          │ specified                  │
├────────────────────┼──────────┼────────────────────────────┤
│ no_default_args    │ ✓ PASSED │ No default argument values │
└────────────────────┴──────────┴────────────────────────────┘
```

### Step 4: Refactored Implementation

After refactoring, the code becomes:

```python
# src/auth.py
from typing import Protocol
from pydantic import BaseModel, EmailStr
from dataclasses import dataclass


# Pydantic models for type safety
class LoginRequest(BaseModel):
    """Login request with email and password."""
    email: EmailStr
    password: str


class LoginResult(BaseModel):
    """Result of login attempt."""
    success: bool
    user_id: int | None = None
    token: str | None = None
    error: str | None = None


# Configuration passed in, not read from env
class AuthConfig(BaseModel):
    """Authentication configuration."""
    api_key: str
    api_url: str
    db_host: str
    db_name: str
    db_user: str
    db_password: str


# Interface for HTTP client (not concrete implementation)
class HttpClient(Protocol):
    """HTTP client interface for dependency injection."""
    def post(self, url: str, json: dict) -> dict:
        """Make POST request and return JSON response."""
        ...


# Interface for database (not concrete implementation)
class SessionStore(Protocol):
    """Session storage interface for dependency injection."""
    def save_session(self, user_id: int, token: str, expires_at: str) -> None:
        """Save user session."""
        ...


# Service class with injected dependencies
class AuthService:
    """Authentication service with dependency injection."""

    def __init__(
        self,
        config: AuthConfig,
        http_client: HttpClient,
        session_store: SessionStore
    ):
        """
        Initialize auth service.

        Args:
            config: Authentication configuration
            http_client: HTTP client for API calls
            session_store: Session storage
        """
        self.config = config
        self.http_client = http_client
        self.session_store = session_store

    def login(self, request: LoginRequest) -> LoginResult:
        """
        Authenticate user with email and password.

        Args:
            request: Login request with credentials

        Returns:
            LoginResult with success status and user data
        """
        # Validate email (already done by Pydantic EmailStr)
        # Validate password
        validation_error = self._validate_password(request.password)
        if validation_error:
            return LoginResult(success=False, error=validation_error)

        # Make API request
        try:
            response_data = self._call_auth_api(request)
            self._save_session(response_data)
            return self._create_success_result(response_data)
        except Exception as e:
            return LoginResult(success=False, error=str(e))

    def _validate_password(self, password: str) -> str | None:
        """Validate password meets requirements. (11 lines)"""
        if len(password) < 8:
            return 'Password too short'

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)

        if not (has_upper and has_lower and has_digit):
            return 'Password not complex enough'

        return None

    def _call_auth_api(self, request: LoginRequest) -> dict:
        """Call authentication API. (5 lines)"""
        return self.http_client.post(
            f'{self.config.api_url}/auth/login',
            json={'email': request.email, 'password': request.password}
        )

    def _save_session(self, response_data: dict) -> None:
        """Save user session to store. (6 lines)"""
        self.session_store.save_session(
            user_id=response_data['user_id'],
            token=response_data['token'],
            expires_at=response_data['expires_at']
        )

    def _create_success_result(self, data: dict) -> LoginResult:
        """Create successful login result. (6 lines)"""
        return LoginResult(
            success=True,
            user_id=data['user_id'],
            token=data['token']
        )
```

### Post-Refactoring Validation

```
┌──────────────────────────────────────────────────────────────┐
│            Post-Refactoring Validation Results               │
├────────────────────┬──────────┬────────────────────────────┤
│ Hook               │ Status   │ Message                    │
├────────────────────┼──────────┼────────────────────────────┤
│ max_function_len   │ ✓ PASSED │ Function length OK: 16     │
│                    │          │ lines                      │
├────────────────────┼──────────┼────────────────────────────┤
│ no_env_access      │ ✓ PASSED │ No direct environment      │
│                    │          │ variable access            │
├────────────────────┼──────────┼────────────────────────────┤
│ no_client_creation │ ✓ PASSED │ No client objects created  │
│                    │          │ in function                │
├────────────────────┼──────────┼────────────────────────────┤
│ typed_arguments    │ ✓ PASSED │ All arguments properly     │
│                    │          │ typed                      │
├────────────────────┼──────────┼────────────────────────────┤
│ typed_return       │ ✓ PASSED │ Return type properly       │
│                    │          │ specified                  │
├────────────────────┼──────────┼────────────────────────────┤
│ no_default_args    │ ✓ PASSED │ No default argument values │
└────────────────────┴──────────┴────────────────────────────┘

Refactored code written to src/auth.py
```

### Updated Test

```python
# tests/test_auth.py
from src.auth import AuthService, LoginRequest, LoginResult, AuthConfig
from unittest.mock import Mock


def test_login_with_valid_credentials():
    """Test that login works with valid credentials."""
    # Create mock dependencies
    mock_http_client = Mock()
    mock_http_client.post.return_value = {
        'user_id': 42,
        'token': 'abc123',
        'expires_at': '2024-12-31T23:59:59Z'
    }

    mock_session_store = Mock()

    # Create config
    config = AuthConfig(
        api_key='test-key',
        api_url='https://api.example.com',
        db_host='localhost',
        db_name='test_db',
        db_user='test_user',
        db_password='test_pass'
    )

    # Create service with injected dependencies
    auth_service = AuthService(config, mock_http_client, mock_session_store)

    # Test login
    request = LoginRequest(email='user@example.com', password='Password123')
    result = auth_service.login(request)

    # Assertions
    assert result.success is True
    assert result.user_id == 42
    assert result.token == 'abc123'

    # Verify interactions
    mock_http_client.post.assert_called_once()
    mock_session_store.save_session.assert_called_once()
```

### Step 5: SummaryAgent

```
Step 4: Generating Summary

╭──────────────────────────────────────────────────────────────╮
│                   Refactoring Summary                        │
│                                                              │
│  Addressed 1 of 1 failing tests. Completed 1 refactoring    │
│  successfully. Key improvements: reduced function           │
│  complexity, removed environment dependencies, improved     │
│  dependency injection, added type safety, and clarified     │
│  return types.                                              │
╰──────────────────────────────────────────────────────────────╯

╭──────────────────────────────────────────────────────────────╮
│                      Statistics                              │
│                                                              │
│  Tests Fixed: 1                                              │
│  Total Refactorings: 1                                       │
│  Successful: 1                                               │
│  Success Rate: 100.0%                                        │
╰──────────────────────────────────────────────────────────────╯
```

## Key Improvements

### Before Refactoring
- ❌ 65 lines - hard to understand and test
- ❌ Reads from `os.environ` - not testable
- ❌ Creates `requests.Session()` - can't mock
- ❌ Creates database connection - can't test
- ❌ No type hints - unclear contracts
- ❌ Returns dict - no type safety

### After Refactoring
- ✅ Main function 16 lines - focused and clear
- ✅ Helper functions < 12 lines each
- ✅ Config passed as argument - fully testable
- ✅ Clients injected via constructor - easy to mock
- ✅ Full type hints with Pydantic models
- ✅ Returns typed `LoginResult` - type safe
- ✅ Uses Protocol for interfaces - proper abstraction
- ✅ All dependencies explicit - no hidden dependencies

## Benefits of Refactored Code

### 1. Testability
```python
# Easy to test with mocks - no real HTTP calls or DB connections
mock_client = Mock()
mock_store = Mock()
service = AuthService(config, mock_client, mock_store)
```

### 2. Type Safety
```python
# IDE autocomplete and type checking work
request = LoginRequest(email="test@example.com", password="pass")
result = service.login(request)
assert result.user_id  # Type checker knows this is int | None
```

### 3. Dependency Injection
```python
# Easy to swap implementations
production_service = AuthService(prod_config, RealHttpClient(), PostgresStore())
test_service = AuthService(test_config, MockHttpClient(), InMemoryStore())
```

### 4. Single Responsibility
```python
# Each function has one clear purpose
_validate_password()  # Only validates
_call_auth_api()      # Only makes API call
_save_session()       # Only saves session
```

### 5. Maintainability
```python
# Easy to find and fix bugs
# Easy to add features (e.g., 2FA)
# Easy to change implementations (e.g., switch from requests to httpx)
```

## Running the Full Workflow

```bash
# 1. See what's wrong
python src/test_fixer_agent_team.py --dry-run

# 2. Review the analysis
# Read the validation results

# 3. Apply the fixes
python src/test_fixer_agent_team.py

# 4. Verify tests pass
make test

# 5. Review the changes
git diff src/auth.py

# 6. Commit if satisfied
git add src/auth.py tests/test_auth.py
git commit -m "Refactor auth.login for better testability"
```

## Lessons Learned

1. **Long functions hide complexity** - Breaking into smaller functions reveals the actual structure
2. **Environment variables make testing hard** - Pass config as arguments
3. **Creating clients couples code** - Inject clients via constructor
4. **Type hints prevent bugs** - Pydantic models catch errors early
5. **Interfaces enable mocking** - Use Protocol for dependency injection
6. **Explicit > Implicit** - Make all dependencies visible in the constructor

This example demonstrates how the Test Fixer Agent Team transforms hard-to-test code into clean, testable, maintainable code following best practices.
