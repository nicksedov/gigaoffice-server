"""
Pytest configuration file
"""

import sys
import os
from pathlib import Path

# Add the app directory to the Python path
app_path = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_path))

import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="session")
def client():
    """Create a TestClient for the FastAPI app"""
    with TestClient(app) as client:
        yield client

@pytest.fixture(scope="session")
def sample_spreadsheet_data():
    """Sample spreadsheet data for testing"""
    return {
        "metadata": {
            "version": "1.0",
            "format": "enhanced-spreadsheet-data",
            "plugin_id": "test-plugin"
        },
        "worksheet": {
            "name": "TestSheet",
            "range": "A1",
            "options": {
                "auto_resize_columns": True,
                "freeze_headers": True,
                "auto_filter": True
            }
        },
        "data": {
            "headers": {
                "values": ["Product", "Q1 Sales", "Q2 Sales"]
            },
            "rows": [
                {
                    "values": ["Product A", 1000, 1200]
                },
                {
                    "values": ["Product B", 800, 900]
                }
            ]
        },
        "columns": [
            {
                "index": 0,
                "name": "Product",
                "type": "string",
                "format": "text"
            },
            {
                "index": 1,
                "name": "Q1 Sales",
                "type": "number",
                "format": "#,##0"
            },
            {
                "index": 2,
                "name": "Q2 Sales",
                "type": "number",
                "format": "#,##0"
            }
        ],
        "styles": {
            "default": {
                "font_family": "Arial",
                "font_size": 10,
                "font_color": "#000000",
                "background_color": "#FFFFFF"
            },
            "header": {
                "font_weight": "bold",
                "font_size": 12,
                "background_color": "#4472C4",
                "font_color": "#FFFFFF"
            }
        },
        "formulas": [],
        "charts": []
    }