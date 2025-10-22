#!/usr/bin/env python3
"""
Test Fixer Agent Team: A team of specialized agents to fix failing Python tests.

This script orchestrates three agents:
1. IdentifyFailingTests: Parses test output and identifies failing tests
2. RefactorAgent: Refactors functions to make them more testable
3. SummaryAgent: Summarizes the changes in adherence with Elements of Style

Usage:
    python test_fixer_agent_team.py [--dry-run] [--verbose]
"""

import argparse
import asyncio
import subprocess
import sys
import re
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AgentDefinition,
    tool,
    create_sdk_mcp_server
)
from cli_tools import print_rich_message, parse_and_print_message


# ============================================================================
# Pydantic Models
# ============================================================================

class FailingTest(BaseModel):
    """Model representing a single failing test."""
    test_file: str = Field(description="Path to the test file")
    test_name: str = Field(description="Full name of the failing test")
    test_class: Optional[str] = Field(None, description="Test class name if applicable")
    test_method: str = Field(description="Test method name")
    error_type: str = Field(description="Type of error (AssertionError, etc.)")
    error_message: str = Field(description="Error message")
    traceback: str = Field(description="Full traceback")
    line_number: Optional[int] = Field(None, description="Line number where test failed")


class TestRunResult(BaseModel):
    """Model representing the result of running tests."""
    exit_code: int = Field(description="Exit code from test runner")
    total_tests: int = Field(description="Total number of tests run")
    passed_tests: int = Field(description="Number of tests that passed")
    failed_tests: int = Field(description="Number of tests that failed")
    failures: List[FailingTest] = Field(default_factory=list, description="List of failing tests")
    stdout: str = Field(description="Standard output from test runner")
    stderr: str = Field(description="Standard error from test runner")


class ValidationIssue(BaseModel):
    """Model representing a validation issue found during refactoring."""
    hook_name: str = Field(description="Name of the validation hook")
    passed: bool = Field(description="Whether validation passed")
    message: str = Field(description="Validation message")
    severity: str = Field(default="error", description="Severity: error or warning")


class RefactoringResult(BaseModel):
    """Model representing the result of refactoring a function."""
    function_name: str = Field(description="Name of the function that was refactored")
    file_path: str = Field(description="Path to the file containing the function")
    success: bool = Field(description="Whether refactoring was successful")
    validation_issues: List[ValidationIssue] = Field(default_factory=list)
    changes_summary: str = Field(description="Summary of changes made")
    refactored_code: Optional[str] = Field(None, description="The refactored code")


class RefactoringSummary(BaseModel):
    """Model representing a concise summary of all refactoring efforts."""
    total_tests_fixed: int = Field(description="Number of tests fixed")
    total_refactorings: int = Field(description="Number of refactoring attempts")
    successful_refactorings: int = Field(description="Number of successful refactorings")
    summary_text: str = Field(description="Concise summary following Elements of Style")


# ============================================================================
# Test Runner Functions
# ============================================================================

