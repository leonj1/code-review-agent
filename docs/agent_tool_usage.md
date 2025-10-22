# Agent Tool Usage: parse_unittest_failures

## Overview

The `parse_unittest_failures` function has been integrated into `test_fixer_agent_team.py` as an **agent tool**. When the agent determines it's working with Python test files, it automatically uses this tool to extract structured information about failing tests.

## How It Works

### 1. Tool Definition

The function is decorated with `@tool` in `test_fixer_agent_team.py`:

```python
@tool
def parse_unittest_failures(test_output: str) -> List[FailingTest]:
    """
    Parse Python unittest test output and extract failing tests with their errors.

    **When to use this tool:**
    - When working with Python test files (*.py)
    - After running 'make test' or 'python -m unittest' or 'pytest'
    - To extract structured information about test failures
    - To identify which tests are failing and why
    ...
    """
```

### 2. Agent Detection Logic

The `IdentifyFailingTestsAgent` automatically detects when to use the tool:

```python
def parse_test_output(self, test_result: TestRunResult) -> List[FailingTest]:
    # Check if this is Python unittest/pytest output
    is_unittest_format = '=' * 70 in stdout and 'FAIL:' in stdout
    is_pytest_format = '::' in stdout and 'FAILED' in stdout and '.py' in stdout

    if is_unittest_format:
        # Use the parse_unittest_failures tool
        failures = parse_unittest_failures(stdout)
        return failures
```

### 3. File Type Detection

A helper tool `is_python_test_file` is provided to check if a file is a Python test file:

```python
@tool
def is_python_test_file(file_path: str) -> bool:
    """Check if a file is a Python test file."""
    path = Path(file_path)
    return path.suffix == '.py' and 'test' in path.name.lower()
```

## Agent Workflow

When the agent encounters test failures:

```
┌─────────────────────────────────────────┐
│ 1. Agent runs 'make test'               │
│    - Captures test output               │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 2. Agent detects file type              │
│    - Checks for .py extension           │
│    - Looks for 'test' in filename       │
│    - Examines output format             │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 3. Agent uses parse_unittest_failures   │
│    - If unittest format detected        │
│    - Passes test output to tool         │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 4. Tool returns structured data         │
│    - List of FailingTest objects        │
│    - Each with file, line, error, etc.  │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 5. Agent processes failures             │
│    - Analyzes each failure              │
│    - Plans refactoring strategy         │
│    - Applies fixes                      │
└─────────────────────────────────────────┘
```

## When the Tool is Used

The agent automatically uses `parse_unittest_failures` when:

✅ **Working with Python files** (`.py` extension)
✅ **Unittest output detected** (contains `======` and `FAIL:`)
✅ **Test failures present** (exit code != 0)

The agent **does NOT** use this tool when:

❌ Working with non-Python files (JavaScript, Go, etc.)
❌ Pytest-style output (uses alternative parser)
❌ All tests passing (no failures to parse)

## Tool Benefits

### 1. Structured Data Access

Instead of parsing text manually, agents get structured `FailingTest` objects:

```python
failure = FailingTest(
    test_file="/app/tests/test_module.py",
    test_name="test_module.TestClass.test_method",
    test_class="TestClass",
    test_method="test_method",
    error_type="AssertionError",
    error_message="'expected' != 'actual'",
    traceback="Traceback (most recent call last)...",
    line_number=42
)

# Agent can now easily access:
failure.test_file        # "/app/tests/test_module.py"
failure.line_number      # 42
failure.error_message    # "'expected' != 'actual'"
```

### 2. Accurate Parsing

The tool uses regex patterns specifically designed for unittest output:

- Extracts test class and method names correctly
- Parses error types and messages accurately
- Captures line numbers from tracebacks
- Handles multiple failures in one output

### 3. Consistency

All agents use the same parsing logic, ensuring consistent behavior across:

- `IdentifyFailingTestsAgent`
- `RefactorAgent`
- `SummaryAgent`

## Example Usage

### Example 1: Basic Agent Workflow

```python
# Agent detects Python test file
if is_python_test_file("tests/test_example.py"):
    # Run tests
    output = run_command("make test")

    # Use tool to parse failures
    failures = parse_unittest_failures(output)

    # Process each failure
    for failure in failures:
        print(f"Fix needed: {failure.test_name}")
        print(f"  Location: {failure.test_file}:{failure.line_number}")
        print(f"  Error: {failure.error_message}")
```

### Example 2: Complex Failure Parsing

Given this unittest output:

```
======================================================================
FAIL: test_log_level_filtering (test_central_logging_integration.TestCentralLoggingIntegration.test_log_level_filtering)
Test that log level filtering works correctly.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tests/test_central_logging_integration.py", line 184, in test_log_level_filtering
    self.assertIn("Warning message", output)
AssertionError: 'Warning message' not found in ''
```

The tool extracts:

```python
FailingTest(
    test_file='/app/tests/test_central_logging_integration.py',
    test_name='test_central_logging_integration.TestCentralLoggingIntegration.test_log_level_filtering',
    test_class='TestCentralLoggingIntegration',
    test_method='test_log_level_filtering',
    error_type='AssertionError',
    error_message="'Warning message' not found in ''",
    traceback='Traceback (most recent call last)...',
    line_number=184
)
```

## Integration Points

### In test_fixer_agent_team.py

```python
# Line 168-210: Tool definition
@tool
def parse_unittest_failures(test_output: str) -> List[FailingTest]:
    ...

# Line 336-368: Agent integration
class IdentifyFailingTestsAgent:
    def parse_test_output(self, test_result: TestRunResult) -> List[FailingTest]:
        if is_unittest_format:
            failures = parse_unittest_failures(stdout)
            return failures
```

### Standalone Module

The core parsing logic is also available as a standalone module in `src/parse_unittest_failures.py` for:

- Command-line usage
- Direct imports
- Testing
- Other tools

## Testing

The integration is validated by:

1. **Unit tests** (`tests/test_parse_unittest_failures.py`) - 14 tests
2. **Integration tests** (`tests/test_agent_tool_integration.py`) - 7 tests
3. **Demo script** (`examples/demo_parse_failures.py`)

Run tests:

```bash
make test
# or
python3 -m pytest tests/test_agent_tool_integration.py -v
```

All 21 tests pass, validating:
- Tool is callable as expected
- Returns structured data correctly
- Handles edge cases gracefully
- Works in agent workflows

## Future Enhancements

Potential improvements:

1. **Multi-format support**: Add pytest-specific parsing
2. **Performance**: Cache parsing results for repeated calls
3. **Filtering**: Add parameters to filter by error type or file
4. **Suggestions**: Include fix suggestions in returned data
5. **Metrics**: Track parsing success rates and patterns

## See Also

- [parse_unittest_failures.md](./parse_unittest_failures.md) - Function documentation
- [Agent Architecture](./agent_architecture.md) - Overall agent design
- [Tool Development Guide](./tool_development.md) - Creating new agent tools
