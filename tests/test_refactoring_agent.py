"""
Tests for the RefactoringAgent class.
"""

import ast
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from refactoring_agent import (
    RefactoringAgent,
    FunctionInfo,
    ClassInfo,
    RefactoringAttempt,
    ValidationResult
)
from claude_service import FakeClaudeService


class TestFunctionInfo:
    """Test the FunctionInfo dataclass."""

    def test_function_info_creation(self):
        """Test creating a FunctionInfo instance."""
        func = FunctionInfo(
            name="test_func",
            lineno=10,
            col_offset=4,
            is_constructor=False,
            is_static=False,
            is_class_method=False,
            has_env_access=False,
            external_calls=["requests.get"],
            body="def test_func(): pass"
        )
        assert func.name == "test_func"
        assert func.lineno == 10
        assert func.external_calls == ["requests.get"]
        assert not func.is_constructor


class TestClassInfo:
    """Test the ClassInfo dataclass."""

    def test_class_info_creation(self):
        """Test creating a ClassInfo instance."""
        func = FunctionInfo(
            name="method",
            lineno=15,
            col_offset=4,
            is_constructor=False,
            is_static=False,
            is_class_method=False,
            has_env_access=False,
            external_calls=[],
            body="def method(): pass"
        )
        cls = ClassInfo(
            name="TestClass",
            lineno=10,
            functions=[func],
            primary_function="method"
        )
        assert cls.name == "TestClass"
        assert len(cls.functions) == 1
        assert cls.primary_function == "method"


class TestValidationResult:
    """Test the ValidationResult dataclass."""

    def test_validation_result_passed(self):
        """Test a passing validation result."""
        result = ValidationResult(passed=True)
        assert result.passed
        assert len(result.errors) == 0

    def test_validation_result_failed(self):
        """Test a failing validation result."""
        result = ValidationResult(
            passed=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"]
        )
        assert not result.passed
        assert len(result.errors) == 2
        assert len(result.warnings) == 1


class TestRefactoringAgent:
    """Test the RefactoringAgent class."""

    @pytest.fixture
    def agent(self):
        """Create a RefactoringAgent instance for testing."""
        fake_service = FakeClaudeService(mock_responses=[])
        return RefactoringAgent(
            claude_service=fake_service,
            model="sonnet",
            max_iterations=5
        )

    def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent.model == "sonnet"
        assert agent.max_iterations == 5
        assert len(agent.attempts) == 0
        assert agent.current_source == ""

    def test_check_env_access_with_os_environ(self, agent):
        """Test detecting os.environ access."""
        code = """
def test_func():
    value = os.environ['KEY']
    return value
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert agent._check_env_access(func_node) is True

    def test_check_env_access_with_os_getenv(self, agent):
        """Test detecting os.getenv access."""
        code = """
def test_func():
    value = os.getenv('KEY')
    return value
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert agent._check_env_access(func_node) is True

    def test_check_env_access_without_env(self, agent):
        """Test function without environment access."""
        code = """
def test_func(param):
    return param * 2
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert agent._check_env_access(func_node) is False

    def test_find_external_calls_requests(self, agent):
        """Test finding requests library calls."""
        code = """
def fetch_data():
    response = requests.get('http://api.example.com')
    data = requests.post('http://api.example.com', json={})
    return response
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        calls = agent._find_external_calls(func_node)
        assert "requests.get" in calls
        assert "requests.post" in calls

    def test_find_external_calls_httpx(self, agent):
        """Test finding httpx library calls."""
        code = """
def fetch_data():
    client = httpx.Client()
    response = httpx.get('http://api.example.com')
    return response
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        calls = agent._find_external_calls(func_node)
        assert "httpx.get" in calls

    def test_find_external_calls_none(self, agent):
        """Test function without external calls."""
        code = """
