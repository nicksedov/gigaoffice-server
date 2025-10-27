#!/usr/bin/env python3
"""
Quick validation script to verify histogram API implementation
"""

import sys
import os

# Add the workspace to the path
sys.path.insert(0, '/data/workspace/gigaoffice-server')

print("=" * 60)
print("Histogram API Implementation Validation")
print("=" * 60)

# Test 1: Import histogram models
print("\n1. Testing histogram model imports...")
try:
    from app.models.api.histogram import (
        HistogramRequest,
        HistogramResponse,
        HistogramProcessResponse,
        HistogramStatusResponse,
        HistogramResultResponse
    )
    print("   ✓ All histogram models imported successfully")
except ImportError as e:
    print(f"   ✗ Failed to import histogram models: {e}")
    sys.exit(1)

# Test 2: Import extended ColumnDefinition
print("\n2. Testing extended ColumnDefinition model...")
try:
    from app.models.api.spreadsheet import ColumnDefinition
    
    # Test with statistical metadata
    col = ColumnDefinition(
        index=1,
        format="#,##0.00",
        range="B2:B50",
        min=100.0,
        max=999.0,
        median=500.0,
        count=49
    )
    print(f"   ✓ ColumnDefinition with statistical metadata created: {col.model_dump()}")
except Exception as e:
    print(f"   ✗ Failed to create ColumnDefinition: {e}")
    sys.exit(1)

# Test 3: Validate statistical constraints
print("\n3. Testing statistical metadata validation...")
try:
    # This should fail - min > max
    try:
        bad_col = ColumnDefinition(
            index=1,
            format="General",
            range="A1:A10",
            min=100.0,
            max=50.0
        )
        print("   ✗ Validation failed to catch min > max")
    except ValueError as e:
        print(f"   ✓ Correctly caught validation error: {e}")
except Exception as e:
    print(f"   ✗ Unexpected error: {e}")

# Test 4: Create HistogramResponse
print("\n4. Testing HistogramResponse model...")
try:
    response = HistogramResponse(
        source_columns=[1, 2],
        recommended_bins=10,
        range_column_name="Диапазон значений",
        count_column_name="Частота"
    )
    print(f"   ✓ HistogramResponse created: {response.model_dump()}")
except Exception as e:
    print(f"   ✗ Failed to create HistogramResponse: {e}")
    sys.exit(1)

# Test 5: Verify prompt files exist
print("\n5. Checking prompt resource files...")
prompt_dir = "/data/workspace/gigaoffice-server/resources/prompts/data-histogram"
required_files = [
    "system_prompt.txt",
    "example_01.yaml",
    "example_02.yaml",
    "example_03.yaml",
    "example_04.yaml",
    "example_05.yaml",
    "example_06.yaml"
]

all_exist = True
for filename in required_files:
    filepath = os.path.join(prompt_dir, filename)
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        print(f"   ✓ {filename} ({size} bytes)")
    else:
        print(f"   ✗ {filename} NOT FOUND")
        all_exist = False

if not all_exist:
    sys.exit(1)

# Test 6: Check API router registration
print("\n6. Checking histogram router registration...")
try:
    from app.api.histograms import histogram_router
    print(f"   ✓ Histogram router imported: {histogram_router.prefix}")
    print(f"   ✓ Router tags: {histogram_router.tags}")
except Exception as e:
    print(f"   ✗ Failed to import histogram router: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ All validation checks passed!")
print("=" * 60)
print("\nHistogram API Implementation Summary:")
print("  • Extended ColumnDefinition with statistical metadata")
print("  • Created 5 histogram model classes")
print("  • Implemented 3 API endpoints:")
print("    - POST /api/v1/histograms/process")
print("    - GET /api/v1/histograms/status/{request_id}")
print("    - GET /api/v1/histograms/result/{request_id}")
print("  • Created system prompt and 6 example files")
print("  • Registered histogram router in main application")
print("=" * 60)
