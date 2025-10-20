"""
Sample class that demonstrates various refactoring scenarios.
This file can be used to test the refactoring agent.
"""

import os
import requests
from typing import Dict, List, Any


class DataProcessor:
    """A class that processes data from various sources."""

    def __init__(self):
        """Initialize the data processor."""
        self.api_key = os.getenv('API_KEY')
        self.base_url = os.environ.get('BASE_URL', 'https://api.example.com')
        self.timeout = int(os.getenv('TIMEOUT', '30'))
        self.data_cache = {}
        self.processed_count = 0

    def fetch_data(self, endpoint: str) -> Dict[str, Any]:
        """Fetch data from an external API."""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Authorization': f'Bearer {self.api_key}'}

        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        self.data_cache[endpoint] = data
        return data

    def process_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of items - this is the main business logic."""
        processed = []

        for item in items:
            # Apply transformations
            processed_item = {
                'id': item.get('id'),
                'name': item.get('name', '').upper(),
                'value': item.get('value', 0) * 2,
                'processed_at': self._get_timestamp()
            }

            # Validate the item
            if self.validate_item(processed_item):
                processed.append(processed_item)
                self.processed_count += 1

        return processed

    def validate_item(self, item: Dict[str, Any]) -> bool:
        """Validate a single item."""
        if not item.get('id'):
            return False
        if not item.get('name'):
            return False
        if item.get('value', 0) < 0:
            return False
        return True

    def save_to_database(self, data: List[Dict[str, Any]]) -> bool:
        """Save processed data to database."""
        db_url = os.getenv('DATABASE_URL')

        # Simulating database save with external HTTP call
        response = requests.post(
            f"{db_url}/save",
            json={'data': data},
            timeout=30
        )

        return response.status_code == 200

    def generate_report(self, data: List[Dict[str, Any]]) -> str:
        """Generate a summary report of the processed data."""
        if not data:
            return "No data to report"

        report = f"Processed {len(data)} items\n"
        report += f"Total items processed: {self.processed_count}\n"

        # Calculate statistics
        total_value = sum(item.get('value', 0) for item in data)
        avg_value = total_value / len(data) if data else 0

        report += f"Total value: {total_value}\n"
        report += f"Average value: {avg_value:.2f}\n"

        return report

    def cleanup_cache(self) -> None:
        """Clean up the internal cache."""
        self.data_cache.clear()
        self.processed_count = 0

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()

    @staticmethod
    def format_output(data: Any) -> str:
        """Format data for output."""
        import json
        return json.dumps(data, indent=2)

    @classmethod
    def from_config(cls, config_path: str) -> 'DataProcessor':
        """Create an instance from a configuration file."""
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Set environment variables from config
        for key, value in config.items():
            os.environ[key] = str(value)

        return cls()