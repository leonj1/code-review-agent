#!/usr/bin/env python3
"""
Demo script showing how to use parse_unittest_failures function.

This demonstrates parsing unittest test output and extracting detailed
information about each failing test.
"""

from src.parse_unittest_failures import parse_unittest_failures


def main():
    """Run demonstration of parse_unittest_failures."""

    # Example unittest output with multiple failures
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
FAIL: test_get_or_create_account_returns_existing (test_fake_account_category_client.TestFakeAccountCategoryClient.test_get_or_create_account_returns_existing)
Test that get_or_create returns existing account.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_fake_account_category_client.py", line 40, in test_get_or_create_account_returns_existing
    self.assertEqual(account2.display_name, self.test_display_name)
AssertionError: 'Different Name' != 'Test User'
"""

    print("=" * 80)
    print("DEMO: Parsing Unittest Failures")
    print("=" * 80)
    print()

    # Parse the test output
    failures = parse_unittest_failures(test_output)

    print(f"Found {len(failures)} failing test(s)\n")

    # Display detailed information about each failure
    for i, failure in enumerate(failures, 1):
        print(f"Failure #{i}")
        print("-" * 80)
        print(f"  Test Name:    {failure.test_name}")
        print(f"  Test Method:  {failure.test_method}")
        print(f"  Test Class:   {failure.test_class}")
        print(f"  File:         {failure.test_file}")
        print(f"  Line Number:  {failure.line_number}")
        print(f"  Error Type:   {failure.error_type}")
        print(f"  Error Msg:    {failure.error_message}")
        print()
        print("  Traceback (first 200 chars):")
        print(f"  {failure.traceback[:200]}...")
        print()

    # Example: Filter by error type
    print("=" * 80)
    print("Example: Filter by Error Type")
    print("=" * 80)
    print()

    assertion_errors = [f for f in failures if f.error_type == "AssertionError"]
    print(f"Found {len(assertion_errors)} AssertionError(s):")
    for failure in assertion_errors:
        print(f"  - {failure.test_method} ({failure.test_file}:{failure.line_number})")

    print()

    # Example: Group by test file
    print("=" * 80)
    print("Example: Group by Test File")
    print("=" * 80)
    print()

    from collections import defaultdict
    by_file = defaultdict(list)
    for failure in failures:
        by_file[failure.test_file].append(failure)

    for file_path, file_failures in by_file.items():
        print(f"{file_path}: {len(file_failures)} failure(s)")
        for failure in file_failures:
            print(f"  - {failure.test_method} (line {failure.line_number})")
        print()

    # Example: Return as dictionary for JSON export
    print("=" * 80)
    print("Example: Export as Dictionary (for JSON)")
    print("=" * 80)
    print()

    failures_dict = [
        {
            'test_name': f.test_name,
            'test_method': f.test_method,
            'test_class': f.test_class,
            'file': f.test_file,
            'line': f.line_number,
            'error_type': f.error_type,
            'error_message': f.error_message
        }
        for f in failures
    ]

    import json
    print(json.dumps(failures_dict, indent=2))


if __name__ == '__main__':
    main()
