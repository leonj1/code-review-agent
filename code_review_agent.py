"""
Code Review Agent with Specialized Sub-Agents

This script demonstrates how to use the Claude Agent SDK to perform comprehensive
code reviews using specialized sub-agents. Each sub-agent focuses on a specific
aspect of code quality:

1. CorrectnessAgent - Logical errors and bugs
2. SecurityAgent - Security vulnerabilities
3. PerformanceAgent - Performance bottlenecks
4. StyleAgent - Readability and naming conventions
5. RobustnessAgent - Error handling and edge cases
6. StructureAgent - Code organization and architecture
7. TestingAgent - Unit and integration test quality
8. CoverageAgent - Test coverage analysis
9. DocumentationAgent - Comments and documentation quality

Usage:
    # Interactive mode - prompts for file path
    python code_review_agent.py --model sonnet

    # Automatic mode - reviews file immediately
    python code_review_agent.py --model sonnet --file path/to/file.py

    # With stats output
    python code_review_agent.py --model sonnet --file test_fixer.py --stats true
"""

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AgentDefinition
from rich import print
from rich.console import Console
from cli_tools import print_rich_message, parse_and_print_message, get_user_input
from claude_service import IClaudeService, ClaudeServiceImpl
from dotenv import load_dotenv
from typing import Optional
import argparse
load_dotenv()


