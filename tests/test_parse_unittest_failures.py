#!/usr/bin/env python3
"""
Tests for parse_unittest_failures function.

This test suite validates the function that parses unittest-style test output
and extracts failing tests with their associated errors.
"""

import unittest
from src.parse_unittest_failures import parse_unittest_failures, FailingTest


class TestParseUnittestFailures(unittest.TestCase):
    """Test suite for parse_unittest_failures function."""

    def test_parse_single_failure(self):
        """Test parsing a single failing test."""
        test_output = """======================================================================
FAIL: test_log_level_filtering (test_central_logging_integration.TestCentralLoggingIntegration.test_log_level_filtering)
Test that log level filtering works correctly.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_central_logging_integration.py", line 184, in test_log_level_filtering
    self.assertIn("Warning message", output)
AssertionError: 'Warning message' not found in ''
"""

        failures = parse_unittest_failures(test_output)

        self.assertEqual(len(failures), 1)

        failure = failures[0]
        self.assertEqual(failure.test_method, "test_log_level_filtering")
        self.assertEqual(
            failure.test_name,
            "test_central_logging_integration.TestCentralLoggingIntegration.test_log_level_filtering"
        )
        self.assertEqual(failure.test_class, "TestCentralLoggingIntegration")
        self.assertEqual(failure.test_file, "/app/tests/test_central_logging_integration.py")
        self.assertEqual(failure.line_number, 184)
        self.assertEqual(failure.error_type, "AssertionError")
        self.assertEqual(failure.error_message, "'Warning message' not found in ''")
        self.assertIn("Traceback", failure.traceback)

    def test_parse_multiple_failures(self):
        """Test parsing multiple failing tests."""
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

======================================================================
FAIL: test_multiple_module_simulation (test_central_logging_integration.TestCentralLoggingIntegration.test_multiple_module_simulation)
Simulate multiple modules logging to verify central service handles all.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_central_logging_integration.py", line 215, in test_multiple_module_simulation
    self.assertIn(f"Message from {name}", output)
