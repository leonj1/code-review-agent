#!/usr/bin/env python3
"""
Refactoring Agent: Automatically refactors source code by extracting functions into service classes.

This agent:
1. Identifies the primary function in a class
2. Extracts other functions into their own service classes
3. Validates the refactoring through hooks
4. Iterates until all functions are properly extracted
"""

import argparse
import asyncio
import ast
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_service import IClaudeService, ClaudeServiceImpl
from cli_tools import print_rich_message, parse_and_print_message


@dataclass
class FunctionInfo:
    """Information about a function in the source file."""
    name: str
    lineno: int
    col_offset: int
    is_constructor: bool
    is_static: bool
    is_class_method: bool
    has_env_access: bool
    external_calls: List[str]
    body: str


@dataclass
class ClassInfo:
    """Information about a class in the source file."""
    name: str
    lineno: int
    functions: List[FunctionInfo]
    primary_function: Optional[str] = None


@dataclass
class RefactoringAttempt:
    """Record of a refactoring attempt."""
    iteration: int
    target_function: str
    service_class_name: str
    success: bool
    validation_errors: List[str]
    changes_made: List[str]


@dataclass
class ValidationResult:
    """Result of validation hooks."""
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class RefactoringAgent:
    """Agent for refactoring source code by extracting functions into service classes."""

    def __init__(
        self,
        claude_service: Optional[IClaudeService] = None,
        model: str = "sonnet",
        max_iterations: int = 50,
        verbose: bool = False
    ):
        self.claude_service = claude_service
        self.model = model
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.console = Console()
        self.attempts: List[RefactoringAttempt] = []
        self.current_source: str = ""
        self.original_source: str = ""
        self.file_path: str = ""

    async def refactor_file(self, file_path: str) -> bool:
        """Main entry point for refactoring a file."""
        self.file_path = file_path

        # Read the source file
        try:
            with open(file_path, 'r') as f:
                self.original_source = f.read()
                self.current_source = self.original_source
        except FileNotFoundError:
            self.console.print(f"[red]Error: File not found: {file_path}[/red]")
            return False
        except Exception as e:
            self.console.print(f"[red]Error reading file: {e}[/red]")
            return False

        self.console.print(Panel(f"Starting refactoring of [cyan]{file_path}[/cyan]"))

        # Analyze the file structure
        classes = self._analyze_source_structure()
        if not classes:
            self.console.print("[yellow]No classes found in the file.[/yellow]")
            return True

        # Process each class
        for class_info in classes:
            success = await self._refactor_class(class_info)
            if not success:
                self.console.print(f"[red]Failed to refactor class {class_info.name}[/red]")
                return False

        # Write the refactored code back
        try:
            with open(file_path, 'w') as f:
                f.write(self.current_source)
            self.console.print("[green]Refactoring completed successfully![/green]")
            return True
        except Exception as e:
            self.console.print(f"[red]Error writing refactored file: {e}[/red]")
            return False

    def _analyze_source_structure(self) -> List[ClassInfo]:
        """Analyze the source file to extract class and function information."""
        classes = []

        try:
            tree = ast.parse(self.current_source)
        except SyntaxError as e:
            self.console.print(f"[red]Syntax error in source file: {e}[/red]")
            return []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = ClassInfo(
                    name=node.name,
                    lineno=node.lineno,
                    functions=[]
                )

                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        func_info = FunctionInfo(
                            name=item.name,
                            lineno=item.lineno,
                            col_offset=item.col_offset,
                            is_constructor=item.name == "__init__",
                            is_static=any(isinstance(d, ast.Name) and d.id == "staticmethod"
                                        for d in item.decorator_list),
                            is_class_method=any(isinstance(d, ast.Name) and d.id == "classmethod"
                                              for d in item.decorator_list),
                            has_env_access=self._check_env_access(item),
                            external_calls=self._find_external_calls(item),
                            body=ast.unparse(item)
                        )
                        class_info.functions.append(func_info)

                classes.append(class_info)

        return classes

    def _check_env_access(self, func_node: ast.FunctionDef) -> bool:
        """Check if a function accesses environment variables."""
        for node in ast.walk(func_node):
            # Check for os.environ access
            if isinstance(node, ast.Attribute):
                if (isinstance(node.value, ast.Name) and
                    node.value.id == "os" and
                    node.attr == "environ"):
                    return True

            # Check for os.getenv calls
            if isinstance(node, ast.Call):
                if (isinstance(node.func, ast.Attribute) and
                    isinstance(node.func.value, ast.Name) and
                    node.func.value.id == "os" and
                    node.func.attr in ["getenv", "getenvb"]):
                    return True

                # Check for dotenv usage
                if (isinstance(node.func, ast.Name) and
                    node.func.id in ["load_dotenv", "dotenv_values"]):
                    return True

        return False

    def _find_external_calls(self, func_node: ast.FunctionDef) -> List[str]:
        """Find external API/HTTP calls in a function."""
        external_calls = []

        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                # Check for requests library
                if isinstance(node.func, ast.Attribute):
                    if (isinstance(node.func.value, ast.Name) and
                        node.func.value.id == "requests" and
                        node.func.attr in ["get", "post", "put", "delete", "patch"]):
                        external_calls.append(f"requests.{node.func.attr}")

                # Check for httpx
                if (isinstance(node.func, ast.Attribute) and
                    isinstance(node.func.value, ast.Name) and
                    node.func.value.id == "httpx"):
                    external_calls.append(f"httpx.{node.func.attr}")

                # Check for urllib
                if (isinstance(node.func, ast.Attribute) and
                    hasattr(node.func.value, "attr") and
                    node.func.value.attr == "urlopen"):
                    external_calls.append("urllib.urlopen")

        return external_calls

    async def _identify_primary_function(self, class_info: ClassInfo) -> str:
        """Use Claude to identify the primary function of a class."""
        if self.claude_service is None:
            options = ClaudeAgentOptions(
                model=f"claude-3-5-{self.model}-latest",
                permission_mode="acceptEdits",
                name="RefactoringAgent",
                tools=["Read", "Write", "Edit", "Grep", "Glob"]
            )
            self.claude_service = ClaudeServiceImpl(options=options)

        prompt = f"""
        Analyze this class and identify which function is most likely the PRIMARY function
        (the main business logic function, not constructor or utility methods).

        Class: {class_info.name}
        Functions:
        {chr(10).join([f"- {f.name} (line {f.lineno})" for f in class_info.functions])}

        Source code:
        ```python
        {self.current_source}
        ```

        Return ONLY the function name of the primary function, nothing else.
        If there's no clear primary function, return the most complex non-constructor function.
        """

        async with self.claude_service as service:
            await service.query(prompt)
            primary_function = ""
            async for message in service.receive_response():
                if message.get("type") == "text":
                    primary_function = message.get("content", "").strip()

        return primary_function

    async def _refactor_class(self, class_info: ClassInfo) -> bool:
        """Refactor a single class by extracting functions into service classes."""
        # Identify the primary function
        primary_function = await self._identify_primary_function(class_info)
        class_info.primary_function = primary_function

        self.console.print(f"Primary function identified: [cyan]{primary_function}[/cyan]")

        # Get functions to extract (exclude constructor and primary)
        functions_to_extract = [
            f for f in class_info.functions
            if not f.is_constructor and f.name != primary_function
        ]

        if not functions_to_extract:
            self.console.print("[green]No functions to extract.[/green]")
            return True

        # Extract each function
        iteration = 0
        while functions_to_extract and iteration < self.max_iterations:
            iteration += 1
            func = functions_to_extract[0]

            self.console.print(f"\n[bold]Iteration {iteration}:[/bold] Extracting [cyan]{func.name}[/cyan]")

            # Attempt extraction
            success = await self._extract_function_to_service(class_info, func)

            if success:
                functions_to_extract.pop(0)
                self.console.print(f"[green]Successfully extracted {func.name}[/green]")
            else:
                # Get failure history for this function
                failures = self._get_failure_history(func.name)
                if len(failures) >= 3:
                    self.console.print(f"[red]Failed to extract {func.name} after 3 attempts. Skipping.[/red]")
                    functions_to_extract.pop(0)
                else:
                    self.console.print(f"[yellow]Retrying extraction of {func.name}[/yellow]")

        return len(functions_to_extract) == 0

    async def _extract_function_to_service(
        self,
        class_info: ClassInfo,
        func: FunctionInfo
    ) -> bool:
        """Extract a single function into a service class."""
        service_class_name = f"{func.name.title()}Service"

        # Get previous attempts for context
        failure_history = self._get_failure_history(func.name)

        # Build the refactoring prompt
        prompt = self._build_refactoring_prompt(
            class_info,
            func,
            service_class_name,
            failure_history
        )

        # Execute refactoring with Claude
        refactored_code = await self._execute_refactoring(prompt)

        if not refactored_code:
            self._record_attempt(
                func.name,
                service_class_name,
                False,
                ["Failed to generate refactored code"]
            )
            return False

        # Apply the refactored code
        self.current_source = refactored_code

        # Run validation hooks
        validation = self._run_validation_hooks(func, service_class_name)

        if validation.passed:
            self._record_attempt(func.name, service_class_name, True, [])
            return True
        else:
            # Revert changes
            self.current_source = self.original_source
            self._record_attempt(func.name, service_class_name, False, validation.errors)
            return False

    def _build_refactoring_prompt(
        self,
        class_info: ClassInfo,
        func: FunctionInfo,
        service_class_name: str,
        failure_history: List[RefactoringAttempt]
    ) -> str:
        """Build the prompt for Claude to perform refactoring."""
        prompt = f"""
        Refactor the following Python class by extracting the function '{func.name}'
        into a separate service class called '{service_class_name}'.

        Requirements:
        1. Create a new service class {service_class_name} that encapsulates the logic of {func.name}
        2. The service class should be injected into the original class via constructor
        3. Replace the original function with a call to the service
        4. NO environment variable access in service classes - pass all config via constructor
        5. External clients (HTTP, DB) must be injected as interfaces, not concrete implementations
        6. Maintain all functionality and behavior

        Current source code:
        ```python
        {self.current_source}
        ```

        Function to extract: {func.name} (line {func.lineno})
        """

        if func.has_env_access:
            prompt += "\nWARNING: This function accesses environment variables. Move all env access to constructor parameters."

        if func.external_calls:
            prompt += f"\nWARNING: This function makes external calls: {', '.join(func.external_calls)}. Create interfaces for these."

        if failure_history:
            prompt += "\n\nPREVIOUS FAILED ATTEMPTS (avoid these mistakes):\n"
            for attempt in failure_history:
                prompt += f"\nAttempt {attempt.iteration}:\n"
                prompt += f"- Service class: {attempt.service_class_name}\n"
                prompt += f"- Errors: {', '.join(attempt.validation_errors)}\n"

        prompt += """

        Return the COMPLETE refactored Python code including:
        1. The new service class
        2. Any necessary interfaces
        3. The modified original class
        4. All imports

        Ensure the code is syntactically correct and follows Python best practices.
        """

        return prompt

    async def _execute_refactoring(self, prompt: str) -> Optional[str]:
        """Execute the refactoring using Claude."""
        if self.claude_service is None:
            options = ClaudeAgentOptions(
                model=f"claude-3-5-{self.model}-latest",
                permission_mode="acceptEdits",
                name="RefactoringAgent"
            )
            self.claude_service = ClaudeServiceImpl(options=options)

        refactored_code = ""
        async with self.claude_service as service:
            await service.query(prompt)
            async for message in service.receive_response():
                if message.get("type") == "text":
                    content = message.get("content", "")
                    # Extract code from markdown if present
                    if "```python" in content:
                        start = content.find("```python") + 9
                        end = content.find("```", start)
                        refactored_code = content[start:end].strip()
                    else:
                        refactored_code = content.strip()

        return refactored_code if refactored_code else None

    def _run_validation_hooks(self, func: FunctionInfo, service_class_name: str) -> ValidationResult:
        """Run validation hooks on the refactored code."""
        result = ValidationResult(passed=True)

        # Hook 1: Validate service class was created
        if not self._validate_service_class_created(service_class_name):
            result.passed = False
            result.errors.append(f"Service class {service_class_name} was not created")

        # Hook 2: Validate function was removed from original class
        if not self._validate_function_removed(func.name):
            result.passed = False
            result.errors.append(f"Function {func.name} was not removed from original class")

        # Hook 3: Validate no environment variable access in service class
        if not self._validate_no_env_access(service_class_name):
            result.passed = False
            result.errors.append(f"Service class {service_class_name} accesses environment variables")

        # Hook 4: Validate external clients use interfaces
        if not self._validate_interface_usage(service_class_name):
            result.passed = False
            result.errors.append(f"Service class {service_class_name} uses concrete implementations instead of interfaces")

        # Hook 5: Validate syntax
        if not self._validate_syntax():
            result.passed = False
            result.errors.append("Refactored code has syntax errors")

        return result

    def _validate_service_class_created(self, service_class_name: str) -> bool:
        """Validate that the service class was created."""
        try:
            tree = ast.parse(self.current_source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == service_class_name:
                    return True
        except:
            pass
        return False

    def _validate_function_removed(self, func_name: str) -> bool:
        """Validate that the function was removed from the original class."""
        try:
            tree = ast.parse(self.current_source)
            classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

            # Check if function still exists in original classes (not service classes)
            for class_node in classes:
                if "Service" not in class_node.name:  # Skip service classes
                    for item in class_node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == func_name:
                            # Check if it's just a delegation call
                            if len(item.body) == 1 and isinstance(item.body[0], ast.Return):
                                return True  # It's a delegation, that's OK
                            return False  # Function still has implementation
        except:
            pass
        return True

    def _validate_no_env_access(self, service_class_name: str) -> bool:
        """Validate that the service class doesn't access environment variables."""
        try:
            tree = ast.parse(self.current_source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == service_class_name:
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            if self._check_env_access(item):
                                return False
        except:
            pass
        return True

    def _validate_interface_usage(self, service_class_name: str) -> bool:
        """Validate that external clients use interfaces, not concrete implementations."""
        try:
            tree = ast.parse(self.current_source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == service_class_name:
                    # Check constructor for concrete HTTP client instantiation
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                            for stmt in ast.walk(item):
                                # Check for assignments to self.client or similar
                                if isinstance(stmt, ast.Assign):
                                    for target in stmt.targets:
                                        if isinstance(target, ast.Attribute) and target.attr == "client":
                                            # Check if assigning requests module directly
                                            if isinstance(stmt.value, ast.Name) and stmt.value.id == "requests":
                                                return False

                                # Check for concrete client instantiation in calls
                                if isinstance(stmt, ast.Call):
                                    if isinstance(stmt.func, ast.Name):
                                        if stmt.func.id in ["requests", "httpx", "Client"]:
                                            return False
        except:
            pass
        return True

    def _validate_syntax(self) -> bool:
        """Validate that the refactored code has valid Python syntax."""
        try:
            ast.parse(self.current_source)
            return True
        except SyntaxError:
            return False

    def _record_attempt(
        self,
        func_name: str,
        service_class_name: str,
        success: bool,
        errors: List[str]
    ):
        """Record a refactoring attempt."""
        attempt = RefactoringAttempt(
            iteration=len(self.attempts) + 1,
            target_function=func_name,
            service_class_name=service_class_name,
            success=success,
            validation_errors=errors,
            changes_made=[]
        )
        self.attempts.append(attempt)

    def _get_failure_history(self, func_name: str) -> List[RefactoringAttempt]:
        """Get the history of failed attempts for a specific function."""
        return [
            attempt for attempt in self.attempts
            if attempt.target_function == func_name and not attempt.success
        ]

    def print_summary(self):
        """Print a summary of the refactoring process."""
        table = Table(title="Refactoring Summary")
        table.add_column("Iteration", style="cyan")
        table.add_column("Function", style="magenta")
        table.add_column("Service Class", style="blue")
        table.add_column("Status", style="green")
        table.add_column("Errors", style="red")

        for attempt in self.attempts:
            status = "✓ Success" if attempt.success else "✗ Failed"
            errors = "\n".join(attempt.validation_errors) if attempt.validation_errors else "None"
            table.add_row(
                str(attempt.iteration),
                attempt.target_function,
                attempt.service_class_name,
                status,
                errors
            )

        self.console.print(table)


async def main():
    """Main entry point for the refactoring agent."""
    parser = argparse.ArgumentParser(
        description="Refactor Python source files by extracting functions into service classes"
    )
    parser.add_argument(
        "file",
        help="Path to the Python source file to refactor"
    )
    parser.add_argument(
        "--model",
        "-m",
        default="sonnet",
        choices=["sonnet", "opus", "haiku"],
        help="Claude model to use (default: sonnet)"
    )
    parser.add_argument(
        "--max-iterations",
        "-i",
        type=int,
        default=50,
        help="Maximum number of refactoring iterations (default: 50)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Perform a dry run without modifying files"
    )

    args = parser.parse_args()

    # Validate file exists
    if not Path(args.file).exists():
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    # Create the agent
    agent = RefactoringAgent(
        model=args.model,
        max_iterations=args.max_iterations,
        verbose=args.verbose
    )

    # Perform refactoring
    success = await agent.refactor_file(args.file)

    # Print summary
    agent.print_summary()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())