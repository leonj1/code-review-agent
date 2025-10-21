# Test Fixer Agent Team

A team of specialized AI agents that work together to fix failing Python tests through automated refactoring.

## Overview

This script implements a multi-agent system using the Claude Agent SDK. The team consists of three specialized agents that work in sequence:

1. **IdentifyFailingTests Agent** - Parses pytest output and identifies failing tests
2. **RefactorAgent** - Analyzes and refactors functions to make them more testable
3. **SummaryAgent** - Generates concise summaries following "The Elements of Style"

## Architecture

### Agent Workflow

```
┌─────────────────────┐
│   Run make test     │
│   Capture Output    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ IdentifyFailingTests│
│      Agent          │
│                     │
│ - Parse pytest      │
│ - Extract failures  │
│ - Create models     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  RefactorAgent      │
│  with Hooks         │
│                     │
│ - Analyze function  │
│ - Run validation    │
│ - Refactor code     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  SummaryAgent       │
│                     │
│ - Summarize changes │
│ - Display results   │
└─────────────────────┘
```

## Pydantic Models

The system uses strongly-typed Pydantic models to ensure data consistency across agents:

### FailingTest
Represents a single failing test with detailed information:
- `test_file`: Path to the test file
- `test_name`: Full qualified test name
- `test_class`: Optional test class name
- `test_method`: Test method name
- `error_type`: Type of error (AssertionError, etc.)
- `error_message`: Error message
- `traceback`: Full traceback
- `line_number`: Line number where test failed

### TestRunResult
Captures the complete test execution results:
- `exit_code`: Exit code from test runner
- `total_tests`: Total number of tests
- `passed_tests`: Number of passing tests
- `failed_tests`: Number of failing tests
- `failures`: List of FailingTest models
- `stdout`/`stderr`: Test output

### ValidationIssue
Represents a validation hook result:
- `hook_name`: Name of the validation hook
- `passed`: Boolean indicating pass/fail
- `message`: Validation message
- `severity`: "error" or "warning"

### RefactoringResult
Contains the outcome of a refactoring operation:
- `function_name`: Name of refactored function
- `file_path`: Source file path
- `success`: Whether refactoring succeeded
- `validation_issues`: List of validation results
- `changes_summary`: Summary of changes
- `refactored_code`: The new code (if successful)

### RefactoringSummary
Final summary following Elements of Style:
- `total_tests_fixed`: Count of tests fixed
- `total_refactorings`: Total refactoring attempts
- `successful_refactorings`: Successful attempts
- `summary_text`: Concise prose summary

## RefactorAgent Validation Hooks

The RefactorAgent implements comprehensive validation hooks that run both before and after refactoring:

### Pre-Refactoring Hooks

1. **max_function_length** - Validates function does not exceed 30 lines
2. **no_env_access** - Ensures no direct `os.environ` or `os.getenv()` calls
3. **no_client_creation** - Verifies no HTTP/database client instantiation
4. **typed_arguments** - Checks arguments use specific types, not `Any`
5. **typed_return** - Validates return type annotation exists
6. **no_default_arguments** - Ensures no default parameter values

### Post-Refactoring Hooks

The same validation hooks run after refactoring to verify compliance.

### Validation Details

#### Hook: Function Length ≤ 30 Lines
**Purpose**: Keep functions focused and testable

**Fails When**:
```python
def complex_function():  # 50 lines
    # Too much logic
    # Hard to test
    # Difficult to maintain
```

**Passes When**:
```python
def focused_function():  # 20 lines
    # Single responsibility
    # Easy to test
```

#### Hook: No Environment Variable Access
**Purpose**: Make functions deterministic and testable

**Fails When**:
```python
def get_api_key():
    return os.environ['API_KEY']  # Direct env access
```

**Passes When**:
```python
def get_api_key(api_key: str):  # Passed as argument
    return api_key
```

#### Hook: No Client Creation
**Purpose**: Enable dependency injection for testing

**Fails When**:
```python
def fetch_data(url: str):
    client = requests.Session()  # Creates client
    return client.get(url)
```

**Passes When**:
```python
def fetch_data(url: str, client: HttpClient):  # Client injected
    return client.get(url)
```

