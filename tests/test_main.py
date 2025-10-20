"""
Unit tests for the code review agent module.

These tests use the FakeClaudeService to verify behavior without making
actual API calls to Claude.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from src.code_review_agent import main
from src.claude_service import FakeClaudeService


class TestMainFunction:
    """Test cases for the main() function."""

    @pytest.mark.asyncio
    async def test_main_with_fake_service_file_mode(self):
        """Test that main processes a file review request correctly."""
        # Arrange
        mock_response = Mock()
        mock_response.type = "text"
        mock_response.content = "Code review complete"

        fake_service = FakeClaudeService(mock_responses=[mock_response])

        # Mock command line arguments
        with patch('sys.argv', ['code_review_agent.py', '--file', 'test_file.py', '--stats', 'false']):
            with patch('src.code_review_agent.parse_and_print_message'):
                # Act
                await main(claude_service=fake_service)

                # Assert
                assert fake_service.query_count == 1
                queries = fake_service.get_queries()
                assert len(queries) == 1
                assert "test_file.py" in queries[0]
                assert "comprehensive code review" in queries[0]

    @pytest.mark.asyncio
    async def test_fake_service_records_multiple_queries(self):
        """Test that FakeClaudeService correctly records multiple queries."""
        # Arrange
        fake_service = FakeClaudeService(mock_responses=[])

        # Act
        async with fake_service as service:
            await service.query("First query")
            await service.query("Second query")
            await service.query("Third query")

        # Assert
        queries = fake_service.get_queries()
        assert len(queries) == 3
        assert queries[0] == "First query"
        assert queries[1] == "Second query"
        assert queries[2] == "Third query"
        assert fake_service.query_count == 3

    @pytest.mark.asyncio
    async def test_fake_service_yields_mock_responses(self):
        """Test that FakeClaudeService yields configured mock responses."""
        # Arrange
        mock_responses = [
            {"type": "text", "content": "Response 1"},
            {"type": "text", "content": "Response 2"},
            {"type": "text", "content": "Response 3"}
        ]
        fake_service = FakeClaudeService(mock_responses=mock_responses)

        # Act
        responses = []
        async with fake_service as service:
            # Query 1
            await service.query("Test query 1")
            async for response in service.receive_response():
                responses.append(response)

            # Query 2
            await service.query("Test query 2")
            async for response in service.receive_response():
                responses.append(response)

            # Query 3
            await service.query("Test query 3")
            async for response in service.receive_response():
                responses.append(response)

        # Assert
        assert len(responses) == 3
        assert responses[0]["content"] == "Response 1"
        assert responses[1]["content"] == "Response 2"
        assert responses[2]["content"] == "Response 3"

    @pytest.mark.asyncio
    async def test_fake_service_reset(self):
        """Test that reset() clears the service state."""
        # Arrange
        fake_service = FakeClaudeService(mock_responses=[])

        # Act
        async with fake_service as service:
            await service.query("Query 1")
            await service.query("Query 2")

        assert fake_service.query_count == 2
        assert len(fake_service.get_queries()) == 2

        # Reset
        fake_service.reset()

        # Assert
        assert fake_service.query_count == 0
        assert len(fake_service.get_queries()) == 0

    @pytest.mark.asyncio
    async def test_fake_service_empty_responses(self):
        """Test FakeClaudeService with no mock responses configured."""
        # Arrange
        fake_service = FakeClaudeService()  # No responses

        # Act
        responses = []
        async with fake_service as service:
            await service.query("Test query")
            async for response in service.receive_response():
                responses.append(response)

        # Assert
        assert len(responses) == 0
        assert fake_service.query_count == 1


class TestClaudeServiceIntegration:
    """Integration tests for the service pattern."""

    @pytest.mark.asyncio
    async def test_service_context_manager(self):
        """Test that fake service works as a context manager."""
        # Arrange
        fake_service = FakeClaudeService()

        # Act & Assert
        async with fake_service as service:
            assert service is fake_service
            await service.query("Test")
            # No exception should be raised

    @pytest.mark.asyncio
    async def test_multiple_response_iterations(self):
        """Test that responses are yielded one per query."""
        # Arrange
        mock_responses = [
            {"id": 1, "content": "First"},
            {"id": 2, "content": "Second"}
        ]
        fake_service = FakeClaudeService(mock_responses=mock_responses)

        # Act
        async with fake_service as service:
            # First query/response
            await service.query("Test 1")
            first_iteration = []
            async for response in service.receive_response():
                first_iteration.append(response)

            # Second query/response
            await service.query("Test 2")
            second_iteration = []
            async for response in service.receive_response():
                second_iteration.append(response)

        # Assert
        assert len(first_iteration) == 1
        assert len(second_iteration) == 1
        assert first_iteration[0]["id"] == 1
        assert second_iteration[0]["id"] == 2


def test_fake_service_synchronous_methods():
    """Test synchronous helper methods on FakeClaudeService."""
    # Arrange
    fake_service = FakeClaudeService()

    # Act - Run async code
    async def run_test():
        async with fake_service as service:
            await service.query("Query 1")
            await service.query("Query 2")

    asyncio.run(run_test())

    # Assert
    queries = fake_service.get_queries()
    assert len(queries) == 2
    assert "Query 1" in queries
    assert "Query 2" in queries


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