AssertionError: 'Message from services.email_processor' not found in ''
"""

        failures = parse_unittest_failures(test_output)

        self.assertEqual(len(failures), 3)

        # Verify first failure
        self.assertEqual(failures[0].test_method, "test_log_level_filtering")
        self.assertEqual(failures[0].line_number, 184)

        # Verify second failure
        self.assertEqual(failures[1].test_method, "test_logging_hierarchy_capture")
        self.assertEqual(failures[1].line_number, 153)

        # Verify third failure
        self.assertEqual(failures[2].test_method, "test_multiple_module_simulation")
        self.assertEqual(failures[2].line_number, 215)

    def test_parse_example_from_requirements(self):
        """Test parsing the exact example provided in requirements."""
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

======================================================================
FAIL: test_multiple_module_simulation (test_central_logging_integration.TestCentralLoggingIntegration.test_multiple_module_simulation)
Simulate multiple modules logging to verify central service handles all.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_central_logging_integration.py", line 215, in test_multiple_module_simulation
    self.assertIn(f"Message from {name}", output)
AssertionError: 'Message from services.email_processor' not found in ''

======================================================================
FAIL: test_third_party_library_capture (test_central_logging_integration.TestCentralLoggingIntegration.test_third_party_library_capture)
Test that third-party library logs are captured.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_central_logging_integration.py", line 92, in test_third_party_library_capture
    self.assertIn("Starting new HTTPS connection", output)
AssertionError: 'Starting new HTTPS connection' not found in ''

======================================================================
FAIL: test_get_or_create_account_returns_existing (test_fake_account_category_client.TestFakeAccountCategoryClient.test_get_or_create_account_returns_existing)
Test that get_or_create returns existing account.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_fake_account_category_client.py", line 40, in test_get_or_create_account_returns_existing
    self.assertEqual(account2.display_name, self.test_display_name)
AssertionError: 'Different Name' != 'Test User'"""

        failures = parse_unittest_failures(test_output)

        self.assertEqual(len(failures), 5)

        # Test 1: test_log_level_filtering
        self.assertEqual(failures[0].test_method, "test_log_level_filtering")
        self.assertEqual(failures[0].test_class, "TestCentralLoggingIntegration")
        self.assertEqual(failures[0].test_file, "/app/tests/test_central_logging_integration.py")
        self.assertEqual(failures[0].line_number, 184)
        self.assertEqual(failures[0].error_type, "AssertionError")
        self.assertIn("'Warning message' not found", failures[0].error_message)

        # Test 2: test_logging_hierarchy_capture
        self.assertEqual(failures[1].test_method, "test_logging_hierarchy_capture")
        self.assertEqual(failures[1].line_number, 153)
        self.assertIn("'Parent message' not found", failures[1].error_message)

        # Test 3: test_multiple_module_simulation
        self.assertEqual(failures[2].test_method, "test_multiple_module_simulation")
        self.assertEqual(failures[2].line_number, 215)
        self.assertIn("'Message from services.email_processor' not found", failures[2].error_message)

        # Test 4: test_third_party_library_capture
        self.assertEqual(failures[3].test_method, "test_third_party_library_capture")
        self.assertEqual(failures[3].line_number, 92)
        self.assertIn("'Starting new HTTPS connection' not found", failures[3].error_message)

        # Test 5: test_get_or_create_account_returns_existing
        self.assertEqual(failures[4].test_method, "test_get_or_create_account_returns_existing")
        self.assertEqual(failures[4].test_class, "TestFakeAccountCategoryClient")
        self.assertEqual(failures[4].test_file, "/app/tests/test_fake_account_category_client.py")
        self.assertEqual(failures[4].line_number, 40)
        self.assertEqual(failures[4].error_message, "'Different Name' != 'Test User'")

    def test_parse_empty_output(self):
        """Test parsing empty output returns empty list."""
        failures = parse_unittest_failures("")
        self.assertEqual(len(failures), 0)

    def test_parse_no_failures(self):
        """Test parsing output with no failures."""
        test_output = """
----------------------------------------------------------------------
Ran 10 tests in 0.234s

OK
"""
        failures = parse_unittest_failures(test_output)
        self.assertEqual(len(failures), 0)

    def test_parse_different_error_types(self):
        """Test parsing different error types (not just AssertionError)."""
        test_output = """======================================================================
FAIL: test_value_error (test_module.TestClass.test_value_error)
Test that ValueError is raised.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_module.py", line 50, in test_value_error
    raise ValueError("Invalid value")
ValueError: Invalid value

======================================================================
FAIL: test_type_error (test_module.TestClass.test_type_error)
Test that TypeError is raised.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_module.py", line 60, in test_type_error
    int("not a number")
TypeError: int() argument must be a string or a number
"""

        failures = parse_unittest_failures(test_output)

        self.assertEqual(len(failures), 2)
        self.assertEqual(failures[0].error_type, "ValueError")
        self.assertEqual(failures[0].error_message, "Invalid value")
        self.assertEqual(failures[1].error_type, "TypeError")
        self.assertIn("int() argument must be a string", failures[1].error_message)

    def test_parse_test_without_class(self):
        """Test parsing a test that's not in a class."""
        test_output = """======================================================================
FAIL: test_standalone_function (test_module.test_standalone_function)
Test standalone function.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_module.py", line 10, in test_standalone_function
    self.assertEqual(1, 2)
AssertionError: 1 != 2
"""

        failures = parse_unittest_failures(test_output)

        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0].test_method, "test_standalone_function")
        self.assertIsNone(failures[0].test_class)
        self.assertEqual(failures[0].test_name, "test_module.test_standalone_function")

    def test_traceback_captured(self):
        """Test that full traceback is captured."""
        test_output = """======================================================================
FAIL: test_complex_failure (test_module.TestClass.test_complex_failure)
Test with complex traceback.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_module.py", line 100, in test_complex_failure
    result = self.helper_method()
  File "/app/tests/test_module.py", line 110, in helper_method
    return self.another_method()
  File "/app/tests/test_module.py", line 120, in another_method
    self.assertEqual(expected, actual)
AssertionError: Expected value != Actual value
"""

        failures = parse_unittest_failures(test_output)

        self.assertEqual(len(failures), 1)
        traceback = failures[0].traceback

        # Verify all parts of traceback are captured
        self.assertIn("helper_method", traceback)
        self.assertIn("another_method", traceback)
        self.assertIn("line 100", traceback)
        self.assertIn("line 110", traceback)
        self.assertIn("line 120", traceback)

    def test_parse_with_extra_whitespace(self):
        """Test parsing handles extra whitespace gracefully."""
        test_output = """

======================================================================
FAIL: test_example (test_module.TestClass.test_example)
Test description
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_module.py", line 42, in test_example
    self.assertEqual(1, 2)
AssertionError: 1 != 2


"""

        failures = parse_unittest_failures(test_output)

        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0].test_method, "test_example")

    def test_parse_multiline_error_message(self):
        """Test parsing error messages that span multiple lines."""
        test_output = """======================================================================
FAIL: test_multiline_error (test_module.TestClass.test_multiline_error)
Test with multiline error.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_module.py", line 75, in test_multiline_error
    self.assertEqual(expected_dict, actual_dict)
AssertionError: {'key1': 'value1', 'key2': 'value2'} != {'key1': 'different', 'key2': 'values'}
"""

        failures = parse_unittest_failures(test_output)

        self.assertEqual(len(failures), 1)
        # Should capture at least the first line of the error
        self.assertIn("{'key1':", failures[0].error_message)

    def test_all_fields_populated(self):
        """Test that all FailingTest fields are properly populated."""
        test_output = """======================================================================
FAIL: test_complete (test_module.TestClass.test_complete)
Complete test case.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_module.py", line 123, in test_complete
    self.assertTrue(False)
AssertionError: False is not true
"""

        failures = parse_unittest_failures(test_output)

        self.assertEqual(len(failures), 1)
        failure = failures[0]

        # Verify all fields are populated
        self.assertIsNotNone(failure.test_file)
        self.assertIsNotNone(failure.test_name)
        self.assertIsNotNone(failure.test_class)
        self.assertIsNotNone(failure.test_method)
        self.assertIsNotNone(failure.error_type)
        self.assertIsNotNone(failure.error_message)
        self.assertIsNotNone(failure.traceback)
        self.assertIsNotNone(failure.line_number)

        # Verify field types
        self.assertIsInstance(failure.test_file, str)
        self.assertIsInstance(failure.test_name, str)
        self.assertIsInstance(failure.test_method, str)
        self.assertIsInstance(failure.error_type, str)
        self.assertIsInstance(failure.error_message, str)
        self.assertIsInstance(failure.traceback, str)
        self.assertIsInstance(failure.line_number, int)


class TestParseUnittestFailuresEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_malformed_header(self):
        """Test handling of malformed test headers."""
        test_output = """======================================================================
FAIL: malformed header without parentheses
----------------------------------------------------------------------
Some error occurred
"""

        failures = parse_unittest_failures(test_output)
        # Should gracefully skip malformed entries
        self.assertEqual(len(failures), 0)

    def test_missing_file_path(self):
        """Test handling when file path is missing from traceback."""
        test_output = """======================================================================
FAIL: test_no_file (test_module.TestClass.test_no_file)
Test without file path.
----------------------------------------------------------------------
Traceback (most recent call last):
  Some error without file path
AssertionError: Something went wrong
"""

        failures = parse_unittest_failures(test_output)

        self.assertEqual(len(failures), 1)
        # Should use "unknown" for missing file
        self.assertEqual(failures[0].test_file, "unknown")
        self.assertIsNone(failures[0].line_number)

    def test_unicode_in_error_message(self):
        """Test handling of unicode characters in error messages."""
        test_output = """======================================================================
FAIL: test_unicode (test_module.TestClass.test_unicode)
Test with unicode.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_module.py", line 50, in test_unicode
    self.assertEqual("café", "cafe")
AssertionError: 'café' != 'cafe'
"""

        failures = parse_unittest_failures(test_output)

        self.assertEqual(len(failures), 1)
        self.assertIn("café", failures[0].error_message)


if __name__ == '__main__':
    unittest.main()
