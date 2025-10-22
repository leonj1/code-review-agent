#!/usr/bin/env python3
"""
Test that run_tests() captures both stdout and stderr.

Some test frameworks output failure information to stderr instead of stdout.
This test validates that both are captured and combined.
"""

import unittest
from unittest.mock import patch, MagicMock
import subprocess


class TestRunTestsCapturesStdoutAndStderr(unittest.TestCase):
    """Test that run_tests() properly captures both stdout and stderr."""

    @patch('subprocess.run')
    def test_captures_stdout_only(self, mock_run):
        """Test when failures are in stdout."""
        # Simulate test output in stdout only
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = """
======================================================================
FAIL: test_example (test_module.TestClass.test_example)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_module.py", line 42, in test_example
    self.assertEqual(1, 2)
AssertionError: 1 != 2

1 failed, 5 passed in 0.5s
"""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Import here to avoid module loading issues
        from src.test_fixer_agent_team import run_tests

        result = run_tests()

        # Verify stdout contains the failure
        self.assertIn("FAIL: test_example", result.stdout)
        self.assertIn("AssertionError", result.stdout)
        self.assertEqual(result.failed_tests, 1)

    @patch('subprocess.run')
    def test_captures_stderr_only(self, mock_run):
        """Test when failures are in stderr."""
        # Simulate test output in stderr only
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "1 failed, 5 passed in 0.5s"
        mock_result.stderr = """
======================================================================
FAIL: test_example (test_module.TestClass.test_example)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_module.py", line 42, in test_example
    self.assertEqual(1, 2)
AssertionError: 1 != 2
"""
        mock_run.return_value = mock_result

        from src.test_fixer_agent_team import run_tests

        result = run_tests()

        # Verify combined output contains the failure
        self.assertIn("FAIL: test_example", result.stdout)
        self.assertIn("AssertionError", result.stdout)
        self.assertEqual(result.failed_tests, 1)

    @patch('subprocess.run')
    def test_captures_both_stdout_and_stderr(self, mock_run):
        """Test when output is split between stdout and stderr."""
        # Simulate test output split between stdout and stderr
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = """
tests/test_module.py::test_example FAILED
1 failed, 5 passed in 0.5s
"""
        mock_result.stderr = """
======================================================================
FAIL: test_example (test_module.TestClass.test_example)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_module.py", line 42, in test_example
    self.assertEqual(1, 2)
AssertionError: 1 != 2
"""
        mock_run.return_value = mock_result

        from src.test_fixer_agent_team import run_tests

        result = run_tests()

        # Verify combined output contains both parts
        self.assertIn("tests/test_module.py::test_example FAILED", result.stdout)
        self.assertIn("FAIL: test_example", result.stdout)
        self.assertIn("AssertionError", result.stdout)
        self.assertEqual(result.failed_tests, 1)

    @patch('subprocess.run')
    def test_combined_output_order(self, mock_run):
        """Test that stdout comes before stderr in combined output."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "STDOUT_CONTENT"
        mock_result.stderr = "STDERR_CONTENT"
        mock_run.return_value = mock_result

        from src.test_fixer_agent_team import run_tests

        result = run_tests()

        # Verify order: stdout should come before stderr
        stdout_pos = result.stdout.find("STDOUT_CONTENT")
        stderr_pos = result.stdout.find("STDERR_CONTENT")

        self.assertNotEqual(stdout_pos, -1, "stdout content should be present")
        self.assertNotEqual(stderr_pos, -1, "stderr content should be present")
        self.assertLess(stdout_pos, stderr_pos, "stdout should come before stderr")


class TestParseTestOutputWithCombinedOutput(unittest.TestCase):
    """Test that IdentifyFailingTestsAgent can parse failures from combined output."""

    def test_parses_failures_from_stderr_content(self):
        """Test parsing when failure details are in what was originally stderr."""
        from src.test_fixer_agent_team import IdentifyFailingTestsAgent, TestRunResult
        from rich.console import Console

        # Simulate combined output where failures were originally in stderr
        combined_output = """
tests run summary here
======================================================================
FAIL: test_log_filter (test_logging.TestLogging.test_log_filter)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_logging.py", line 100, in test_log_filter
    self.assertIn("expected", output)
AssertionError: 'expected' not found in ''
"""

        test_result = TestRunResult(
            exit_code=1,
            total_tests=10,
            passed_tests=9,
            failed_tests=1,
            stdout=combined_output,  # Now contains both stdout and stderr
            stderr=""
        )

        console = Console(quiet=True)
        agent = IdentifyFailingTestsAgent(console)
        failures = agent.parse_test_output(test_result)

        # Should successfully parse the failure
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0].test_method, "test_log_filter")
        self.assertEqual(failures[0].line_number, 100)


if __name__ == '__main__':
    unittest.main()
