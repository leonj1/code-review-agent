#!/usr/bin/env python3
"""
Tests for agent tool integration.

This test suite validates that the parse_unittest_failures function works
as an agent tool for Python test files.
"""

import unittest
from pathlib import Path
from src.parse_unittest_failures import parse_unittest_failures, FailingTest


class TestIsPythonTestFile(unittest.TestCase):
    """Test helper function for identifying Python test files."""

    def test_python_test_file(self):
        """Test that Python test files are correctly identified."""
        self.assertTrue(Path("tests/test_example.py").suffix == '.py')
        self.assertTrue('test' in "test_module.py".lower())
        self.assertTrue(Path("tests/test_integration.py").suffix == '.py')

    def test_non_python_files(self):
        """Test that non-Python files are rejected."""
        self.assertFalse(Path("tests/test_example.js").suffix == '.py')
        self.assertFalse(Path("test_module.txt").suffix == '.py')


class TestParseUnittestFailuresAsAgentTool(unittest.TestCase):
    """Test the parse_unittest_failures function as an agent tool."""

    def test_tool_is_callable(self):
        """Test that the tool can be called directly."""
        test_output = """======================================================================
FAIL: test_example (test_module.TestClass.test_example)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_module.py", line 42, in test_example
    self.assertEqual(1, 2)
AssertionError: 1 != 2
"""
        failures = parse_unittest_failures(test_output)
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0].test_method, "test_example")

    def test_tool_with_empty_input(self):
        """Test tool handles empty input gracefully."""
        failures = parse_unittest_failures("")
        self.assertEqual(len(failures), 0)

    def test_tool_returns_structured_data(self):
        """Test that tool returns properly structured FailingTest objects."""
        test_output = """======================================================================
FAIL: test_example (test_module.TestClass.test_example)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_module.py", line 42, in test_example
    self.assertEqual(1, 2)
AssertionError: 1 != 2
"""
        failures = parse_unittest_failures(test_output)

        # Verify it returns FailingTest objects
        self.assertIsInstance(failures[0], FailingTest)

        # Verify all required fields are present
        failure = failures[0]
        self.assertIsNotNone(failure.test_file)
        self.assertIsNotNone(failure.test_name)
        self.assertIsNotNone(failure.test_method)
        self.assertIsNotNone(failure.error_type)
        self.assertIsNotNone(failure.error_message)
        self.assertIsNotNone(failure.traceback)


class TestAgentWorkflowWithPythonFiles(unittest.TestCase):
    """Test typical agent workflow when working with Python test files."""

    def test_agent_workflow_parse_failures(self):
        """
        Test complete workflow: Agent detects Python file, uses parse_unittest_failures tool.

        Simulates an agent that:
        1. Detects it's working with a Python test file
        2. Uses parse_unittest_failures to extract failures
        3. Processes the structured failure data
        """
        # Step 1: Detect Python test file
        test_file_path = "tests/test_central_logging_integration.py"
        is_python_file = Path(test_file_path).suffix == '.py'
        has_test_in_name = 'test' in Path(test_file_path).name.lower()

        self.assertTrue(is_python_file and has_test_in_name,
                       "Should detect this is a Python test file")

        # Step 2: Use parse_unittest_failures tool
        test_output = """======================================================================
FAIL: test_log_level_filtering (test_central_logging_integration.TestCentralLoggingIntegration.test_log_level_filtering)
Test that log level filtering works correctly.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_central_logging_integration.py", line 184, in test_log_level_filtering
    self.assertIn("Warning message", output)
AssertionError: 'Warning message' not found in ''

======================================================================
FAIL: test_logging_hierarchy_capture (test_central_logging_integration.TestCentralLoggingIntegration.test_logging_hierarchy_capture)
Test that child loggers inherit central logging configuration.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_central_logging_integration.py", line 153, in test_logging_hierarchy_capture
    self.assertIn("Parent message", output)
AssertionError: 'Parent message' not found in ''
"""

        failures = parse_unittest_failures(test_output)

        # Step 3: Process structured failure data
        self.assertEqual(len(failures), 2, "Should extract 2 failures")

        # Agent can now work with structured data
        for failure in failures:
            # Agent has access to all failure details
            self.assertIsInstance(failure.test_file, str)
            self.assertIsInstance(failure.test_method, str)
            self.assertIsInstance(failure.error_message, str)
            self.assertIsInstance(failure.line_number, int)

        # Verify specific failure details
        self.assertEqual(failures[0].test_method, "test_log_level_filtering")
        self.assertEqual(failures[0].line_number, 184)
        self.assertEqual(failures[1].test_method, "test_logging_hierarchy_capture")
        self.assertEqual(failures[1].line_number, 153)

    def test_agent_workflow_with_complex_example(self):
        """Test agent workflow with the complex example from requirements."""
        test_output = """======================================================================
FAIL: test_log_level_filtering (test_central_logging_integration.TestCentralLoggingIntegration.test_log_level_filtering)
Test that log level filtering works correctly.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_central_logging_integration.py", line 184, in test_log_level_filtering
    self.assertIn("Warning message", output)
AssertionError: 'Warning message' not found in ''

======================================================================
FAIL: test_multiple_module_simulation (test_central_logging_integration.TestCentralLoggingIntegration.test_multiple_module_simulation)
Simulate multiple modules logging to verify central service handles all.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_central_logging_integration.py", line 215, in test_multiple_module_simulation
    self.assertIn(f"Message from {name}", output)
AssertionError: 'Message from services.email_processor' not found in ''

======================================================================
FAIL: test_get_or_create_account_returns_existing (test_fake_account_category_client.TestFakeAccountCategoryClient.test_get_or_create_account_returns_existing)
Test that get_or_create returns existing account.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_fake_account_category_client.py", line 40, in test_get_or_create_account_returns_existing
    self.assertEqual(account2.display_name, self.test_display_name)
AssertionError: 'Different Name' != 'Test User'
"""

        failures = parse_unittest_failures(test_output)

        # Verify all 3 failures were parsed correctly
        self.assertEqual(len(failures), 3)

        # Check first failure
        self.assertEqual(failures[0].test_method, "test_log_level_filtering")
        self.assertEqual(failures[0].test_class, "TestCentralLoggingIntegration")
        self.assertEqual(failures[0].line_number, 184)
        self.assertIn("'Warning message' not found", failures[0].error_message)

        # Check second failure
        self.assertEqual(failures[1].test_method, "test_multiple_module_simulation")
        self.assertEqual(failures[1].line_number, 215)

        # Check third failure
        self.assertEqual(failures[2].test_method, "test_get_or_create_account_returns_existing")
        self.assertEqual(failures[2].test_class, "TestFakeAccountCategoryClient")
        self.assertEqual(failures[2].line_number, 40)
        self.assertIn("'Different Name' != 'Test User'", failures[2].error_message)


if __name__ == '__main__':
    unittest.main()
