"""
Unit tests for the test_fixer module.

These tests verify the test fixing logic without making actual API calls
or running real pytest commands. Uses FakeClaudeService for mocking.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from src.test_fixer import TestFixer, TestResult, FixAttempt
from src.claude_service import FakeClaudeService


class TestTestResult:
    """Tests for the TestResult dataclass."""

    def test_has_failures_true(self):
        """Test has_failures returns True when there are failures."""
        result = TestResult(
            passed=5,
            failed=3,
            total=8,
            failures=["test1 failed", "test2 failed"],
            exit_code=1,
            full_output="output"
        )
        assert result.has_failures() is True

    def test_has_failures_false(self):
        """Test has_failures returns False when all tests pass."""
        result = TestResult(
            passed=8,
            failed=0,
            total=8,
            failures=[],
            exit_code=0,
            full_output="output"
        )
        assert result.has_failures() is False

    def test_is_worse_than_true(self):
        """Test is_worse_than returns True when more failures."""
        worse = TestResult(5, 5, 10, [], 1, "")
        better = TestResult(8, 2, 10, [], 1, "")
        assert worse.is_worse_than(better) is True

    def test_is_worse_than_false(self):
        """Test is_worse_than returns False when fewer failures."""
        better = TestResult(8, 2, 10, [], 1, "")
        worse = TestResult(5, 5, 10, [], 1, "")
        assert better.is_worse_than(worse) is False


class TestTestFixerStoppingConditions:
    """Tests for the stopping condition logic."""

    @pytest.fixture
    def fixer(self):
        """Create a TestFixer instance for testing."""
        fake_service = FakeClaudeService()
        return TestFixer(claude_service=fake_service, max_iterations=5)

    def test_stop_all_tests_passing(self, fixer):
        """Should stop when all tests pass."""
        result = TestResult(10, 0, 10, [], 0, "")
        should_stop, reason = fixer.check_stopping_conditions(1, result, None)

        assert should_stop is True
        assert "All tests passing" in reason

    def test_stop_max_iterations_reached(self, fixer):
        """Should stop when max iterations reached."""
        result = TestResult(5, 5, 10, ["failure"], 1, "")
        should_stop, reason = fixer.check_stopping_conditions(5, result, None)

        assert should_stop is True
        assert "Maximum iterations" in reason

    def test_stop_no_progress_same_failures(self, fixer):
        """Should stop when failures haven't changed."""
        previous = TestResult(5, 5, 10, ["test1::failed", "test2::failed"], 1, "")
        current = TestResult(5, 5, 10, ["test1::failed", "test2::failed"], 1, "")

        should_stop, reason = fixer.check_stopping_conditions(2, current, previous)

        assert should_stop is True
        assert "No progress" in reason

    def test_stop_regression_more_failures(self, fixer):
        """Should stop when more failures appear."""
        previous = TestResult(8, 2, 10, ["test1::failed"], 1, "")
        current = TestResult(5, 5, 10, ["test1::failed", "test2::failed", "test3::failed"], 1, "")

        should_stop, reason = fixer.check_stopping_conditions(2, current, previous)

        assert should_stop is True
        assert "Regression" in reason

    def test_stop_test_count_decreased(self, fixer):
        """Should stop when test count drops significantly."""
        previous = TestResult(8, 2, 10, [], 1, "")
        current = TestResult(5, 2, 7, [], 1, "")  # 3 tests disappeared

        should_stop, reason = fixer.check_stopping_conditions(2, current, previous)

        assert should_stop is True
        assert "Test count decreased" in reason

    def test_continue_making_progress(self, fixer):
        """Should continue when making progress."""
        previous = TestResult(5, 5, 10, ["f1", "f2", "f3", "f4", "f5"], 1, "")
        current = TestResult(7, 3, 10, ["f1", "f2", "f3"], 1, "")  # 2 fewer failures

        should_stop, reason = fixer.check_stopping_conditions(2, current, previous)

        assert should_stop is False
        assert reason == ""

    def test_continue_first_iteration(self, fixer):
        """Should continue on first iteration with failures."""
        current = TestResult(5, 5, 10, ["failure"], 1, "")
        should_stop, reason = fixer.check_stopping_conditions(1, current, None)

        assert should_stop is False