#### Hook: Typed Arguments (Not Any)
**Purpose**: Provide type safety and clear contracts

**Fails When**:
```python
def process(data):  # No type hint
    pass

def process(data: Any):  # Generic Any type
    pass
```

**Passes When**:
```python
from pydantic import BaseModel

class RequestData(BaseModel):
    id: int
    name: str

def process(data: RequestData):  # Specific type
    pass
```

#### Hook: Typed Return
**Purpose**: Document and enforce return value contracts

**Fails When**:
```python
def calculate():  # No return type
    return 42
```

**Passes When**:
```python
from pydantic import BaseModel

class CalculationResult(BaseModel):
    value: int
    timestamp: float

def calculate() -> CalculationResult:
    return CalculationResult(value=42, timestamp=time.time())
```

#### Hook: No Default Arguments
**Purpose**: Make dependencies explicit, easier to test

**Fails When**:
```python
def __init__(self, db_host: str = "localhost"):  # Has default
    self.db_host = db_host
```

**Passes When**:
```python
def __init__(self, db_host: str):  # Required argument
    self.db_host = db_host
```

#### Hook: Interface-Based Dependencies
**Purpose**: Use interfaces instead of concrete implementations

**Fails When**:
```python
def __init__(self, client: requests.Session):  # Concrete class
    self.client = client
```

**Passes When**:
```python
from abc import ABC, abstractmethod

class HttpClient(ABC):
    @abstractmethod
    def get(self, url: str) -> Response:
        pass

def __init__(self, client: HttpClient):  # Interface
    self.client = client
```

#### Hook: Unit Test Runs Successfully
**Purpose**: Ensure refactoring doesn't break tests

The agent runs the specific unit test independently to verify it passes after refactoring.

## SummaryAgent - Elements of Style

The SummaryAgent follows principles from "The Elements of Style" by Strunk & White:

### Principles Applied

1. **Omit Needless Words**
   - Avoids verbose phrases
   - Gets to the point quickly
   - Example: "Fixed 3 issues" not "Successfully completed the fixing of 3 issues"

2. **Use Active Voice**
   - "Completed 5 refactorings" not "5 refactorings were completed"
   - "Addressed failing tests" not "Failing tests were addressed"

3. **Put Statements in Positive Form**
   - States what was done, not what wasn't
   - "Improved dependency injection" over "Did not create clients"

4. **Use Specific, Concrete Language**
   - "Reduced function complexity" over "Made improvements"
   - Provides exact numbers: "Fixed 3 of 5 tests"

### Example Summary Output

```
Addressed 3 of 5 failing tests. Completed 3 refactorings successfully.
Key improvements: reduced function complexity, removed environment
dependencies, and improved dependency injection.
```

## Usage

### Basic Usage

```bash
python src/test_fixer_agent_team.py
```

### With Options

```bash
# Dry run (no file modifications)
python src/test_fixer_agent_team.py --dry-run

# Verbose output
python src/test_fixer_agent_team.py --verbose

# Specify Claude model
python src/test_fixer_agent_team.py --model opus

# Combine options
python src/test_fixer_agent_team.py --dry-run --verbose --model sonnet
```

### Options

- `--dry-run`: Analyze and show changes without modifying files
- `--verbose`: Show detailed output from all agents
- `--model`: Choose Claude model (`sonnet`, `opus`, `haiku`)

## Example Output

