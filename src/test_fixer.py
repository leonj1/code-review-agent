"""
Test Fixer Agent

This script automatically fixes failing tests using an agent-driven approach:
1. Running the test suite
2. Analyzing failures with Claude (with previous attempt history)
3. Applying suggested fixes (avoiding repeated approaches)
4. Re-running tests
5. Asking Claude whether to continue based on progress and alternative strategies

Agent-Driven Stopping:
The agent analyzes the attempt history and decides whether to continue by evaluating:
- Progress made (are failures decreasing?)
- Repeated approaches (are we trying the same thing?)
- Alternative strategies (do we have new ideas to try?)
- Problem solvability (is this fixable with available information?)

Safety Stopping Conditions:
- All tests pass (success!)
- Maximum iteration safety limit (default: 20, rarely hit)
- Test count decreases significantly (breaking changes)
- User interruption (Ctrl+C)

This approach allows the agent to make intelligent decisions rather than hitting
arbitrary limits, while still maintaining safety guardrails.
"""

import subprocess
import re
import argparse
import asyncio
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.markdown import Markdown
from claude_agent_sdk import ClaudeAgentOptions, AgentDefinition
from src.claude_service import IClaudeService, ClaudeServiceImpl
from dotenv import load_dotenv

load_dotenv()


@dataclass
class TestResult:
    """Represents the result of running tests."""
    passed: int
    failed: int
    total: int
    failures: List[str]
    exit_code: int
    full_output: str

    def has_failures(self) -> bool:
        """Check if there are any test failures."""
        return self.failed > 0

    def is_worse_than(self, other: 'TestResult') -> bool:
        """Check if this result is worse than another (more failures)."""
        return self.failed > other.failed


@dataclass
class FixAttempt:
    """Represents a single fix attempt."""
    iteration: int
    test_result: TestResult
    fixes_applied: List[str]


