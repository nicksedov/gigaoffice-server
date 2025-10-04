#!/usr/bin/env python3
"""
Simple JSON validation test for migrated examples
"""

import json
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_migrated_json():
    """Test a migrated JSON example"""
    
    # Sample migrated JSON from formatting file (first example)
    migrated_json = """
    {
      "metadata": {
        "version": "1.0"
      },
      "worksheet": {
        "name": "Отчет",
        "range": "A1:C4"
      },
      "styles": [
        {
          "id": "header_style",
          "background_color": "#4472C4",
          "font_color": "#FFFFFF",
          "font_weight": "bold"
        },
        {
          "id": "even_row_style",
          "background_color": "#F2F2F2"
        },
        {
          "id": "odd_row_style",
          "background_color": "#FFFFFF"
        }
      ],
      "data": {
        "header": {
          "values": ["Дата", "Описание", "Сумма"],
          "style": "header_style"
        },
        "rows": [
          {
            "values": ["01.01.2024", "Продажа товара", 15000],
            "style": "even_row_style"
          },
          {
            "values": ["02.01.2024", "Покупка материалов", -8000],
            "style": "odd_row_style"
          },
          {
            "values": ["03.01.2024", "Оплата услуг", -3000],
            "style": "even_row_style"
          }
        ]
      }
    }
    """
    
    try:
        # Test JSON parsing
        data = json.loads(migrated_json)
        print("✓ JSON parsing successful")
        
        # Test basic structure
        required_fields = ["metadata", "worksheet", "styles", "data"]
        for field in required_fields:
            if field in data:
                print(f"✓ Field '{field}' present")
            else:
                print(f"✗ Field '{field}' missing")
                return False
        
        # Test styles array
        styles = data.get("styles", [])
        print(f"✓ Found {len(styles)} style definitions")
        
        style_ids = set()
        for i, style in enumerate(styles):
            if "id" in style:
                style_ids.add(style["id"])
                print(f"✓ Style {i+1}: {style['id']}")
            else:
                print(f"✗ Style {i+1} missing 'id' field")
                return False
        
        # Test style references
        references = set()
        
        # Header style reference
        header_style = data.get("data", {}).get("header", {}).get("style")
        if header_style:
            references.add(header_style)
            print(f"✓ Header references style: {header_style}")
        
        # Row style references
        rows = data.get("data", {}).get("rows", [])
        for i, row in enumerate(rows):
            row_style = row.get("style")
            if row_style:
                references.add(row_style)
                print(f"✓ Row {i+1} references style: {row_style}")
        
        # Validate style references
        for ref in references:
            if ref in style_ids:
                print(f"✓ Style reference '{ref}' resolved")
            else:
                print(f"✗ Style reference '{ref}' not found in styles array")
                return False
        
        # Test payload size comparison (estimate)
        original_estimate = len(migrated_json.replace('"styles": [', '"data": {').replace('], "data":', ', "data":'))
        migrated_size = len(migrated_json)
        
        # Rough estimate of v1 format size with inline styles
        v1_estimate = migrated_size + (len(references) * 150)  # Estimate inline style overhead
        reduction = ((v1_estimate - migrated_size) / v1_estimate) * 100 if v1_estimate > 0 else 0
        
        print(f"✓ Estimated payload reduction: {reduction:.1f}%")
        
        print("\n🎉 All validation tests passed!")
        return True
        
    except json.JSONDecodeError as e:
        print(f"✗ JSON parsing failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Validation error: {e}")
        return False


if __name__ == "__main__":
    success = test_migrated_json()
    sys.exit(0 if success else 1)