def run_tests() -> TestRunResult:
    """
    Run 'make test' and capture its output.

    Returns:
        TestRunResult containing test execution results and output
    """
    console = Console()
    console.print("\n[bold blue]Running tests with 'make test'...[/bold blue]\n")

    try:
        result = subprocess.run(
            ['make', 'test'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Parse pytest output to extract test counts
        # IMPORTANT: Combine stdout and stderr since test frameworks may output to either
        stdout = result.stdout
        stderr = result.stderr
        combined_output = stdout + "\n" + stderr

        total_tests = 0
        passed_tests = 0
        failed_tests = 0

        # Look for pytest summary line like: "89 passed in 2.45s"
        summary_match = re.search(r'(\d+)\s+passed', combined_output)
        if summary_match:
            passed_tests = int(summary_match.group(1))
            total_tests = passed_tests

        # Look for failures
        failure_match = re.search(r'(\d+)\s+failed', combined_output)
        if failure_match:
            failed_tests = int(failure_match.group(1))
            total_tests += failed_tests

        return TestRunResult(
            exit_code=result.returncode,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            stdout=combined_output,  # Store combined output
            stderr=result.stderr
        )

    except subprocess.TimeoutExpired:
        console.print("[bold red]Test execution timed out after 5 minutes[/bold red]")
        return TestRunResult(
            exit_code=-1,
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            stdout="",
            stderr="Test execution timed out"
        )
    except Exception as e:
        console.print(f"[bold red]Error running tests: {e}[/bold red]")
        return TestRunResult(
            exit_code=-1,
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            stdout="",
            stderr=str(e)
        )


# ============================================================================
# Agent Tools
# ============================================================================

def is_python_test_file(file_path: str) -> bool:
    """
    Check if a file is a Python test file.

    **When to use this tool:**
    - To determine if you should use parse_unittest_failures
    - Before parsing test output to ensure it's Python-related
    - To validate file types in test fixing workflows

    Args:
        file_path: Path to the file to check

    Returns:
        True if the file is a Python test file (.py extension and contains 'test' in name)
        False otherwise

    Example:
        >>> is_python_test_file("tests/test_example.py")
        True
        >>> is_python_test_file("src/main.js")
        False
    """
    path = Path(file_path)
    return path.suffix == '.py' and 'test' in path.name.lower()


def parse_unittest_failures(test_output: str) -> List[FailingTest]:
    """
    Parse Python unittest test output and extract failing tests with their errors.

    **When to use this tool:**
    - When working with Python test files (*.py)
    - After running 'make test' or 'python -m unittest' or 'pytest'
    - To extract structured information about test failures
    - To identify which tests are failing and why

    **Input format:**
    Raw output from unittest/pytest containing failure blocks that look like:
        ======================================================================
        FAIL: test_name (test_module.TestClass.test_name)
        Test description
        ----------------------------------------------------------------------
        Traceback (most recent call last):
          File "/path/to/test.py", line X, in test_name
            self.assertEqual(expected, actual)
        AssertionError: error message

    Args:
        test_output: Raw output from unittest/pytest test runner as a string

    Returns:
        List of FailingTest objects, each containing:
        - test_file: Path to the test file
        - test_name: Full qualified test name (module.Class.method)
        - test_class: Test class name (if applicable)
        - test_method: Test method name
        - error_type: Type of error (AssertionError, ValueError, etc.)
        - error_message: The error message
        - traceback: Full traceback
        - line_number: Line number where test failed

    Example:
        >>> output = run_command('make test')
        >>> failures = parse_unittest_failures(output)
        >>> for failure in failures:
        ...     print(f"{failure.test_name} failed at {failure.test_file}:{failure.line_number}")
        ...     print(f"Error: {failure.error_message}")
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


# ============================================================================
# IdentifyFailingTests Agent
# ============================================================================

class IdentifyFailingTestsAgent:
    """
    Agent responsible for parsing test output and identifying failing tests.
    """

    def __init__(self, console: Console):
        self.console = console

    def parse_test_output(self, test_result: TestRunResult) -> List[FailingTest]:
        """
        Parse the test output and extract detailed information about each failing test.

        For Python test files, this method uses the parse_unittest_failures tool
        to extract structured information from unittest/pytest output.

        Args:
            test_result: The result from running tests

        Returns:
            List of FailingTest models
        """
        if test_result.failed_tests == 0:
            self.console.print("[bold green]No failing tests found![/bold green]")
            return []

        self.console.print(f"\n[bold yellow]Parsing {test_result.failed_tests} failing tests...[/bold yellow]\n")

        stdout = test_result.stdout

        # Check if this is Python unittest/pytest output by looking for unittest patterns
        # Unittest format: "====== FAIL: test_name"
        # Pytest format: "tests/test_file.py::TestClass::test_method FAILED"
        is_unittest_format = '=' * 70 in stdout and 'FAIL:' in stdout
        is_pytest_format = '::' in stdout and 'FAILED' in stdout and '.py' in stdout

        if is_unittest_format:
            # Use the parse_unittest_failures tool for unittest-style output
            self.console.print("[cyan]Detected unittest format - using parse_unittest_failures tool[/cyan]")
            failures = parse_unittest_failures(stdout)
            self._display_failures(failures)
            return failures

        # Fall back to pytest parsing for pytest format
        self.console.print("[cyan]Detected pytest format - using pytest parser[/cyan]")
        failures = []

        # Parse pytest verbose output for FAILED lines
        # Format: tests/test_file.py::TestClass::test_method FAILED
        failed_pattern = r'(tests/[\w/]+\.py)::([\w:]+)\s+FAILED'
        matches = re.finditer(failed_pattern, stdout)

        for match in matches:
            test_file = match.group(1)
            test_path = match.group(2)

            # Parse test class and method
            path_parts = test_path.split('::')
            if len(path_parts) == 2:
                test_class = path_parts[0]
                test_method = path_parts[1]
            else:
                test_class = None
                test_method = path_parts[0]

            # Try to find the error details in the output
            # This is a simplified version - in production, you'd parse the full traceback
            error_type = "Unknown"
            error_message = "Test failed"
            traceback = ""
            line_number = None

            # Look for the failure section in output
            failure_section_pattern = rf'_+ {re.escape(test_path)} _+'
            failure_section_match = re.search(failure_section_pattern, stdout)

            if failure_section_match:
                # Extract the section after this match until the next test or end
                start_pos = failure_section_match.end()
                # Look for the next test failure or end of failures
                next_section = re.search(r'_+ [\w:]+ _+', stdout[start_pos:])
                if next_section:
                    end_pos = start_pos + next_section.start()
                else:
                    end_pos = len(stdout)

                failure_details = stdout[start_pos:end_pos]
                traceback = failure_details.strip()

                # Extract error type
                error_type_match = re.search(r'(\w+Error):', failure_details)
                if error_type_match:
                    error_type = error_type_match.group(1)

                # Extract error message
                error_msg_match = re.search(r'(?:AssertionError|Error):\s*(.+?)(?:\n|$)', failure_details)
                if error_msg_match:
                    error_message = error_msg_match.group(1).strip()

                # Extract line number
                line_match = re.search(r':(\d+):', failure_details)
                if line_match:
                    line_number = int(line_match.group(1))

            failures.append(FailingTest(
                test_file=test_file,
                test_name=test_path,
                test_class=test_class,
                test_method=test_method,
                error_type=error_type,
                error_message=error_message,
                traceback=traceback,
                line_number=line_number
            ))

        # Display summary
        self._display_failures(failures)
        return failures

    def _display_failures(self, failures: List[FailingTest]):
        """Display failing tests in a formatted table."""
        if not failures:
            return

        table = Table(title="Failing Tests", show_header=True, header_style="bold magenta")
        table.add_column("Test File", style="cyan")
        table.add_column("Test Name", style="yellow")
        table.add_column("Error Type", style="red")
        table.add_column("Error Message", style="white")

        for failure in failures:
            table.add_row(
                failure.test_file,
                failure.test_method,
                failure.error_type,
                failure.error_message[:50] + "..." if len(failure.error_message) > 50 else failure.error_message
            )

        self.console.print(table)


# ============================================================================
# RefactorAgent with Validation Hooks
# ============================================================================

class RefactorAgentWithHooks:
    """
    Agent responsible for refactoring functions to make them more testable.
    Includes comprehensive validation hooks.
    """

    def __init__(self, console: Console, dry_run: bool = False):
        self.console = console
        self.dry_run = dry_run
        self.max_function_lines = 30

    async def analyze_and_refactor(
        self,
        failing_test: FailingTest,
        claude_service: Any
    ) -> RefactoringResult:
        """
        Analyze a failing test and refactor the associated function.

        Args:
            failing_test: The failing test to address
            claude_service: Claude SDK client for AI assistance

        Returns:
            RefactoringResult with refactoring details
        """
        self.console.print(f"\n[bold cyan]Analyzing test: {failing_test.test_name}[/bold cyan]\n")

        # Extract the function being tested
        function_under_test = self._identify_function_under_test(failing_test)

        if not function_under_test:
            return RefactoringResult(
                function_name="Unknown",
                file_path=failing_test.test_file,
                success=False,
                changes_summary="Could not identify function under test",
                validation_issues=[
                    ValidationIssue(
                        hook_name="identify_function",
                        passed=False,
                        message="Failed to identify the function being tested"
                    )
                ]
            )

        # Read the source file
        source_file = self._find_source_file(failing_test.test_file)
        if not source_file or not source_file.exists():
            return RefactoringResult(
                function_name=function_under_test,
                file_path=str(source_file) if source_file else "Unknown",
                success=False,
                changes_summary="Source file not found"
            )

        source_code = source_file.read_text()

        # Analyze the function
        function_info = self._analyze_function(source_code, function_under_test)

        if not function_info:
            return RefactoringResult(
                function_name=function_under_test,
                file_path=str(source_file),
                success=False,
                changes_summary=f"Function {function_under_test} not found in {source_file}"
            )

        # Run pre-refactoring validation hooks
        validation_issues = self._run_validation_hooks(function_info, source_code)

        # If no issues found, function is already good
        if all(issue.passed for issue in validation_issues):
            self.console.print("[bold green]Function already meets all guidelines![/bold green]")
            return RefactoringResult(
                function_name=function_under_test,
                file_path=str(source_file),
                success=True,
                validation_issues=validation_issues,
                changes_summary="Function already meets all testability guidelines"
            )

        # Display issues
        self._display_validation_issues(validation_issues)

        # Refactor using Claude (simplified - in real implementation, use Claude SDK)
        refactored_code = await self._refactor_with_claude(
            function_info,
            source_code,
            validation_issues,
            claude_service
        )

        # Run post-refactoring validation
        post_validation = self._run_validation_hooks(
            self._analyze_function(refactored_code, function_under_test),
            refactored_code
        )

        success = all(issue.passed for issue in post_validation)

        # Write back if not dry run
        if success and not self.dry_run:
            source_file.write_text(refactored_code)
            self.console.print(f"[bold green]Refactored code written to {source_file}[/bold green]")

        return RefactoringResult(
            function_name=function_under_test,
            file_path=str(source_file),
            success=success,
            validation_issues=post_validation,
            changes_summary=self._generate_changes_summary(validation_issues, post_validation),
            refactored_code=refactored_code if success else None
        )

    def _identify_function_under_test(self, failing_test: FailingTest) -> Optional[str]:
        """
        Identify the function being tested based on test method name.
        Convention: test_function_name tests function_name
        """
        test_method = failing_test.test_method

        # Remove 'test_' prefix
        if test_method.startswith('test_'):
            return test_method[5:]

        return test_method

    def _find_source_file(self, test_file: str) -> Optional[Path]:
        """
        Find the source file corresponding to a test file.
        Convention: tests/test_module.py -> src/module.py
        """
        test_path = Path(test_file)

        # Remove 'test_' prefix from filename
        filename = test_path.name
        if filename.startswith('test_'):
            source_filename = filename[5:]
        else:
            source_filename = filename

        # Look in src directory
        source_path = Path('src') / source_filename

        return source_path if source_path.exists() else None

    def _analyze_function(self, source_code: str, function_name: str) -> Optional[Dict[str, Any]]:
        """
        Analyze a function in the source code.

        Returns:
            Dictionary with function information or None if not found
        """
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return None

        for node in ast.walk(tree):
            # Check for function definitions
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                return self._extract_function_info(node, source_code)

            # Check for methods in classes
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == function_name:
                        return self._extract_function_info(item, source_code)

        return None

    def _extract_function_info(self, node: ast.FunctionDef, source_code: str) -> Dict[str, Any]:
        """Extract detailed information about a function."""
        lines = source_code.split('\n')

        # Calculate function length
        start_line = node.lineno - 1
        end_line = node.end_lineno if node.end_lineno else start_line + 1
        function_lines = end_line - start_line

        # Check for environment variable access
        has_env_access = self._check_env_access(node)

        # Check for client object creation
        creates_clients = self._check_client_creation(node)

        # Check argument types
        has_typed_args = self._check_typed_arguments(node)

        # Check return type
        has_typed_return = node.returns is not None

        # Check if arguments have defaults
        has_default_args = len(node.args.defaults) > 0 or len(node.args.kw_defaults) > 0

        return {
            'name': node.name,
            'lineno': node.lineno,
            'end_lineno': node.end_lineno,
            'function_lines': function_lines,
            'has_env_access': has_env_access,
            'creates_clients': creates_clients,
            'has_typed_args': has_typed_args,
            'has_typed_return': has_typed_return,
            'has_default_args': has_default_args,
            'args': [arg.arg for arg in node.args.args],
            'is_method': len(node.args.args) > 0 and node.args.args[0].arg in ['self', 'cls']
        }

    def _check_env_access(self, node: ast.FunctionDef) -> bool:
        """Check if function accesses environment variables directly."""
        for child in ast.walk(node):
            # Check for os.environ or os.getenv
            if isinstance(child, ast.Attribute):
                if isinstance(child.value, ast.Name) and child.value.id == 'os':
                    if child.attr in ['environ', 'getenv']:
                        return True
        return False

    def _check_client_creation(self, node: ast.FunctionDef) -> List[str]:
        """Check if function creates HTTP or database client objects."""
        client_patterns = [
            'requests', 'httpx', 'aiohttp', 'urllib',
            'pymongo', 'psycopg2', 'sqlalchemy', 'redis'
        ]

        found_clients = []

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                # Check for client instantiation
                if isinstance(child.func, ast.Attribute):
                    if isinstance(child.func.value, ast.Name):
                        module = child.func.value.id
                        if any(pattern in module.lower() for pattern in client_patterns):
                            found_clients.append(module)
                elif isinstance(child.func, ast.Name):
                    name = child.func.id
                    if any(pattern in name.lower() for pattern in client_patterns):
                        found_clients.append(name)

        return found_clients

    def _check_typed_arguments(self, node: ast.FunctionDef) -> bool:
        """Check if function arguments are properly typed (not Any)."""
        for arg in node.args.args:
            if arg.arg in ['self', 'cls']:
                continue
            if arg.annotation is None:
                return False
            # Check if annotation is 'Any'
            if isinstance(arg.annotation, ast.Name) and arg.annotation.id == 'Any':
                return False
        return True

    def _run_validation_hooks(
        self,
        function_info: Optional[Dict[str, Any]],
        source_code: str
    ) -> List[ValidationIssue]:
        """
        Run all validation hooks on the function.

        Returns:
            List of validation issues
        """
        if not function_info:
            return [
                ValidationIssue(
                    hook_name="function_exists",
                    passed=False,
                    message="Function not found in source code"
                )
            ]

        issues = []

        # Hook 1: Function length <= 30 lines
        if function_info['function_lines'] > self.max_function_lines:
            issues.append(ValidationIssue(
                hook_name="max_function_length",
                passed=False,
                message=f"Function has {function_info['function_lines']} lines, exceeds maximum of {self.max_function_lines}"
            ))
        else:
            issues.append(ValidationIssue(
                hook_name="max_function_length",
                passed=True,
                message=f"Function length OK: {function_info['function_lines']} lines"
            ))

        # Hook 2: No direct environment variable access
        if function_info['has_env_access']:
            issues.append(ValidationIssue(
                hook_name="no_env_access",
                passed=False,
                message="Function reads directly from environment variables"
            ))
        else:
            issues.append(ValidationIssue(
                hook_name="no_env_access",
                passed=True,
                message="No direct environment variable access"
            ))

        # Hook 3: No client object creation
        if function_info['creates_clients']:
            issues.append(ValidationIssue(
                hook_name="no_client_creation",
                passed=False,
                message=f"Function creates client objects: {', '.join(function_info['creates_clients'])}"
            ))
        else:
            issues.append(ValidationIssue(
                hook_name="no_client_creation",
                passed=True,
                message="No client objects created in function"
            ))

        # Hook 4: Arguments are typed (not Any)
        if not function_info['has_typed_args']:
            issues.append(ValidationIssue(
                hook_name="typed_arguments",
                passed=False,
                message="Function arguments are not properly typed or use 'Any'"
            ))
        else:
            issues.append(ValidationIssue(
                hook_name="typed_arguments",
                passed=True,
                message="All arguments properly typed"
            ))

        # Hook 5: Return type is specified (not Any)
        if not function_info['has_typed_return']:
            issues.append(ValidationIssue(
                hook_name="typed_return",
                passed=False,
                message="Function return type not specified"
            ))
        else:
            issues.append(ValidationIssue(
                hook_name="typed_return",
                passed=True,
                message="Return type properly specified"
            ))

        # Hook 6: No default argument values
        if function_info['has_default_args']:
            issues.append(ValidationIssue(
                hook_name="no_default_arguments",
                passed=False,
                message="Function has arguments with default values"
            ))
        else:
            issues.append(ValidationIssue(
                hook_name="no_default_arguments",
                passed=True,
                message="No default argument values"
            ))

        return issues

    def _display_validation_issues(self, issues: List[ValidationIssue]):
        """Display validation issues in a formatted table."""
        table = Table(title="Validation Results", show_header=True, header_style="bold magenta")
        table.add_column("Hook", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("Message", style="white")

        for issue in issues:
            status = "[green]✓ PASSED[/green]" if issue.passed else "[red]✗ FAILED[/red]"
            table.add_row(issue.hook_name, status, issue.message)

        self.console.print(table)

    async def _refactor_with_claude(
        self,
        function_info: Dict[str, Any],
        source_code: str,
        validation_issues: List[ValidationIssue],
        claude_service: Any
    ) -> str:
        """
        Use Claude to refactor the function based on validation issues.

        This is a simplified version. In production, this would use the Claude SDK
        to interact with the AI for refactoring suggestions.
        """
        # For now, return the original source code
        # In a real implementation, you would:
        # 1. Build a prompt with the validation issues
        # 2. Send to Claude for refactoring suggestions
        # 3. Apply the suggestions
        # 4. Return the refactored code

        self.console.print("[yellow]Refactoring with Claude (simulated)...[/yellow]")

        return source_code

    def _generate_changes_summary(
        self,
        before_issues: List[ValidationIssue],
        after_issues: List[ValidationIssue]
    ) -> str:
        """Generate a summary of changes made during refactoring."""
        before_failed = [i for i in before_issues if not i.passed]
        after_failed = [i for i in after_issues if not i.passed]

        fixed_count = len(before_failed) - len(after_failed)

        if fixed_count > 0:
            return f"Fixed {fixed_count} validation issue(s). {len(after_failed)} issue(s) remaining."
        elif fixed_count == 0:
            return "No validation issues were resolved."
        else:
            return f"Refactoring introduced {abs(fixed_count)} new issue(s)."


# ============================================================================
# SummaryAgent
# ============================================================================

class SummaryAgent:
    """
    Agent responsible for summarizing refactoring changes.
    Follows the principles of "The Elements of Style" by Strunk & White.
    """

    def __init__(self, console: Console):
        self.console = console

    def generate_summary(
        self,
        test_result: TestRunResult,
        refactoring_results: List[RefactoringResult]
    ) -> RefactoringSummary:
        """
        Generate a concise summary following Elements of Style principles.

        Elements of Style principles applied:
        - Omit needless words
        - Use active voice
        - Put statements in positive form
        - Use specific, concrete language
        """
        total_refactorings = len(refactoring_results)
        successful = sum(1 for r in refactoring_results if r.success)

        # Count tests that could potentially be fixed
        tests_addressed = total_refactorings

        # Build concise summary
        summary_parts = []

        # Opening statement (active voice, specific)
        if test_result.failed_tests == 0:
            summary_parts.append("All tests passed.")
        else:
            summary_parts.append(f"Addressed {tests_addressed} of {test_result.failed_tests} failing tests.")

        # Refactoring results (positive form when possible)
        if successful > 0:
            summary_parts.append(f"Completed {successful} refactorings successfully.")

        if successful < total_refactorings:
            failed = total_refactorings - successful
            summary_parts.append(f"{failed} refactorings need additional work.")

        # Specific improvements (concrete language)
        all_issues_fixed = []
        for result in refactoring_results:
            if result.success:
                passed_hooks = [i.hook_name for i in result.validation_issues if i.passed]
                all_issues_fixed.extend(passed_hooks)

        # Count unique types of improvements
        unique_improvements = set(all_issues_fixed)
        if unique_improvements:
            improvement_desc = self._describe_improvements(unique_improvements)
            if improvement_desc:
                summary_parts.append(improvement_desc)

        # Combine into final summary (omit needless words)
        summary_text = " ".join(summary_parts)

        return RefactoringSummary(
            total_tests_fixed=successful,
            total_refactorings=total_refactorings,
            successful_refactorings=successful,
            summary_text=summary_text
        )

    def _describe_improvements(self, improvements: set) -> str:
        """Describe improvements in concrete terms."""
        descriptions = {
            'max_function_length': 'reduced function complexity',
            'no_env_access': 'removed environment dependencies',
            'no_client_creation': 'improved dependency injection',
            'typed_arguments': 'added type safety',
            'typed_return': 'clarified return types',
            'no_default_arguments': 'eliminated implicit defaults'
        }

        concrete_improvements = [descriptions.get(i, i) for i in improvements if i in descriptions]

        if not concrete_improvements:
            return ""

        if len(concrete_improvements) == 1:
            return f"Key improvement: {concrete_improvements[0]}."
        elif len(concrete_improvements) == 2:
            return f"Key improvements: {concrete_improvements[0]} and {concrete_improvements[1]}."
        else:
            return f"Key improvements: {', '.join(concrete_improvements[:-1])}, and {concrete_improvements[-1]}."

    def display_summary(self, summary: RefactoringSummary):
        """Display the summary in a rich panel."""
        self.console.print("\n")
        self.console.print(Panel(
            summary.summary_text,
            title="[bold]Refactoring Summary[/bold]",
            border_style="green",
            padding=(1, 2)
        ))

        # Display statistics
        stats_text = f"""
Tests Fixed: {summary.total_tests_fixed}
Total Refactorings: {summary.total_refactorings}
Successful: {summary.successful_refactorings}
Success Rate: {(summary.successful_refactorings / summary.total_refactorings * 100):.1f}%
        """.strip()

        self.console.print(Panel(
            stats_text,
            title="[bold]Statistics[/bold]",
            border_style="blue",
            padding=(1, 2)
        ))


# ============================================================================
# Main Orchestration
# ============================================================================

async def main():
    """
    Main orchestration function that coordinates all agents.
    """
    parser = argparse.ArgumentParser(
        description="Test Fixer Agent Team - Fix failing Python tests through refactoring"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run analysis without making changes'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show verbose output'
    )
    parser.add_argument(
        '--model',
        default='sonnet',
        choices=['sonnet', 'opus', 'haiku'],
        help='Claude model to use'
    )

    args = parser.parse_args()
    console = Console()

    console.print(Panel(
        "[bold cyan]Test Fixer Agent Team[/bold cyan]\n\n"
        "Orchestrating three specialized agents:\n"
        "1. IdentifyFailingTests - Parse test output\n"
        "2. RefactorAgent - Improve code testability\n"
        "3. SummaryAgent - Summarize changes",
        border_style="cyan",
        padding=(1, 2)
    ))

    # Step 1: Run tests
    console.print("\n[bold]Step 1: Running Tests[/bold]")
    test_result = run_tests()

    if test_result.failed_tests == 0:
        console.print("\n[bold green]All tests passing! No refactoring needed.[/bold green]")
        return 0

    # Step 2: Identify failing tests
    console.print("\n[bold]Step 2: Identifying Failing Tests[/bold]")
    identify_agent = IdentifyFailingTestsAgent(console)
    failing_tests = identify_agent.parse_test_output(test_result)

    if not failing_tests:
        console.print("[yellow]Could not parse any failing tests from output[/yellow]")
        return 1

    # Step 3: Refactor functions (process one test as per requirements)
    console.print("\n[bold]Step 3: Refactoring Functions[/bold]")
    refactor_agent = RefactorAgentWithHooks(console, dry_run=args.dry_run)

    # Process the first failing test
    refactoring_results = []

    if failing_tests:
        console.print(f"\n[cyan]Processing first failing test: {failing_tests[0].test_name}[/cyan]")

        # For this demo, we're not using actual Claude SDK integration
        # In production, you'd create the Claude client here
        result = await refactor_agent.analyze_and_refactor(
            failing_tests[0],
            claude_service=None  # Would be ClaudeSDKClient instance
        )
        refactoring_results.append(result)

    # Step 4: Generate summary
    console.print("\n[bold]Step 4: Generating Summary[/bold]")
    summary_agent = SummaryAgent(console)
    summary = summary_agent.generate_summary(test_result, refactoring_results)
    summary_agent.display_summary(summary)

    # Return exit code
    if summary.successful_refactorings == summary.total_refactorings:
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
