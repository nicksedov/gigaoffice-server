"""
Custom JSON Encoder
Handles datetime serialization for JSON operations
"""

import json
from datetime import datetime
from typing import Any

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects"""
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)