def calculate(x, y):
    return x + y
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        calls = agent._find_external_calls(func_node)
        assert len(calls) == 0

    def test_analyze_source_structure(self, agent):
        """Test analyzing Python source structure."""
        agent.current_source = """
class Calculator:
    def __init__(self):
        self.value = 0

    def add(self, x):
        self.value += x

    def multiply(self, x):
        self.value *= x

    @staticmethod
    def square(x):
        return x * x
"""
        classes = agent._analyze_source_structure()
        assert len(classes) == 1
        assert classes[0].name == "Calculator"
        assert len(classes[0].functions) == 4

        # Check function details
        func_names = [f.name for f in classes[0].functions]
        assert "__init__" in func_names
        assert "add" in func_names
        assert "multiply" in func_names
        assert "square" in func_names

        # Check static method detection
        square_func = next(f for f in classes[0].functions if f.name == "square")
        assert square_func.is_static is True

        # Check constructor detection
        init_func = next(f for f in classes[0].functions if f.name == "__init__")
        assert init_func.is_constructor is True

    def test_validate_syntax_valid(self, agent):
        """Test syntax validation with valid code."""
        agent.current_source = """
def test():
    return 42
"""
        assert agent._validate_syntax() is True

    def test_validate_syntax_invalid(self, agent):
        """Test syntax validation with invalid code."""
        agent.current_source = """
def test()
    return 42
"""
        assert agent._validate_syntax() is False

    def test_validate_service_class_created(self, agent):
        """Test validation of service class creation."""
        agent.current_source = """
class TestService:
    def __init__(self):
        pass

    def execute(self):
        return True

class OriginalClass:
    def __init__(self):
        self.service = TestService()
"""
        assert agent._validate_service_class_created("TestService") is True
        assert agent._validate_service_class_created("NonExistentService") is False

    def test_validate_no_env_access_passing(self, agent):
        """Test environment access validation - passing case."""
        agent.current_source = """
class ConfigService:
    def __init__(self, api_key):
        self.api_key = api_key

    def get_config(self):
        return self.api_key
"""
        assert agent._validate_no_env_access("ConfigService") is True

    def test_validate_no_env_access_failing(self, agent):
        """Test environment access validation - failing case."""
        agent.current_source = """
import os

class ConfigService:
    def __init__(self):
        self.api_key = os.getenv('API_KEY')

    def get_config(self):
        return os.environ['DATABASE_URL']
"""
        assert agent._validate_no_env_access("ConfigService") is False

    def test_validate_interface_usage_passing(self, agent):
        """Test interface usage validation - passing case."""
        agent.current_source = """
class HttpClientInterface:
    def get(self, url):
        raise NotImplementedError

class DataService:
    def __init__(self, http_client: HttpClientInterface):
        self.client = http_client

    def fetch_data(self, url):
        return self.client.get(url)
"""
        assert agent._validate_interface_usage("DataService") is True

    def test_validate_interface_usage_failing(self, agent):
        """Test interface usage validation - failing case."""
        agent.current_source = """
import requests

class DataService:
    def __init__(self):
        self.client = requests

    def fetch_data(self, url):
        return self.client.get(url)
"""
        assert agent._validate_interface_usage("DataService") is False

    def test_record_attempt(self, agent):
        """Test recording a refactoring attempt."""
        agent._record_attempt(
            func_name="test_func",
            service_class_name="TestService",
            success=True,
            errors=[]
        )
        assert len(agent.attempts) == 1
        assert agent.attempts[0].target_function == "test_func"
        assert agent.attempts[0].success is True

    def test_get_failure_history(self, agent):
        """Test getting failure history for a function."""
        # Add some attempts
        agent._record_attempt("func1", "Service1", True, [])
        agent._record_attempt("func2", "Service2", False, ["Error 1"])
        agent._record_attempt("func1", "Service1", False, ["Error 2"])
        agent._record_attempt("func2", "Service2", False, ["Error 3"])

        # Get failure history
        failures = agent._get_failure_history("func2")
        assert len(failures) == 2
        assert all(a.target_function == "func2" for a in failures)
        assert all(not a.success for a in failures)

    def test_build_refactoring_prompt(self, agent):
        """Test building a refactoring prompt."""
        func = FunctionInfo(
            name="process_data",
            lineno=20,
            col_offset=4,
            is_constructor=False,
            is_static=False,
            is_class_method=False,
            has_env_access=True,
            external_calls=["requests.get"],
            body="def process_data(): pass"
        )

        agent.current_source = "class DataProcessor: pass"

        prompt = agent._build_refactoring_prompt(
            func,
            "ProcessDataService",
            []
        )

        assert "process_data" in prompt
        assert "ProcessDataService" in prompt
        assert "DataProcessor" in prompt
        assert "environment variables" in prompt
        assert "requests.get" in prompt

    def test_run_validation_hooks_all_passing(self, agent):
        """Test validation hooks when all pass."""
        agent.current_source = """
class TestService:
    def __init__(self, config):
        self.config = config

    def execute(self):
        return True

class OriginalClass:
    def __init__(self):
        self.service = TestService(config={})

    def test_func(self):
        return self.service.execute()
"""
        func = FunctionInfo(
            name="old_func",
            lineno=10,
            col_offset=4,
            is_constructor=False,
            is_static=False,
            is_class_method=False,
            has_env_access=False,
            external_calls=[],
            body=""
        )

        result = agent._run_validation_hooks(func, "TestService")
        assert result.passed is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_identify_primary_function(self):
        """Test identifying the primary function of a class."""
        # Create a mock response object with content attribute
        mock_response = MagicMock()
        mock_response.content = "process_data"

        fake_service = FakeClaudeService(
            mock_responses=[mock_response]
        )
        agent = RefactoringAgent(claude_service=fake_service)

        class_info = ClassInfo(
            name="DataProcessor",
            lineno=10,
            functions=[
                FunctionInfo("__init__", 11, 4, True, False, False, False, [], ""),
                FunctionInfo("process_data", 15, 4, False, False, False, False, [], ""),
                FunctionInfo("helper", 20, 4, False, False, False, False, [], "")
            ]
        )

        agent.current_source = "class DataProcessor: pass"

        # Need to use the service within its context manager
        async with fake_service as service:
            agent.claude_service = service
            primary = await agent._identify_primary_function(class_info)
            assert primary == "process_data"

    @pytest.mark.asyncio
    async def test_execute_refactoring(self):
        """Test executing refactoring with Claude."""
        refactored_code = """class ProcessDataService:
    def __init__(self):
        pass

    def execute(self):
        return "processed"

class DataProcessor:
    def __init__(self):
        self.service = ProcessDataService()"""

        # Create a mock response object with content attribute
        mock_response = MagicMock()
        mock_response.content = f"```python\n{refactored_code}\n```"

        fake_service = FakeClaudeService(
            mock_responses=[mock_response]
        )
        agent = RefactoringAgent(claude_service=fake_service)

        # Need to use the service within its context manager
        async with fake_service as service:
            agent.claude_service = service
            result = await agent._execute_refactoring("Test prompt")
            assert result == refactored_code

    @pytest.mark.asyncio
    async def test_refactor_file_not_found(self):
        """Test refactoring a non-existent file."""
        agent = RefactoringAgent()
        success = await agent.refactor_file("/nonexistent/file.py")
        assert success is False

    @pytest.mark.asyncio
    async def test_refactor_file_no_classes(self):
        """Test refactoring a file with no classes."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def standalone_func(): return 42")
            temp_file = f.name

        try:
            agent = RefactoringAgent()
            success = await agent.refactor_file(temp_file)
            assert success is True  # No classes to refactor
        finally:
            Path(temp_file).unlink()

    @pytest.mark.asyncio
    async def test_extract_function_to_service_success(self):
        """Test successful function extraction to service."""
        refactored_code = """
