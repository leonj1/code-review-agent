# Comprehensive Test Plan for RefactoringAgent

## Current Test Coverage: 77% (33 tests)

## Test Categories

### 1. Unit Tests - Data Classes ✅ (Completed)

#### FunctionInfo Tests
- [x] test_function_info_creation - Basic creation
- [x] test_function_info_with_env_access - Function with environment variable access
- [ ] test_function_info_with_multiple_external_calls - Multiple API calls
- [ ] test_function_info_equality - Equality comparison
- [ ] test_function_info_as_dict - Serialization

#### ClassInfo Tests
- [x] test_class_info_creation - Basic creation
- [ ] test_class_info_with_no_functions - Empty class
- [ ] test_class_info_with_nested_classes - Nested class structures
- [ ] test_class_info_with_inheritance - Class with parent classes

#### RefactoringAttempt Tests
- [x] test_refactoring_attempt_creation - Basic creation
- [ ] test_refactoring_attempt_with_complex_errors - Multiple validation errors
- [ ] test_refactoring_attempt_serialization - JSON serialization

#### ValidationResult Tests
- [x] test_validation_result_passed - Passing validation
- [x] test_validation_result_failed - Failed validation
- [ ] test_validation_result_with_warnings_only - Only warnings, no errors
- [ ] test_validation_result_aggregation - Combining multiple results

### 2. Unit Tests - Core Functionality

#### Agent Initialization
- [x] test_agent_initialization - Basic initialization
- [ ] test_agent_initialization_with_all_params - All parameters set
- [ ] test_agent_initialization_with_invalid_model - Invalid model name
- [ ] test_agent_initialization_with_custom_console - Custom Rich console

#### Source Analysis (_analyze_source_structure)
- [x] test_analyze_source_structure - Basic class analysis
- [ ] test_analyze_empty_file - Empty Python file
- [ ] test_analyze_module_level_functions - Functions outside classes
- [ ] test_analyze_nested_classes - Classes within classes
- [ ] test_analyze_abstract_classes - ABC and abstract methods
- [ ] test_analyze_dataclasses - @dataclass decorated classes
- [ ] test_analyze_multiple_inheritance - Classes with multiple parents
- [ ] test_analyze_property_decorators - @property methods
- [ ] test_analyze_async_functions - async def methods
- [ ] test_analyze_generators - Generator functions
- [ ] test_analyze_class_with_metaclass - Metaclass usage
- [ ] test_analyze_syntax_error - File with syntax errors

#### Environment Access Detection (_check_env_access)
- [x] test_check_env_access_with_os_environ - os.environ usage
- [x] test_check_env_access_with_os_getenv - os.getenv usage
- [x] test_check_env_access_without_env - No environment access
- [ ] test_check_env_access_with_dotenv - python-dotenv usage
- [ ] test_check_env_access_with_environs - environs library
- [ ] test_check_env_access_in_nested_functions - Nested function env access
- [ ] test_check_env_access_in_comprehensions - List/dict comprehensions
- [ ] test_check_env_access_in_lambda - Lambda functions
- [ ] test_check_env_access_indirect - Via variable assignment

#### External Calls Detection (_find_external_calls)
- [x] test_find_external_calls_requests - requests library
- [x] test_find_external_calls_httpx - httpx library
- [x] test_find_external_calls_none - No external calls
- [ ] test_find_external_calls_urllib - urllib usage
- [ ] test_find_external_calls_aiohttp - aiohttp async calls
- [ ] test_find_external_calls_boto3 - AWS SDK calls
- [ ] test_find_external_calls_database - Database connections
- [ ] test_find_external_calls_grpc - gRPC calls
- [ ] test_find_external_calls_graphql - GraphQL queries
- [ ] test_find_external_calls_websocket - WebSocket connections
- [ ] test_find_external_calls_mixed - Multiple types of calls

#### Primary Function Identification (_identify_primary_function)
- [x] test_identify_primary_function - Basic identification
- [ ] test_identify_primary_function_no_clear_primary - Ambiguous case
- [ ] test_identify_primary_function_only_constructor - Only __init__
- [ ] test_identify_primary_function_with_main_method - Explicit main()
- [ ] test_identify_primary_function_with_execute_pattern - execute/run methods
- [ ] test_identify_primary_function_with_complex_logic - Most complex method
- [ ] test_identify_primary_function_claude_service_error - Service failure

