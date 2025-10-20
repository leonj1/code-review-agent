"""
CLI Tools for Rich Console Output

This module provides utility functions for displaying formatted output
using the Rich library for better terminal UX.
"""

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from typing import Dict, Any, Optional


def print_rich_message(role: str, message: str, console: Console) -> None:
    """
    Print a formatted message with a role indicator.

    Args:
        role: The role/type of the message (e.g., "system", "user", "assistant")
        message: The message content to display
        console: Rich Console instance for output
    """
    color_map = {
        "system": "blue",
        "user": "green",
        "assistant": "cyan",
        "error": "red"
    }

    color = color_map.get(role, "white")
    panel = Panel(
        message.strip(),
        title=f"[bold]{role.upper()}[/bold]",
        border_style=color,
        padding=(1, 2)
    )
    console.print(panel)


def parse_and_print_message(
    message: Dict[str, Any],
    console: Console,
    print_stats: bool = False
) -> None:
    """
    Parse and display a message from the Claude Agent SDK.

    Args:
        message: The message dictionary from the agent
        console: Rich Console instance for output
        print_stats: Whether to print usage statistics
    """
    msg_type = message.get("type", "")

    if msg_type == "text":
        # Display text content
        content = message.get("content", "")
        if content:
            console.print(Markdown(content))

    elif msg_type == "usage":
        # Display usage statistics if requested
        if print_stats:
            usage = message.get("usage", {})
            stats_text = f"""
**Token Usage Statistics:**
- Input tokens: {usage.get('input_tokens', 0)}
- Output tokens: {usage.get('output_tokens', 0)}
- Total tokens: {usage.get('input_tokens', 0) + usage.get('output_tokens', 0)}
"""
            console.print(Panel(
                Markdown(stats_text),
                title="[bold]Statistics[/bold]",
                border_style="yellow"
            ))

    elif msg_type == "error":
        # Display error messages
        error_msg = message.get("content", "Unknown error")
        console.print(Panel(
            f"[red]{error_msg}[/red]",
            title="[bold red]Error[/bold red]",
            border_style="red"
        ))

    elif msg_type == "tool_use":
        # Display tool usage information
        tool_name = message.get("name", "unknown")
        console.print(f"[dim]Using tool: {tool_name}[/dim]")


def get_user_input(console: Console) -> str:
    """
    Get user input with a formatted prompt.

    Args:
        console: Rich Console instance for output

    Returns:
        The user's input string
    """
    console.print("\n[bold green]You:[/bold green] ", end="")
    user_input = input().strip()
    return user_input