class CalculateService:
    def __init__(self):
        pass

    def execute(self, x, y):
        return x + y

class Calculator:
    def __init__(self):
        self.calculate_service = CalculateService()

    def calculate(self, x, y):
        return self.calculate_service.execute(x, y)
"""
        # Create a mock response object with content attribute
        mock_response = MagicMock()
        mock_response.content = f"```python\n{refactored_code}\n```"

        fake_service = FakeClaudeService(
            mock_responses=[mock_response]
        )
        agent = RefactoringAgent(claude_service=fake_service)
        agent.original_source = "class Calculator: pass"
        agent.current_source = agent.original_source

        class_info = ClassInfo(
            name="Calculator",
            lineno=1,
            functions=[]
        )
        func = FunctionInfo(
            name="calculate",
            lineno=5,
            col_offset=4,
            is_constructor=False,
            is_static=False,
            is_class_method=False,
            has_env_access=False,
            external_calls=[],
            body=""
        )

        # Need to use the service within its context manager
        async with fake_service as service:
            agent.claude_service = service
            success = await agent._extract_function_to_service(class_info, func)
            assert success is True
            assert len(agent.attempts) == 1
            assert agent.attempts[0].success is True

    @pytest.mark.asyncio
    async def test_refactor_class_with_primary_function(self):
        """Test refactoring a class with a primary function identified."""
        # Create a mock response object with content attribute
        mock_response = MagicMock()
        mock_response.content = "main_logic"

        fake_service = FakeClaudeService(
            mock_responses=[mock_response]  # Primary function identification
        )
        agent = RefactoringAgent(claude_service=fake_service, max_iterations=1)

        class_info = ClassInfo(
            name="MyClass",
            lineno=1,
            functions=[
                FunctionInfo("__init__", 2, 4, True, False, False, False, [], ""),
                FunctionInfo("main_logic", 5, 4, False, False, False, False, [], ""),
                FunctionInfo("helper", 10, 4, False, False, False, False, [], "")
            ]
        )

        agent.current_source = """