#### Refactoring Prompt Building (_build_refactoring_prompt)
- [x] test_build_refactoring_prompt - Basic prompt
- [ ] test_build_refactoring_prompt_with_env_warning - Environment variable warning
- [ ] test_build_refactoring_prompt_with_external_calls_warning - External calls warning
- [ ] test_build_refactoring_prompt_with_failure_history - Previous failures included
- [ ] test_build_refactoring_prompt_with_multiple_failures - Multiple failure attempts
- [ ] test_build_refactoring_prompt_for_static_method - Static method extraction
- [ ] test_build_refactoring_prompt_for_class_method - Class method extraction
- [ ] test_build_refactoring_prompt_for_async_function - Async function extraction

#### Refactoring Execution (_execute_refactoring)
- [x] test_execute_refactoring - Basic execution
- [ ] test_execute_refactoring_no_markdown - Plain Python response
- [ ] test_execute_refactoring_invalid_python - Syntax error in response
- [ ] test_execute_refactoring_partial_code - Incomplete response
- [ ] test_execute_refactoring_empty_response - No code returned
- [ ] test_execute_refactoring_multiple_code_blocks - Multiple ```python blocks
- [ ] test_execute_refactoring_service_timeout - Claude timeout

### 3. Validation Hook Tests

#### Service Class Creation (_validate_service_class_created)
- [x] test_validate_service_class_created - Service class exists
- [ ] test_validate_service_class_not_created - Service class missing
- [ ] test_validate_service_class_wrong_name - Different class name
- [ ] test_validate_service_class_malformed - Invalid class structure

#### Function Removal (_validate_function_removed)
- [ ] test_validate_function_removed_completely - Function fully removed
- [ ] test_validate_function_delegated - Function delegates to service
- [ ] test_validate_function_not_removed - Function still has logic
- [ ] test_validate_function_partially_removed - Some logic remains

#### Environment Access (_validate_no_env_access)
- [x] test_validate_no_env_access_passing - No env access in service
- [x] test_validate_no_env_access_failing - Env access in service
- [ ] test_validate_env_access_in_init - Env access in constructor
- [ ] test_validate_env_access_in_method - Env access in methods
- [ ] test_validate_env_access_nested - Nested function env access

#### Interface Usage (_validate_interface_usage)
- [x] test_validate_interface_usage_passing - Uses interfaces
- [x] test_validate_interface_usage_failing - Uses concrete implementations
- [ ] test_validate_interface_http_client - HTTP client interface
- [ ] test_validate_interface_database - Database interface
- [ ] test_validate_interface_multiple_clients - Multiple client types

#### Syntax Validation (_validate_syntax)
- [x] test_validate_syntax_valid - Valid Python syntax
- [x] test_validate_syntax_invalid - Invalid Python syntax
- [ ] test_validate_syntax_indentation_error - Indentation issues
- [ ] test_validate_syntax_unclosed_brackets - Bracket mismatch

#### Combined Validation (_run_validation_hooks)
- [x] test_run_validation_hooks_all_passing - All hooks pass
- [ ] test_run_validation_hooks_one_failing - Single hook failure
- [ ] test_run_validation_hooks_multiple_failing - Multiple failures
- [ ] test_run_validation_hooks_with_warnings - Warnings but passing

### 4. Function Extraction Tests

#### Extract Function to Service (_extract_function_to_service)
- [x] test_extract_function_to_service_success - Successful extraction
- [ ] test_extract_function_to_service_first_failure - First attempt fails
- [ ] test_extract_function_to_service_retry_success - Succeeds on retry
- [ ] test_extract_function_to_service_max_retries - Fails after 3 attempts
- [ ] test_extract_function_with_dependencies - Function with dependencies
- [ ] test_extract_function_with_class_attributes - Uses self attributes
- [ ] test_extract_function_with_decorators - Decorated functions
- [ ] test_extract_async_function - Async function extraction

### 5. Class Refactoring Tests (_refactor_class)

- [x] test_refactor_class_with_primary_function - Primary function identified
- [ ] test_refactor_class_no_functions_to_extract - Only constructor and primary
- [ ] test_refactor_class_multiple_functions - Multiple extractions
- [ ] test_refactor_class_max_iterations_reached - Hits iteration limit
- [ ] test_refactor_class_partial_success - Some functions fail
- [ ] test_refactor_class_with_inheritance - Inherited methods
- [ ] test_refactor_class_with_mixins - Mixin classes

### 6. File Refactoring Tests (refactor_file)

- [x] test_refactor_file_not_found - File doesn't exist
- [x] test_refactor_file_no_classes - No classes in file
- [ ] test_refactor_file_single_class - One class to refactor
- [ ] test_refactor_file_multiple_classes - Multiple classes
- [ ] test_refactor_file_read_error - Permission denied
- [ ] test_refactor_file_write_error - Cannot write result
- [ ] test_refactor_file_dry_run - Dry run mode
- [ ] test_refactor_file_backup_creation - Creates backup
- [ ] test_refactor_file_service_initialization_error - Claude service fails

### 7. Attempt Tracking Tests

#### Record Attempt (_record_attempt)
- [x] test_record_attempt - Basic recording
- [ ] test_record_multiple_attempts - Multiple attempts
- [ ] test_record_attempt_with_detailed_errors - Complex error details
- [ ] test_record_attempt_changes_made - Track changes

#### Get Failure History (_get_failure_history)
- [x] test_get_failure_history - Get failures for function
- [ ] test_get_failure_history_empty - No failures
- [ ] test_get_failure_history_multiple_functions - Mixed functions
- [ ] test_get_failure_history_max_attempts - After max attempts

### 8. Output and Reporting Tests

#### Print Summary (print_summary)
- [ ] test_print_summary_empty - No attempts
- [ ] test_print_summary_all_success - All successful
- [ ] test_print_summary_all_failed - All failed
- [ ] test_print_summary_mixed_results - Mixed success/failure
- [ ] test_print_summary_with_long_errors - Truncated errors

### 9. Integration Tests

#### End-to-End Scenarios
- [ ] test_e2e_simple_class - Simple class refactoring
- [ ] test_e2e_complex_class - Complex class with many methods
- [ ] test_e2e_with_env_vars - Class using environment variables
- [ ] test_e2e_with_external_apis - Class making API calls
- [ ] test_e2e_with_database - Database operations
- [ ] test_e2e_with_file_io - File operations
- [ ] test_e2e_with_async_operations - Async/await usage
- [ ] test_e2e_with_threading - Threading/multiprocessing
- [ ] test_e2e_django_model - Django model class
- [ ] test_e2e_flask_view - Flask view class
- [ ] test_e2e_fastapi_endpoint - FastAPI endpoint class

#### Error Recovery
- [ ] test_recovery_from_claude_error - Claude service error
- [ ] test_recovery_from_partial_refactoring - Partial completion
- [ ] test_recovery_from_invalid_response - Invalid Claude response
- [ ] test_recovery_from_network_timeout - Network issues

### 10. CLI and Main Function Tests

- [x] test_main_with_missing_file - No file argument
- [x] test_main_with_nonexistent_file - File not found
- [x] test_main_with_valid_file - Valid file processing
- [ ] test_main_with_all_arguments - All CLI args
- [ ] test_main_with_invalid_model - Invalid model choice
- [ ] test_main_with_verbose_flag - Verbose output
- [ ] test_main_with_dry_run_flag - Dry run mode
- [ ] test_main_with_max_iterations - Custom iteration limit
- [ ] test_main_with_service_injection - Injected service
- [ ] test_main_keyboard_interrupt - Ctrl+C handling

### 11. Edge Cases and Error Handling

#### Malformed Input
- [ ] test_malformed_python_file - Invalid Python syntax
- [ ] test_binary_file_input - Non-text file
- [ ] test_empty_file_input - Zero-byte file
- [ ] test_huge_file_input - Very large file (>10MB)
- [ ] test_circular_dependencies - Circular imports
- [ ] test_encoding_issues - Non-UTF8 encoding

#### Resource Management
- [ ] test_memory_usage_large_file - Memory efficiency
- [ ] test_concurrent_refactoring - Thread safety
- [ ] test_file_lock_handling - Locked files
- [ ] test_temp_file_cleanup - Temporary files cleaned up

### 12. Performance Tests

- [ ] test_performance_small_file - <100 lines
- [ ] test_performance_medium_file - 100-1000 lines
- [ ] test_performance_large_file - >1000 lines
- [ ] test_performance_many_classes - 10+ classes
- [ ] test_performance_many_functions - 50+ functions
- [ ] test_performance_with_retries - Performance with failures

### 13. Compatibility Tests

#### Python Version Compatibility
- [ ] test_python_38_syntax - Python 3.8 features
- [ ] test_python_39_syntax - Python 3.9 features
- [ ] test_python_310_syntax - Python 3.10 features (match, |)
- [ ] test_python_311_syntax - Python 3.11 features
- [ ] test_python_312_syntax - Python 3.12 features

#### Framework Integration
- [ ] test_django_compatibility - Django classes
- [ ] test_flask_compatibility - Flask classes
- [ ] test_fastapi_compatibility - FastAPI classes
- [ ] test_sqlalchemy_compatibility - SQLAlchemy models
- [ ] test_pydantic_compatibility - Pydantic models

### 14. Regression Tests

- [ ] test_regression_issue_001 - (Add as bugs are found)
- [ ] test_regression_issue_002 - (Add as bugs are found)

## Test Metrics Goals

- **Code Coverage**: Target 95%+ coverage
- **Branch Coverage**: Target 90%+ branch coverage
- **Mutation Testing**: Target 80%+ mutation score
- **Performance**: All tests run in < 10 seconds
- **Reliability**: 100% pass rate, no flaky tests

## Test Implementation Priority

### Priority 1 (Critical) - Must Have
1. All validation hook tests
2. Error handling and recovery tests
3. Core refactoring functionality tests
4. File I/O error handling

### Priority 2 (Important) - Should Have
1. Edge case handling
2. Integration tests for common scenarios
3. CLI argument validation
4. Performance tests

### Priority 3 (Nice to Have) - Could Have
1. Framework compatibility tests
2. Python version compatibility
3. Advanced async scenarios
4. Mutation testing

## Test Data Requirements

### Sample Files Needed
1. `simple_class.py` - Basic class with 3-5 methods
2. `complex_class.py` - Class with 10+ methods, inheritance
3. `env_dependent.py` - Class using environment variables
4. `api_client.py` - Class making external API calls
5. `async_class.py` - Class with async methods
6. `django_model.py` - Django model example
7. `malformed.py` - Syntax errors for testing
8. `empty.py` - Empty file
9. `huge_class.py` - Performance testing (1000+ lines)

## Test Utilities Needed

### Helper Functions
```python
def create_temp_python_file(content: str) -> str:
    """Create temporary Python file with content."""

def create_mock_claude_responses(*responses) -> FakeClaudeService:
    """Create fake service with mock responses."""

def assert_file_refactored(original: str, refactored: str):
    """Assert file was properly refactored."""

def assert_service_class_created(source: str, service_name: str):
    """Assert service class exists in source."""

def assert_no_env_access(source: str, class_name: str):
    """Assert no environment access in class."""
```

### Test Fixtures
```python
@pytest.fixture
def simple_class_file():
    """Fixture providing simple class file."""

@pytest.fixture
def mock_claude_service():
    """Fixture providing configured fake Claude service."""

@pytest.fixture
def refactoring_agent():
    """Fixture providing configured RefactoringAgent."""
```

## Continuous Integration Requirements

1. Run tests on every commit
2. Generate coverage reports
3. Fail builds if coverage drops below 90%
4. Run mutation testing weekly
5. Performance regression detection
6. Memory leak detection

## Documentation Requirements

1. Each test must have a clear docstring
2. Complex tests need inline comments
3. Test data files must be documented
4. Performance baselines documented
5. Known limitations documented