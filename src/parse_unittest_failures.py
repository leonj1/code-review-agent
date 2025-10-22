#!/usr/bin/env python3
"""
Standalone module for parsing unittest-style test failures.

This module provides a function to parse unittest test output and extract
detailed information about each failing test.
"""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FailingTest:
    """Model representing a single failing test."""
    test_file: str
    test_name: str
    test_class: Optional[str]
    test_method: str
    error_type: str
    error_message: str
    traceback: str
    line_number: Optional[int]


def parse_unittest_failures(test_output: str) -> List[FailingTest]:
    """
    Parse unittest-style test output and extract failing tests with their errors.

    This function handles output from Python's unittest framework, which uses
    the format:
        ======================================================================
        FAIL: test_name (test_module.TestClass.test_name)
        Test description
        ----------------------------------------------------------------------
        Traceback (most recent call last):
          File "...", line X, in test_name
            ...
        AssertionError: error message

    Args:
        test_output: Raw output from unittest test runner

    Returns:
        List of FailingTest objects with parsed information

    Examples:
        >>> output = '''
        ... ======================================================================
        ... FAIL: test_example (test_module.TestClass.test_example)
        ... Test description
        ... ----------------------------------------------------------------------
        ... Traceback (most recent call last):
        ...   File "/app/tests/test_module.py", line 42, in test_example
        ...     self.assertEqual(1, 2)
        ... AssertionError: 1 != 2
        ... '''
        >>> failures = parse_unittest_failures(output)
        >>> len(failures)
        1
        >>> failures[0].test_name
        'test_module.TestClass.test_example'
    """
    failures = []

    # Split output into individual failure blocks
    # Pattern: ====== FAIL: ... followed by content until next ====== or end
    failure_blocks = re.split(r'={70,}\n', test_output)

    for block in failure_blocks:
        if not block.strip() or not block.startswith('FAIL:'):
            continue

        # Parse the header line: FAIL: test_method (full.test.path)
        header_match = re.match(
            r'FAIL:\s+(\w+)\s+\(([^)]+)\)',
            block
        )

        if not header_match:
            continue

        test_method = header_match.group(1)
        full_test_path = header_match.group(2)

        # Extract test class and full name
        # Format: test_module.TestClass.test_method
        path_parts = full_test_path.split('.')
        if len(path_parts) >= 3:
            # Has module.Class.method
            test_class = path_parts[-2]
            test_name = full_test_path
        elif len(path_parts) == 2:
            # Has module.method (no class)
            test_class = None
            test_name = full_test_path
        else:
            # Just method name
            test_class = None
            test_name = test_method

        # Extract test file path from traceback
        # Pattern: File "/path/to/file.py", line X, in test_method
        file_match = re.search(
            r'File\s+"([^"]+)",\s+line\s+(\d+),\s+in\s+\w+',
            block
        )

        test_file = file_match.group(1) if file_match else "unknown"
        line_number = int(file_match.group(2)) if file_match else None

        # Extract error type and message
        # Pattern: ErrorType: error message
        error_match = re.search(
            r'(\w+Error):\s*(.+?)(?:\n|$)',
            block,
            re.MULTILINE
        )

        if error_match:
            error_type = error_match.group(1)
            error_message = error_match.group(2).strip()
        else:
            error_type = "Unknown"
            error_message = "Test failed"

        # Extract full traceback (everything after the dashed line)
        traceback_match = re.search(
            r'-{70,}\n(.+)',
            block,
            re.DOTALL
        )

        traceback = traceback_match.group(1).strip() if traceback_match else block

        failures.append(FailingTest(
            test_file=test_file,
            test_name=test_name,
            test_class=test_class,
            test_method=test_method,
            error_type=error_type,
            error_message=error_message,
            traceback=traceback,
            line_number=line_number
        ))

    return failures


if __name__ == '__main__':
    # Example usage
    import sys

    if len(sys.argv) > 1:
        # Read from file
        with open(sys.argv[1], 'r') as f:
            output = f.read()
    else:
        # Read from stdin
        output = sys.stdin.read()

    failures = parse_unittest_failures(output)

    print(f"Found {len(failures)} failing test(s):\n")

    for i, failure in enumerate(failures, 1):
        print(f"{i}. {failure.test_name}")
        print(f"   File: {failure.test_file}:{failure.line_number}")
        print(f"   Error: {failure.error_type}: {failure.error_message}")
        print()