class MyClass:
    def __init__(self):
        pass

    def main_logic(self):
        return "main"

    def helper(self):
        return "help"
"""

        # Need to use the service within its context manager
        async with fake_service as service:
            agent.claude_service = service
            with patch.object(agent, '_extract_function_to_service', return_value=True) as mock_extract:
                await agent._refactor_class(class_info)
                # Should only try to extract 'helper' (not constructor or primary)
                assert mock_extract.called
                extracted_func = mock_extract.call_args[0][1]
                assert extracted_func.name == "helper"


class TestRefactoringAttempt:
    """Test the RefactoringAttempt dataclass."""

    def test_refactoring_attempt_creation(self):
        """Test creating a RefactoringAttempt."""
        attempt = RefactoringAttempt(
            iteration=1,
            target_function="test_func",
            service_class_name="TestService",
            success=False,
            validation_errors=["Error 1", "Error 2"],
            changes_made=["Change 1"]
        )
        assert attempt.iteration == 1
        assert attempt.target_function == "test_func"
        assert not attempt.success
        assert len(attempt.validation_errors) == 2


class TestMainFunction:
    """Test the main function and CLI parsing."""

    @pytest.mark.asyncio
    async def test_main_with_missing_file(self):
        """Test main function with missing file argument."""
        with patch('sys.argv', ['refactoring_agent.py']):
            with pytest.raises(SystemExit):
                from refactoring_agent import main
                await main()

    @pytest.mark.asyncio
    async def test_main_with_nonexistent_file(self):
        """Test main function with non-existent file."""
        with patch('sys.argv', ['refactoring_agent.py', '/nonexistent.py']):
            with pytest.raises(SystemExit) as exc_info:
                from refactoring_agent import main
                await main()
            assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_main_with_valid_file(self):
        """Test main function with a valid file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("class Test: pass")
            temp_file = f.name

        try:
            # Create a fake service for testing
            fake_service = FakeClaudeService(mock_responses=[])

            with patch('sys.argv', ['refactoring_agent.py', temp_file]):
                with patch('refactoring_agent.RefactoringAgent.refactor_file', return_value=True):
                    with patch('sys.exit') as mock_exit:
                        from refactoring_agent import main
                        await main(claude_service=fake_service)
                        mock_exit.assert_called_once_with(0)
        finally:
            Path(temp_file).unlink()