class TestTestFixerExtractFailures:
    """Tests for failure extraction from pytest output."""

    @pytest.fixture
    def fixer(self):
        """Create a TestFixer instance."""
        return TestFixer(claude_service=FakeClaudeService())

    def test_extract_failures_from_pytest_output(self, fixer):
        """Test extracting failures from real pytest output format."""
        output = """
test_main.py::test_one PASSED
test_main.py::test_two FAILED - AssertionError: expected 5, got 3
test_main.py::test_three PASSED
test_utils.py::test_helper FAILED - ValueError: invalid input
"""
        failures = fixer._extract_failures(output)

        assert len(failures) == 2
        assert "test_main.py::test_two" in failures[0]
        assert "test_utils.py::test_helper" in failures[1]

    def test_extract_failures_no_failures(self, fixer):
        """Test extraction when all tests pass."""
        output = """
test_main.py::test_one PASSED
test_main.py::test_two PASSED
"""
        failures = fixer._extract_failures(output)
        assert len(failures) == 0

    def test_extract_failures_assertion_errors(self, fixer):
        """Test extraction of assertion errors."""
        output = """
AssertionError: Expected value to be True
AssertionError: List should have 5 items
"""
        failures = fixer._extract_failures(output)
        assert len(failures) == 2
        assert "Expected value to be True" in failures[0]
        assert "List should have 5 items" in failures[1]


class TestTestFixerAnalysis:
    """Tests for Claude analysis integration."""

    @pytest.mark.asyncio
    async def test_analyze_failures_sends_correct_prompt(self):
        """Test that analysis sends proper prompt to Claude."""
        # Arrange
        mock_responses = [
            Mock(content="Analysis: The test failed because...")
        ]
        fake_service = FakeClaudeService(mock_responses=mock_responses)
        fixer = TestFixer(claude_service=fake_service)

        test_result = TestResult(
            passed=5,
            failed=2,
            total=7,
            failures=["test1::failed - AssertionError", "test2::failed - ValueError"],
            exit_code=1,
            full_output="Full test output here"
        )

        # Act
        async with fake_service as service:
            fixer.claude_service = service
            response = await fixer.analyze_failures_with_claude(test_result)

        # Assert
        queries = fake_service.get_queries()
        assert len(queries) == 1
        prompt = queries[0]

        assert "Total tests: 7" in prompt
        assert "Passed: 5" in prompt
        assert "Failed: 2" in prompt
        assert "test1::failed" in prompt
        assert "test2::failed" in prompt
        assert "Full test output here" in prompt
        assert "root cause" in prompt.lower()

    @pytest.mark.asyncio
    async def test_analyze_failures_returns_response(self):
        """Test that analysis returns Claude's response."""
        # Arrange
        mock_responses = [
            Mock(content="Fix: Change line 42 to use assertEqual")
        ]
        fake_service = FakeClaudeService(mock_responses=mock_responses)
        fixer = TestFixer(claude_service=fake_service)

        test_result = TestResult(5, 1, 6, ["failure"], 1, "output")

        # Act
        async with fake_service as service:
            fixer.claude_service = service
            response = await fixer.analyze_failures_with_claude(test_result)

        # Assert
        assert "Fix: Change line 42" in response
        assert "assertEqual" in response


class TestTestFixerApplyFixes:
    """Tests for applying fixes."""

    @pytest.mark.asyncio
    async def test_apply_fixes_sends_fix_prompt(self):
        """Test that apply_fixes sends correct prompt."""
        # Arrange
        mock_responses = [
            Mock(content="Modified test_main.py")
        ]
        fake_service = FakeClaudeService(mock_responses=mock_responses)
        fixer = TestFixer(claude_service=fake_service)

        analysis = "Fix test1 by changing assertion on line 10"

        # Act
        async with fake_service as service:
            fixer.claude_service = service
            files = await fixer.apply_fixes(analysis)

        # Assert
        queries = fake_service.get_queries()
        assert len(queries) == 1
        assert "apply these fixes" in queries[0].lower()
        assert analysis in queries[0]

    @pytest.mark.asyncio
    async def test_apply_fixes_extracts_modified_files(self):
        """Test that file modifications are extracted correctly."""
        # Arrange
        mock_responses = [
            Mock(content="Modified test_main.py and Updated test_utils.py")
        ]
        fake_service = FakeClaudeService(mock_responses=mock_responses)
        fixer = TestFixer(claude_service=fake_service)

        # Act
        async with fake_service as service:
            fixer.claude_service = service
            files = await fixer.apply_fixes("Fix the tests")

        # Assert
        assert "test_main.py" in files
        assert "test_utils.py" in files

    @pytest.mark.asyncio
    async def test_apply_fixes_no_files_modified(self):
        """Test when no files are modified."""
        # Arrange
        mock_responses = [
            Mock(content="I analyzed the code but cannot apply fixes")
        ]
        fake_service = FakeClaudeService(mock_responses=mock_responses)
        fixer = TestFixer(claude_service=fake_service)

        # Act
        async with fake_service as service:
            fixer.claude_service = service
            files = await fixer.apply_fixes("Fix the tests")

        # Assert
        assert len(files) == 0


