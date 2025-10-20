"""
Claude Service Interface and Implementations

This module provides an abstraction layer over the Claude SDK to enable
dependency injection and easier testing.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Dict, Any
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions


class IClaudeService(ABC):
    """
    Interface for Claude service interactions.

    This abstraction allows for easy testing by providing a contract
    that both real and fake implementations must follow.
    """

    @abstractmethod
    async def query(self, prompt: str) -> None:
        """
        Send a query to Claude.

        Args:
            prompt: The text prompt to send to Claude
        """
        pass

    @abstractmethod
    async def receive_response(self) -> AsyncIterator[Any]:
        """
        Receive streaming responses from Claude.

        Yields:
            Message objects from Claude's response stream
        """
        pass

    @abstractmethod
    async def __aenter__(self):
        """Context manager entry."""
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass


class ClaudeServiceImpl(IClaudeService):
    """
    Real implementation of IClaudeService using the Claude SDK.

    This wraps the actual ClaudeSDKClient and delegates all calls to it.
    """

    def __init__(self, options: ClaudeAgentOptions):
        """
        Initialize the Claude service.

        Args:
            options: Configuration options for the Claude SDK client
        """
        self.options = options
        self.client: Optional[ClaudeSDKClient] = None

    async def query(self, prompt: str) -> None:
        """Send a query to Claude using the SDK client."""
        if self.client is None:
            raise RuntimeError("Service not initialized. Use async context manager.")
        await self.client.query(prompt)

    async def receive_response(self) -> AsyncIterator[Any]:
        """Receive streaming responses from Claude."""
        if self.client is None:
            raise RuntimeError("Service not initialized. Use async context manager.")
        async for message in self.client.receive_response():
            yield message

    async def __aenter__(self):
        """Initialize the SDK client when entering context."""
        self.client = ClaudeSDKClient(options=self.options)
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up the SDK client when exiting context."""
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
            self.client = None


class FakeClaudeService(IClaudeService):
    """
    Fake implementation of IClaudeService for testing.

    This allows tests to run without making actual API calls to Claude.
    Responses can be pre-configured for different test scenarios.
    """

    def __init__(self, mock_responses: Optional[list] = None):
        """
        Initialize the fake service.

        Args:
            mock_responses: List of mock response messages to return.
                          If None, returns empty responses.
        """
        self.mock_responses = mock_responses or []
        self.queries_received: list[str] = []
        self.query_count = 0
        self.response_index = 0

    async def query(self, prompt: str) -> None:
        """
        Record the query for testing verification.

        Args:
            prompt: The query text (recorded but not sent anywhere)
        """
        self.queries_received.append(prompt)
        self.query_count += 1

    async def receive_response(self) -> AsyncIterator[Any]:
        """
        Yield pre-configured mock responses one at a time per query.

        Yields:
            Mock message objects configured during initialization
        """
        # Yield the next response if available
        if self.response_index < len(self.mock_responses):
            yield self.mock_responses[self.response_index]
            self.response_index += 1

    async def __aenter__(self):
        """No-op for fake service."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """No-op for fake service."""
        pass

    def get_queries(self) -> list[str]:
        """
        Get all queries received by this fake service.

        Returns:
            List of query strings received
        """
        return self.queries_received.copy()

    def reset(self) -> None:
        """Reset the fake service state."""
        self.queries_received.clear()
        self.response_index = 0
        self.query_count = 0