```
╭──────────────────────────────────────────────────╮
│  Test Fixer Agent Team                           │
│                                                  │
│  Orchestrating three specialized agents:         │
│  1. IdentifyFailingTests - Parse test output     │
│  2. RefactorAgent - Improve code testability     │
│  3. SummaryAgent - Summarize changes             │
╰──────────────────────────────────────────────────╯

Step 1: Running Tests
Running tests with 'make test'...

Step 2: Identifying Failing Tests

Parsing 3 failing tests...

┌─────────────────────────────────────────────────┐
│              Failing Tests                      │
├──────────────┬──────────────┬──────────┬────────┤
│ Test File    │ Test Name    │ Error    │ Message│
├──────────────┼──────────────┼──────────┼────────┤
│ tests/test.py│ test_login  │ Assert   │ ...    │
└──────────────┴──────────────┴──────────┴────────┘

Step 3: Refactoring Functions

Analyzing test: test_login

┌─────────────────────────────────────────────────┐
│          Validation Results                     │
├──────────────┬──────────────┬──────────────────┤
│ Hook         │ Status       │ Message          │
├──────────────┼──────────────┼──────────────────┤
│ max_function │ ✗ FAILED     │ Function has 45  │
│              │              │ lines, exceeds 30│
├──────────────┼──────────────┼──────────────────┤
│ no_env_access│ ✗ FAILED     │ Function reads   │
│              │              │ from environment │
└──────────────┴──────────────┴──────────────────┘

Step 4: Generating Summary

╭──────────────────────────────────────────────────╮
│         Refactoring Summary                      │
│                                                  │
│  Addressed 3 of 3 failing tests. Completed 3    │
│  refactorings successfully. Key improvements:    │
│  reduced function complexity and removed         │
│  environment dependencies.                       │
╰──────────────────────────────────────────────────╯

╭──────────────────────────────────────────────────╮
│            Statistics                            │
│                                                  │
│  Tests Fixed: 3                                  │
│  Total Refactorings: 3                           │
│  Successful: 3                                   │
│  Success Rate: 100.0%                            │
╰──────────────────────────────────────────────────╯
```

## Implementation Details

### Function: run_tests()

Executes `make test` and captures output:
- Uses `subprocess.run()` with 5-minute timeout
- Captures both stdout and stderr
- Parses pytest output for test counts
- Returns `TestRunResult` model

### IdentifyFailingTestsAgent

**Purpose**: Parse pytest output and extract failing test information

**Key Methods**:
- `parse_test_output()`: Main parsing logic
- `_display_failures()`: Rich table display

**Parsing Strategy**:
1. Find FAILED lines matching pattern: `tests/file.py::Class::method FAILED`
2. Extract test file, class, and method names
3. Locate failure details in output
4. Extract error type, message, and traceback
5. Create `FailingTest` model for each failure

### RefactorAgentWithHooks

**Purpose**: Analyze functions and refactor for better testability

**Key Methods**:
- `analyze_and_refactor()`: Main entry point
- `_identify_function_under_test()`: Map test to source function
- `_find_source_file()`: Locate source file from test file
- `_analyze_function()`: Parse function with AST
- `_run_validation_hooks()`: Execute all validation checks
- `_refactor_with_claude()`: AI-powered refactoring (placeholder)

**AST Analysis**:
Uses Python's `ast` module to:
- Parse source code into abstract syntax tree
- Walk the tree to find function definitions
- Analyze function characteristics (length, calls, types)
- Check for environment access and client creation

### SummaryAgent

**Purpose**: Generate concise, well-written summaries

**Key Methods**:
- `generate_summary()`: Create summary from results
- `_describe_improvements()`: Convert technical terms to prose
- `display_summary()`: Rich panel display

**Writing Style**:
- Active voice: "Completed" not "Was completed"
- Concrete: "3 tests" not "some tests"
- Positive: "Improved" not "Fixed problems"
- Concise: Remove unnecessary words

## Extension Points

### Adding New Validation Hooks

To add a new validation hook:

1. Add check in `_analyze_function()`:
```python
def _analyze_function(self, source_code: str, function_name: str):
    # ... existing checks ...
    has_docstring = self._check_has_docstring(node)
    return {
        # ... existing fields ...
        'has_docstring': has_docstring
    }
```

2. Add validation in `_run_validation_hooks()`:
```python
def _run_validation_hooks(self, function_info, source_code):
    # ... existing hooks ...

    # Hook: Has docstring
    if not function_info['has_docstring']:
        issues.append(ValidationIssue(
            hook_name="has_docstring",
            passed=False,
            message="Function missing docstring"
        ))
```

### Integrating Real Claude SDK

Replace the placeholder in `_refactor_with_claude()`:

```python
async def _refactor_with_claude(self, function_info, source_code, validation_issues, claude_service):
    # Build prompt
    prompt = self._build_refactoring_prompt(function_info, validation_issues)

    # Use Claude SDK
    options = ClaudeAgentOptions(model="sonnet", allowed_tools=["Read", "Write"])
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)

        refactored_code = ""
        async for message in client.receive_response():
            # Extract refactored code from response
            refactored_code += self._extract_code(message)

    return refactored_code
```

