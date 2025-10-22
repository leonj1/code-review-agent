# parse_unittest_failures Function

## Overview

The `parse_unittest_failures` function parses unittest-style test output and extracts detailed information about each failing test, returning a structured list of `FailingTest` objects.

## Location

- **Module**: `src/parse_unittest_failures.py`
- **Test Suite**: `tests/test_parse_unittest_failures.py`
- **Demo**: `examples/demo_parse_failures.py`

## Function Signature

```python
def parse_unittest_failures(test_output: str) -> List[FailingTest]
```

## Parameters

- **test_output** (`str`): Raw output from unittest test runner

## Returns

`List[FailingTest]`: A list of `FailingTest` dataclass objects, each containing:

| Field | Type | Description |
|-------|------|-------------|
| `test_file` | `str` | Path to the test file |
| `test_name` | `str` | Full qualified test name (e.g., `module.Class.method`) |
| `test_class` | `Optional[str]` | Test class name (if applicable) |
| `test_method` | `str` | Test method name |
| `error_type` | `str` | Type of error (e.g., `AssertionError`, `ValueError`) |
| `error_message` | `str` | Error message from the failure |
| `traceback` | `str` | Full traceback of the failure |
| `line_number` | `Optional[int]` | Line number where test failed |

## Usage Examples

### Basic Usage

```python
from src.parse_unittest_failures import parse_unittest_failures

# Parse test output
test_output = """======================================================================
FAIL: test_example (test_module.TestClass.test_example)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_module.py", line 42, in test_example
    self.assertEqual(1, 2)
AssertionError: 1 != 2
"""

failures = parse_unittest_failures(test_output)

# Access failure details
for failure in failures:
    print(f"Test: {failure.test_name}")
    print(f"Error: {failure.error_type}: {failure.error_message}")
    print(f"Location: {failure.test_file}:{failure.line_number}")
```

### Command-Line Usage

```bash
# From file
python3 src/parse_unittest_failures.py test_output.txt

# From stdin
make test 2>&1 | python3 src/parse_unittest_failures.py

# From pipeline
python3 -m unittest discover 2>&1 | python3 src/parse_unittest_failures.py
```

### Filter by Error Type

```python
failures = parse_unittest_failures(test_output)

# Get only AssertionErrors
assertion_errors = [f for f in failures if f.error_type == "AssertionError"]

print(f"Found {len(assertion_errors)} assertion failures")
```

### Group by Test File

```python
from collections import defaultdict

failures = parse_unittest_failures(test_output)

# Group failures by file
by_file = defaultdict(list)
for failure in failures:
    by_file[failure.test_file].append(failure)

# Display grouped results
for file_path, file_failures in by_file.items():
    print(f"{file_path}: {len(file_failures)} failure(s)")
    for failure in file_failures:
        print(f"  - {failure.test_method} (line {failure.line_number})")
```

### Export to JSON

```python
import json

failures = parse_unittest_failures(test_output)

# Convert to dictionaries
failures_dict = [
    {
        'test_name': f.test_name,
        'file': f.test_file,
        'line': f.line_number,
        'error_type': f.error_type,
        'error_message': f.error_message
    }
    for f in failures
]

# Export as JSON
print(json.dumps(failures_dict, indent=2))
```

## Supported Test Output Format

The function expects unittest-style output with this format:

```
======================================================================
FAIL: test_method_name (test_module.TestClass.test_method_name)
Test description
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/path/to/test_file.py", line X, in test_method_name
    self.assertSomething(...)
AssertionError: error message
```

## Features

### ✅ Handles Multiple Failures
Parses multiple test failures from a single output string.

### ✅ Extracts Full Traceback
Captures the complete traceback for each failure.

### ✅ Supports Different Error Types
Not limited to `AssertionError` - handles all Python exception types.

### ✅ Graceful Error Handling
- Skips malformed entries
- Uses "unknown" for missing file paths
- Continues parsing even if some blocks are invalid

### ✅ Unicode Support
Handles unicode characters in error messages and tracebacks.

## Test Coverage

The function has comprehensive test coverage (14 tests):

- ✅ Single failure parsing
- ✅ Multiple failures parsing
- ✅ Empty output handling
- ✅ Different error types (ValueError, TypeError, etc.)
- ✅ Tests without classes
- ✅ Complex multi-line tracebacks
- ✅ Extra whitespace handling
- ✅ Multiline error messages
- ✅ All fields populated correctly
- ✅ Malformed header handling
- ✅ Missing file path handling
- ✅ Unicode character support

Run tests with:

```bash
make test
# or
python3 -m pytest tests/test_parse_unittest_failures.py -v
```

## Integration with test_fixer_agent_team.py

This function has been integrated into `src/test_fixer_agent_team.py` and can be used by the agent team for parsing unittest failures.

## Example Output

Given the example test output with 5 failures, the function returns:

```
Found 5 failing test(s):

1. test_central_logging_integration.TestCentralLoggingIntegration.test_log_level_filtering
   File: /app/tests/test_central_logging_integration.py:184
   Error: AssertionError: 'Warning message' not found in ''

2. test_central_logging_integration.TestCentralLoggingIntegration.test_logging_hierarchy_capture
   File: /app/tests/test_central_logging_integration.py:153
   Error: AssertionError: 'Parent message' not found in ''

3. test_central_logging_integration.TestCentralLoggingIntegration.test_multiple_module_simulation
   File: /app/tests/test_central_logging_integration.py:215
   Error: AssertionError: 'Message from services.email_processor' not found in ''

4. test_central_logging_integration.TestCentralLoggingIntegration.test_third_party_library_capture
   File: /app/tests/test_central_logging_integration.py:92
   Error: AssertionError: 'Starting new HTTPS connection' not found in ''

5. test_fake_account_category_client.TestFakeAccountCategoryClient.test_get_or_create_account_returns_existing
   File: /app/tests/test_fake_account_category_client.py:40
   Error: AssertionError: 'Different Name' != 'Test User'
```

## See Also

- Demo script: `examples/demo_parse_failures.py`
- Test suite: `tests/test_parse_unittest_failures.py`
- Integration: `src/test_fixer_agent_team.py`