class TestFixer:
    """
    Main test fixer orchestrator.

    Uses Claude to analyze and fix failing tests through an iterative process.
    """

    def __init__(
        self,
        claude_service: Optional[IClaudeService] = None,
        max_iterations: int = 20,
        console: Optional[Console] = None
    ):
        """
        Initialize the test fixer.

        Args:
            claude_service: Optional Claude service (for testing)
            max_iterations: Maximum iterations (safety limit, default 20).
                          The agent primarily decides when to stop.
            console: Rich console for output
        """
        self.claude_service = claude_service
        self.max_iterations = max_iterations
        self.console = console or Console()
        self.fix_history: List[FixAttempt] = []

    def run_tests(self, test_path: str = ".") -> TestResult:
        """
        Run pytest and capture results.

        Args:
            test_path: Path to tests directory or file

        Returns:
            TestResult containing test outcomes
        """
        self.console.print(f"[cyan]Running tests: {test_path}[/cyan]")

        try:
            result = subprocess.run(
                ["pytest", test_path, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            output = result.stdout + result.stderr

            # Parse pytest output
            passed = len(re.findall(r"PASSED", output))
            failed = len(re.findall(r"FAILED", output))
            total = passed + failed

            # Extract failure details
            failures = self._extract_failures(output)

            return TestResult(
                passed=passed,
                failed=failed,
                total=total,
                failures=failures,
                exit_code=result.returncode,
                full_output=output
            )

        except subprocess.TimeoutExpired:
            self.console.print("[red]Tests timed out after 5 minutes[/red]")
            return TestResult(0, 999, 999, ["Test suite timeout"], -1, "")
        except FileNotFoundError:
            self.console.print("[red]pytest not found. Install with: pip install pytest[/red]")
            raise

    def _extract_failures(self, output: str) -> List[str]:
        """
        Extract failure details from pytest output.

        Args:
            output: Full pytest output

        Returns:
            List of failure descriptions
        """
        failures = []

        # Look for FAILED test lines (format: test_file.py::test_name FAILED - error)
        failed_pattern = r"([\w/._]+::\w+) FAILED - (.+?)(?:\n|$)"
        matches = re.finditer(failed_pattern, output, re.MULTILINE)

        for match in matches:
            test_name = match.group(1)
            error = match.group(2)
            failures.append(f"{test_name}: {error}")

        # If no structured failures found, look for assertion errors
        if not failures:
            assertion_pattern = r"(AssertionError: .+?)(?:\n|$)"
            matches = re.finditer(assertion_pattern, output, re.MULTILINE)
            for match in matches:
                failures.append(match.group(1))

        return failures

    async def analyze_failures_with_claude(self, test_result: TestResult) -> str:
        """
        Send test failures to Claude for analysis.

        Args:
            test_result: The failed test result

        Returns:
            Claude's suggested fixes
        """
        # Build history context from previous attempts
        history_context = self._build_history_context()

        prompt = f"""I have failing tests. Please analyze the failures and suggest fixes.

Test Results:
- Total tests: {test_result.total}
- Passed: {test_result.passed}
- Failed: {test_result.failed}

Failures:
{chr(10).join(f"- {failure}" for failure in test_result.failures)}

Full Output:
```
{test_result.full_output}
```

{history_context}

Please provide:
1. Root cause analysis for each failure
2. Specific code changes needed to fix each issue
3. File paths and line numbers for changes
4. Updated code snippets

IMPORTANT: Review the previous attempts above (if any) and avoid repeating the same approach.
Think of alternative solutions if previous attempts failed.

Format your response with clear sections for each fix."""

        self.console.print("[cyan]Analyzing failures with Claude...[/cyan]")

        response_text = ""
        await self.claude_service.query(prompt)

        async for message in self.claude_service.receive_response():
            if hasattr(message, 'content'):
                response_text += str(message.content)

        return response_text

    def _build_history_context(self) -> str:
        """
        Build context string from previous fix attempts.

        Returns:
            Formatted string describing previous attempts
        """
        if not self.fix_history:
            return ""

        context = "\n\n## Previous Fix Attempts:\n"
        for attempt in self.fix_history:
            context += f"\n### Attempt {attempt.iteration}:\n"
            context += f"- Files modified: {', '.join(attempt.fixes_applied) if attempt.fixes_applied else 'None'}\n"
            context += f"- Result: {attempt.test_result.passed} passed, {attempt.test_result.failed} failed\n"
            context += f"- Failures: {', '.join(attempt.test_result.failures[:3])}"
            if len(attempt.test_result.failures) > 3:
                context += f" ... and {len(attempt.test_result.failures) - 3} more"
            context += "\n"

        return context

    async def should_continue_fixing(self, current_result: TestResult) -> Tuple[bool, str]:
        """
        Ask Claude whether to continue fixing based on attempt history.

        Args:
            current_result: Latest test result

        Returns:
            Tuple of (should_continue, reason)
        """
        # Safety checks first
        if not current_result.has_failures():
            return False, "All tests passing!"

        if not self.fix_history:
            return True, "First attempt - continuing"

        # Build detailed history for Claude's analysis
        history_summary = self._build_history_context()

        prompt = f"""You are analyzing a test fixing session to determine if you should continue.

Current Status:
- Tests: {current_result.passed} passed, {current_result.failed} failed
- Current failures: {', '.join(current_result.failures[:5])}

{history_summary}

Based on this history, please analyze:

1. Are we making progress (fewer failures over time)?
2. Are we repeating the same failed approaches?
3. Do you have alternative strategies that haven't been tried?
4. Is this problem solvable with the information available?

Please respond with EXACTLY one of these two options:

CONTINUE: [brief reason why you have a new approach to try]
or
STOP: [brief reason why further attempts won't help]

Your decision:"""

        self.console.print("[cyan]Asking Claude if we should continue...[/cyan]")

        response_text = ""
        await self.claude_service.query(prompt)

        async for message in self.claude_service.receive_response():
            if hasattr(message, 'content'):
                response_text += str(message.content)

        # Parse Claude's decision
        response_upper = response_text.upper()
        if "CONTINUE:" in response_upper:
            reason = response_text.split("CONTINUE:", 1)[1].strip() if ":" in response_text else "Agent decided to continue"
            return True, f"Agent: {reason}"
        elif "STOP:" in response_upper:
            reason = response_text.split("STOP:", 1)[1].strip() if ":" in response_text else "Agent decided to stop"
            return False, f"Agent: {reason}"
        else:
            # Default to stop if unclear response
            return False, "Agent response unclear - stopping as safety measure"

    async def apply_fixes(self, claude_response: str) -> List[str]:
        """
        Apply fixes suggested by Claude.

        Args:
            claude_response: Claude's response with fix suggestions

        Returns:
            List of files modified
        """
        self.console.print("[cyan]Applying fixes...[/cyan]")

        # Ask Claude to apply the fixes
        fix_prompt = f"""Based on your analysis:

{claude_response}

Please now apply these fixes to the actual files. Use the Edit or Write tools to make the changes.
After making changes, list the files you modified."""

        files_modified = []
        await self.claude_service.query(fix_prompt)

        async for message in self.claude_service.receive_response():
            # Extract file modifications from Claude's response
            if hasattr(message, 'content'):
                content = str(message.content)
                # Look for file paths in the response
                file_pattern = r"(?:Modified|Updated|Fixed).*?([/\w._-]+\.py)"
                matches = re.finditer(file_pattern, content, re.IGNORECASE)
                for match in matches:
                    files_modified.append(match.group(1))

        return list(set(files_modified))  # Remove duplicates

    def check_stopping_conditions(
        self,
        current_iteration: int,
        current_result: TestResult,
        previous_result: Optional[TestResult]
    ) -> Tuple[bool, str]:
        """
        Check critical stopping conditions (safety checks only).

        This method now only checks for critical safety conditions.
        The agent makes the primary decision via should_continue_fixing().

        Args:
            current_iteration: Current iteration number
            current_result: Latest test result
            previous_result: Previous test result (if any)

        Returns:
            Tuple of (should_stop, reason)
        """
        # Success: All tests pass
        if not current_result.has_failures():
            return True, "All tests passing!"

        # Safety: Absolute maximum iterations (default 20, much higher than before)
        if current_iteration >= self.max_iterations:
            return True, f"Safety limit: Maximum iterations ({self.max_iterations}) reached"

        # Safety: Test count dropped significantly (breaking changes)
        if previous_result and current_result.total < previous_result.total - 2:
            return True, f"Safety: Test count decreased significantly ({previous_result.total} → {current_result.total})"

        # Check for regression: more failures than before
        if previous_result and current_result.failed > previous_result.failed:
            return True, f"Regression: failures increased from {previous_result.failed} to {current_result.failed}"

        # Check for no progress: same failures as before
        if previous_result and current_result.failures == previous_result.failures:
            return True, "No progress: failures haven't changed"

        # Let the agent decide in all other cases
        return False, ""

    async def fix_tests(self, test_path: str = ".") -> bool:
        """
        Main loop: repeatedly fix tests until stopping conditions met.

        Args:
            test_path: Path to tests

        Returns:
            True if all tests pass, False otherwise
        """
        self.console.print(Panel.fit(
            "[bold cyan]Test Fixer Agent[/bold cyan]\n"
            f"Max iterations: {self.max_iterations}",
            border_style="cyan"
        ))

        # Create Claude service if not provided
        if self.claude_service is None:
            options = ClaudeAgentOptions(
                model="sonnet",
                permission_mode="acceptEdits",
                allowed_tools=['Read', 'Write', 'Edit', 'Grep', 'Glob'],
                system_prompt="""You are a test fixing expert. Analyze test failures,
identify root causes, and apply precise fixes to make tests pass."""
            )
            self.claude_service = ClaudeServiceImpl(options=options)

        iteration = 0
        previous_result = None

        try:
            async with self.claude_service as service:
                self.claude_service = service

                while iteration < self.max_iterations:
                    iteration += 1
                    self.console.print(f"\n[bold]Iteration {iteration}[/bold] (safety limit: {self.max_iterations})")

                    # Run tests
                    current_result = self.run_tests(test_path)
                    self._print_test_results(current_result)

                    # Check critical safety conditions
                    should_stop, reason = self.check_stopping_conditions(
                        iteration, current_result, previous_result
                    )

                    if should_stop:
                        self.console.print(f"\n[green]✓ {reason}[/green]")
                        return not current_result.has_failures()

                    # Analyze and fix
                    analysis = await self.analyze_failures_with_claude(current_result)
                    fixes = await self.apply_fixes(analysis)

                    # Record attempt
                    attempt = FixAttempt(iteration, current_result, fixes)
                    self.fix_history.append(attempt)

                    self.console.print(f"[yellow]Files modified: {', '.join(fixes) if fixes else 'None'}[/yellow]")

                    # Ask agent if we should continue (agent-driven decision)
                    should_continue, agent_reason = await self.should_continue_fixing(current_result)

                    if not should_continue:
                        self.console.print(f"\n[yellow]⚠ {agent_reason}[/yellow]")
                        return False

                    self.console.print(f"[cyan]→ {agent_reason}[/cyan]")

                    previous_result = current_result

                # Safety limit reached (agent should have stopped before this)
                self.console.print(f"\n[red]✗ Safety limit reached ({self.max_iterations} iterations)[/red]")
                return False

        except KeyboardInterrupt:
            self.console.print("\n[yellow]⚠ Interrupted by user[/yellow]")
            return False

    def _print_test_results(self, result: TestResult):
        """Print formatted test results."""
        status_color = "green" if result.failed == 0 else "red"
        self.console.print(
            f"[{status_color}]Tests: {result.passed} passed, "
            f"{result.failed} failed, {result.total} total[/{status_color}]"
        )

        if result.failures:
            self.console.print("[red]Failures:[/red]")
            for failure in result.failures[:5]:  # Show first 5
                self.console.print(f"  • {failure}")
            if len(result.failures) > 5:
                self.console.print(f"  ... and {len(result.failures) - 5} more")


async def main():
    """CLI entry point for test fixer."""
    parser = argparse.ArgumentParser(description="Automatically fix failing tests using Claude")
    parser.add_argument(
        "test_path",
        nargs="?",
        default=".",
        help="Path to tests (default: current directory)"
    )
    parser.add_argument(
        "--max-iterations",
        "-m",
        type=int,
        default=20,
        help="Safety limit for iterations (default: 20). Agent decides when to stop."
    )
    parser.add_argument(
        "--model",
        default="sonnet",
        help="Claude model to use (default: sonnet)"
    )

    args = parser.parse_args()

    fixer = TestFixer(max_iterations=args.max_iterations)
    success = await fixer.fix_tests(args.test_path)

    exit_code = 0 if success else 1
    return exit_code


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