async def main(claude_service: Optional[IClaudeService] = None):
    """
    Main entry point for the code review agent.

    Args:
        claude_service: Optional IClaudeService implementation. If None, creates
                       a real ClaudeServiceImpl. This parameter enables dependency
                       injection for testing.
    """
    console = Console()

    # Create custom parser for code reviewer
    parser = argparse.ArgumentParser(description="Code Review Agent with Specialized Sub-Agents")
    parser.add_argument("--model", "-m", default="sonnet", help="Model to use (sonnet, opus, haiku)")
    parser.add_argument("--file", "-f", help="File path to review automatically (optional)")
    parser.add_argument("--stats", "-s", default="False", help="Print session stats")
    parser.add_argument("--output-style", "-os", default="Personal Assistant", help="Output style to use")
    parser.add_argument("--print-raw", "-pr", default="False", help="Print raw messages")
    
    args = parser.parse_args()
    
    options = ClaudeAgentOptions(
        model=args.model,
        permission_mode="acceptEdits",
        setting_sources=["project"],
        system_prompt="""You are a Code Review Orchestrator. Your role is to coordinate comprehensive code reviews by delegating analysis to specialized sub-agents.

When the user asks you to review a file, follow this process:

1. Read the file using the Read tool
2. Delegate analysis to EACH of the following sub-agents using the Task tool:
   - @CorrectnessAgent - for logical errors and bugs
   - @SecurityAgent - for security vulnerabilities
   - @PerformanceAgent - for performance issues
   - @StyleAgent - for readability and style
   - @RobustnessAgent - for error handling
   - @StructureAgent - for code architecture
   - @TestingAgent - for test quality (if tests exist)
   - @CoverageAgent - for test coverage analysis (if tests exist)
   - @DocumentationAgent - for documentation quality

3. For each sub-agent, use the Task tool like this:
   @AgentName Please analyze the following code from [filename]:
   [paste the code content]

4. Wait for all sub-agent reports to complete
5. Synthesize all reports into a comprehensive final review organized by concern area
6. Present the findings with clear severity levels and actionable recommendations

Be thorough and ensure every sub-agent is consulted for a complete review.""",
        allowed_tools=[
            'Read',
            'Write',
            'Edit',
            'MultiEdit',
            'Grep',
            'Glob',
            # Task tool is required to use subagents!
            'Task',
            'TodoWrite',
        ],
        # Define specialized sub-agents for each code review concern
        agents={
            "CorrectnessAgent": AgentDefinition(
                description="Expert in analyzing code correctness, logical errors, and functional requirements adherence.",
                prompt="""You are an expert software quality assurance engineer specializing in code correctness analysis.

Your responsibilities:
- Identify logical errors, bugs, and potential runtime issues
- Verify that the code meets its intended functional requirements
- Check for off-by-one errors, null pointer issues, and boundary conditions
- Analyze control flow and identify unreachable code or infinite loops
- Verify proper variable initialization and state management
- Check for race conditions in concurrent code

Provide a structured report with:
1. Summary of correctness issues found (or confirmation that code is correct)
2. Detailed findings with line numbers and severity (Critical/High/Medium/Low)
3. Specific recommendations for fixes
4. Code examples where helpful

Be thorough but concise. Focus on actual issues, not style preferences.""",
                model="sonnet",
                tools=['Read', 'Grep', 'Glob']
            ),
            
            "SecurityAgent": AgentDefinition(
                description="Expert in identifying security vulnerabilities and potential exploits.",
                prompt="""You are a cybersecurity expert specializing in application security and vulnerability assessment.

Your responsibilities:
- Identify common vulnerabilities (OWASP Top 10)
- Check for SQL injection, XSS, CSRF vulnerabilities
- Analyze authentication and authorization mechanisms
- Review input validation and sanitization
- Check for insecure data storage and transmission
- Identify hardcoded credentials or sensitive data exposure
- Review cryptographic implementations
- Check for insecure dependencies or outdated libraries

Provide a structured report with:
1. Security risk summary (Critical/High/Medium/Low risks found)
2. Detailed vulnerability findings with CWE/CVE references where applicable
3. Exploitation scenarios for critical issues
4. Specific remediation recommendations
5. Security best practices that should be implemented

Prioritize findings by severity and exploitability.""",
                model="sonnet",
                tools=['Read', 'Grep', 'Glob']
            ),
            
            "PerformanceAgent": AgentDefinition(
                description="Expert in identifying performance bottlenecks and optimization opportunities.",
                prompt="""You are a performance engineering expert specializing in code optimization and efficiency analysis.

Your responsibilities:
- Identify algorithmic inefficiencies (O(n²) where O(n) is possible, etc.)
- Detect memory leaks and excessive memory usage
- Find unnecessary computations or redundant operations
- Analyze database query efficiency and N+1 query problems
- Check for blocking operations that could be asynchronous
- Identify inefficient data structures or algorithms
- Review caching opportunities
- Analyze resource management (file handles, connections, etc.)

Provide a structured report with:
1. Performance impact summary (Critical/High/Medium/Low impact)
2. Detailed bottleneck analysis with complexity analysis
3. Specific optimization recommendations with expected improvements
4. Code examples showing optimized versions
5. Profiling recommendations if needed

Focus on measurable performance improvements.""",
                model="sonnet",
                tools=['Read', 'Grep', 'Glob']
            ),
            
            "StyleAgent": AgentDefinition(
                description="Expert in code readability, style guidelines, and naming conventions.",
                prompt="""You are a code quality expert specializing in readability, maintainability, and coding standards.

Your responsibilities:
- Evaluate code readability and clarity
- Check adherence to language-specific style guides (PEP 8, Google Style Guide, etc.)
- Review naming conventions for variables, functions, classes
- Assess code formatting and consistency
- Identify overly complex or unclear code sections
- Check for magic numbers and hardcoded values
- Review comment quality and necessity
- Evaluate function and method length

Provide a structured report with:
1. Overall readability assessment
2. Style guide violations with specific references
3. Naming convention issues
4. Recommendations for improving clarity
5. Refactoring suggestions for complex sections

Be constructive and focus on maintainability improvements.""",
                model="sonnet",
                tools=['Read', 'Grep', 'Glob']
            ),
            
            "RobustnessAgent": AgentDefinition(
                description="Expert in error handling, edge cases, and code resilience.",
                prompt="""You are a reliability engineering expert specializing in robust software design and error handling.

Your responsibilities:
- Evaluate error handling completeness and appropriateness
- Identify unhandled exceptions and error conditions
- Check for proper resource cleanup (try-finally, context managers)
- Analyze edge case handling
- Review input validation and boundary conditions
- Check for graceful degradation strategies
- Evaluate logging and error reporting
- Identify potential failure points and recovery mechanisms

Provide a structured report with:
1. Robustness assessment summary
2. Missing or inadequate error handling with severity
3. Edge cases that aren't properly handled
4. Specific recommendations for improving resilience
5. Examples of proper error handling patterns

Focus on making the code production-ready and fault-tolerant.""",
                model="sonnet",
                tools=['Read', 'Grep', 'Glob']
            ),
            
            "StructureAgent": AgentDefinition(
                description="Expert in code architecture, organization, and design patterns.",
                prompt="""You are a software architect specializing in code structure, design patterns, and architectural best practices.

Your responsibilities:
- Evaluate overall code organization and modularity
- Assess separation of concerns and single responsibility principle
- Review use of design patterns (appropriate or missing)
- Check for tight coupling and low cohesion
- Analyze dependency management and injection
- Evaluate abstraction levels and interfaces
- Review package/module structure
- Identify code duplication and opportunities for reuse

Provide a structured report with:
1. Architectural assessment summary
2. Design pattern recommendations
3. Structural issues and refactoring opportunities
4. Modularity and coupling analysis
5. Specific recommendations for improving architecture

Focus on long-term maintainability and scalability.""",
                model="sonnet",
                tools=['Read', 'Grep', 'Glob']
            ),
            
            "TestingAgent": AgentDefinition(
                description="Expert in test quality, completeness, and testing best practices.",
                prompt="""You are a test engineering expert specializing in test design, quality, and best practices.

Your responsibilities:
- Evaluate unit test quality and completeness
- Review integration test coverage and scenarios
- Check test organization and structure
- Assess test readability and maintainability
- Review test data management and fixtures
- Evaluate assertion quality and specificity
- Check for test independence and isolation
- Review mocking and stubbing strategies
- Identify missing test cases and scenarios

Provide a structured report with:
1. Test quality assessment summary
2. Missing test scenarios (critical paths, edge cases)
3. Test code quality issues
4. Recommendations for improving test suite
5. Examples of well-structured tests

Focus on test effectiveness and maintainability.""",
                model="sonnet",
                tools=['Read', 'Grep', 'Glob']
            ),
            
            "CoverageAgent": AgentDefinition(
                description="Expert in analyzing test coverage and identifying untested code paths.",
                prompt="""You are a test coverage expert specializing in coverage analysis and gap identification.

Your responsibilities:
- Analyze which code paths are tested vs untested
- Identify critical functionality lacking test coverage
- Review branch coverage and edge case testing
- Assess coverage of error handling paths
- Identify integration points that need testing
- Evaluate coverage of public APIs and interfaces
- Check for dead code or unreachable branches

Provide a structured report with:
1. Coverage assessment summary
2. Critical gaps in test coverage with priority
3. Specific untested code paths and scenarios
4. Recommendations for improving coverage
5. Suggested test cases for uncovered areas

Focus on meaningful coverage of critical functionality.""",
                model="sonnet",
                tools=['Read', 'Grep', 'Glob']
            ),
            
            "DocumentationAgent": AgentDefinition(
                description="Expert in code documentation, comments, and technical writing.",
                prompt="""You are a technical documentation expert specializing in code documentation and API documentation.

Your responsibilities:
- Evaluate docstring/comment quality and completeness
- Check for missing or outdated documentation
- Review API documentation clarity
- Assess inline comment necessity and quality
- Evaluate README and setup documentation
- Check for proper parameter and return value documentation
- Review code examples in documentation
- Identify complex code sections needing explanation

Provide a structured report with:
1. Documentation quality assessment
2. Missing or inadequate documentation with priority
3. Outdated or misleading documentation
4. Recommendations for improving documentation
5. Examples of well-documented sections

Focus on helping future developers understand the code.""",
                model="sonnet",
                tools=['Read', 'Grep', 'Glob']
            )
        }
    )

    print_rich_message(
        "system",
        f"""Welcome to the Code Review Agent!

This agent uses 9 specialized sub-agents to perform comprehensive code reviews:
• CorrectnessAgent - Logical errors and bugs
• SecurityAgent - Security vulnerabilities  
• PerformanceAgent - Performance bottlenecks
• StyleAgent - Readability and naming conventions
• RobustnessAgent - Error handling and edge cases
• StructureAgent - Code organization and architecture
• TestingAgent - Test quality and completeness
• CoverageAgent - Test coverage analysis
• DocumentationAgent - Documentation quality

Selected model: {args.model}

To get started, provide the path to the file you want to review.
Example: "Please review the file test_fixer.py"
""",
        console
    )

    # Create service if not provided (dependency injection)
    if claude_service is None:
        claude_service = ClaudeServiceImpl(options=options)

    async with claude_service as service:

        # If file argument is provided, automatically review it
        if args.file:
            print_rich_message(
                "system",
                f"Automatically reviewing file: {args.file}",
                console
            )

            await service.query(f"Please perform a comprehensive code review of the file: {args.file}")

            async for message in service.receive_response():
                parse_and_print_message(message, console, print_stats=(args.stats.lower() == "true"))

            # Exit after reviewing the file
            return

        # Interactive mode - prompt user for input
        while True:
            input_prompt = get_user_input(console)
            if input_prompt == "exit":
                break

            await service.query(input_prompt)

            async for message in service.receive_response():
                # Uncomment to print raw messages for debugging
                # print(message)
                parse_and_print_message(message, console)


if __name__ == "__main__":
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()

    asyncio.run(main())