class TestTestFixerRunTests:
    """Tests for running tests (mocked)."""

    @pytest.mark.asyncio
    async def test_run_tests_parses_output(self):
        """Test that run_tests correctly parses pytest output."""
        # Arrange
        fake_service = FakeClaudeService()
        fixer = TestFixer(claude_service=fake_service)

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = """
test_main.py::test_one PASSED
test_main.py::test_two FAILED - AssertionError
test_main.py::test_three PASSED
"""
        mock_result.stderr = ""

        # Act
        with patch('subprocess.run', return_value=mock_result):
            result = fixer.run_tests("test_main.py")

        # Assert
        assert result.passed == 2
        assert result.failed == 1
        assert result.total == 3
        assert result.exit_code == 1
        assert len(result.failures) == 1

    @pytest.mark.asyncio
    async def test_run_tests_all_passing(self):
        """Test parsing when all tests pass."""
        # Arrange
        fake_service = FakeClaudeService()
        fixer = TestFixer(claude_service=fake_service)

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = """
test_main.py::test_one PASSED
test_main.py::test_two PASSED
"""
        mock_result.stderr = ""

        # Act
        with patch('subprocess.run', return_value=mock_result):
            result = fixer.run_tests(".")

        # Assert
        assert result.passed == 2
        assert result.failed == 0
        assert result.total == 2
        assert result.exit_code == 0
        assert len(result.failures) == 0


class TestFixAttemptDataclass:
    """Tests for the FixAttempt dataclass."""

    def test_fix_attempt_creation(self):
        """Test creating a FixAttempt."""
        result = TestResult(5, 2, 7, ["f1", "f2"], 1, "output")
        attempt = FixAttempt(
            iteration=1,
            test_result=result,
            fixes_applied=["test_main.py", "test_utils.py"]
        )

        assert attempt.iteration == 1
        assert attempt.test_result.failed == 2
        assert len(attempt.fixes_applied) == 2
        assert "test_main.py" in attempt.fixes_applied


class TestTestFixerIntegration:
    """Integration tests for the full test fixing flow."""

    @pytest.mark.asyncio
    async def test_fix_tests_success_scenario(self):
        """Test the full fix loop when tests eventually pass."""
        # Arrange - Mock responses for analysis, fixes, and continue decision
        mock_responses = [
            Mock(content="Analysis: test failed due to wrong assertion"),
            Mock(content="Modified test_main.py"),
            Mock(content="CONTINUE: Will run tests again to verify the fix"),
        ]
        fake_service = FakeClaudeService(mock_responses=mock_responses)
        fixer = TestFixer(claude_service=fake_service, max_iterations=3)

        # Mock test results: first failing, then passing
        test_results = [
            # First run: failures
            Mock(returncode=1, stdout="test::one FAILED", stderr=""),
            # Second run: all pass
            Mock(returncode=0, stdout="test::one PASSED", stderr=""),
        ]

        # Act
        with patch('subprocess.run', side_effect=test_results):
            success = await fixer.fix_tests("test_main.py")

        # Assert
        assert success is True
        assert len(fixer.fix_history) == 1  # One fix attempt

    @pytest.mark.asyncio
    async def test_fix_tests_max_iterations_scenario(self):
        """Test when max iterations is reached."""
        # Arrange
        mock_responses = [
            Mock(content="Analysis: complex issue"),
            Mock(content="Modified file.py"),
        ] * 5  # Enough for 5 iterations

        fake_service = FakeClaudeService(mock_responses=mock_responses)
        fixer = TestFixer(claude_service=fake_service, max_iterations=2)

        # Mock test results: always failing
        failing_result = Mock(
            returncode=1,
            stdout="test::one FAILED\ntest::two FAILED",
            stderr=""
        )

        # Act
        with patch('subprocess.run', return_value=failing_result):
            success = await fixer.fix_tests(".")

        # Assert
        assert success is False
        assert len(fixer.fix_history) <= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