### Processing All Failing Tests

Modify the main loop:

```python
# Current: Process only first test
if failing_tests:
    result = await refactor_agent.analyze_and_refactor(failing_tests[0], None)
    refactoring_results.append(result)

# Modified: Process all tests
for failing_test in failing_tests:
    result = await refactor_agent.analyze_and_refactor(failing_test, None)
    refactoring_results.append(result)
```

## Testing the Agent Team

### Test with Passing Tests

```bash
# All tests should pass currently
python src/test_fixer_agent_team.py
# Expected: "All tests passing! No refactoring needed."
```

### Test with Dry Run

```bash
python src/test_fixer_agent_team.py --dry-run
# Expected: Analysis runs but no files modified
```

### Test Individual Components

```python
# Test IdentifyFailingTestsAgent
from test_fixer_agent_team import IdentifyFailingTestsAgent, TestRunResult

agent = IdentifyFailingTestsAgent(Console())
test_result = TestRunResult(
    exit_code=1,
    total_tests=10,
    passed_tests=7,
    failed_tests=3,
    stdout="...",  # Paste pytest output
    stderr=""
)
failures = agent.parse_test_output(test_result)
```

## Dependencies

Required packages (already in requirements.txt):
- `claude-agent-sdk` - Claude Agent SDK for AI integration
- `pydantic` - Data validation and models
- `rich` - Terminal formatting and display
- `python-dotenv` - Environment variable management

## Best Practices

### When Using the Agent Team

1. **Start with dry-run**: Always test with `--dry-run` first
2. **Review validation issues**: Check what needs fixing before refactoring
3. **One test at a time**: Current implementation processes one test - good for careful refactoring
4. **Commit before running**: Ensure you can revert changes if needed
5. **Review refactored code**: AI suggestions should be reviewed before committing

### Validation Hook Guidelines

1. **Keep hooks focused**: Each hook should check one thing
2. **Provide clear messages**: Explain what's wrong and why
3. **Use severity levels**: Distinguish errors from warnings
4. **Make them independent**: Hooks shouldn't depend on each other
5. **Test hooks separately**: Ensure each hook works correctly

### Summary Writing Guidelines

1. **Lead with impact**: Start with most important information
2. **Use numbers**: Quantify results when possible
3. **Be specific**: Name actual improvements, not generic terms
4. **Stay concise**: Aim for 2-3 sentences maximum
5. **Active voice**: Make it clear who did what

## Troubleshooting

### "All tests passing! No refactoring needed."

This is expected when all tests pass. To test the agents:
1. Temporarily modify a test to make it fail
2. Run the agent team
3. Revert the changes

### "Could not parse any failing tests from output"

The pytest output format may have changed. Check:
1. Run `make test` manually to see output format
2. Update regex patterns in `parse_test_output()` if needed

### "Function not found in source code"

Check file mapping conventions:
- Test file: `tests/test_module.py`
- Source file: `src/module.py`

Update `_find_source_file()` if your project uses different conventions.

### Import Errors

Ensure all dependencies are installed:
```bash
venv/bin/pip install -r requirements.txt
```

## Future Enhancements

1. **Parallel Processing**: Process multiple tests concurrently
2. **Learning from History**: Remember successful refactoring patterns
3. **Interactive Mode**: Ask user for guidance on ambiguous cases
4. **Test Generation**: Generate new tests after refactoring
5. **Metrics Dashboard**: Track refactoring success rates over time
6. **Integration Tests**: Validate end-to-end functionality after changes
7. **Code Review**: Add agent to review refactored code before committing
8. **Rollback Support**: Automatically revert if tests still fail

## References

- [Claude Agent SDK Documentation](https://docs.claude.com/en/api/agent-sdk)
- [The Elements of Style - Strunk & White](https://www.gutenberg.org/ebooks/37134)
- [Python AST Module](https://docs.python.org/3/library/ast.html)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [pytest Documentation](https://docs.pytest.org/)
