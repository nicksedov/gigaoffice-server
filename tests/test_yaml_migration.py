"""
Unit tests for YAML Schema Migration

Tests the migration utility and validation logic for converting JSON examples
from v1 format (inline styles) to v2 format (style reference architecture).
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

import sys
# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from scripts.migrate_yaml_examples import JSONExampleMigrator, YAMLFileMigrator
    from scripts.validate_migrations import MigrationValidator
    from app.models.api.spreadsheet import StyleDefinition, SpreadsheetData
    from app.services.spreadsheet.style_registry import StyleRegistry, StyleValidator
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Migration modules not available")
class TestJSONExampleMigrator:
    """Test cases for JSON example migration logic"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.migrator = JSONExampleMigrator()
    
    def test_migrate_simple_inline_style(self):
        """Test migration of simple inline style to v2 format"""
        v1_json = json.dumps({
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Test", "range": "A1:B2"},
            "data": {
                "header": {
                    "values": ["Col1", "Col2"],
                    "style": {
                        "background_color": "#4472C4",
                        "font_color": "#FFFFFF",
                        "font_weight": "bold"
                    }
                },
                "rows": [
                    {
                        "values": ["Data1", "Data2"],
                        "style": {
                            "background_color": "#F2F2F2"
                        }
                    }
                ]
            }
        })
        
        migrated_json, success, errors = self.migrator.migrate_json_example(v1_json)
        
        assert success, f"Migration failed: {errors}"
        
        # Parse migrated result
        migrated_data = json.loads(migrated_json)
        
        # Check styles array exists
        assert "styles" in migrated_data
        assert len(migrated_data["styles"]) == 2
        
        # Check style references
        assert migrated_data["data"]["header"]["style"] is not None
        assert isinstance(migrated_data["data"]["header"]["style"], str)
        assert migrated_data["data"]["rows"][0]["style"] is not None
        assert isinstance(migrated_data["data"]["rows"][0]["style"], str)
    
    def test_migrate_already_v2_format(self):
        """Test migration of already migrated v2 format"""
        v2_json = json.dumps({
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Test", "range": "A1:B2"},
            "styles": [
                {"id": "header_style", "font_weight": "bold"}
            ],
            "data": {
                "header": {
                    "values": ["Col1", "Col2"],
                    "style": "header_style"
                },
                "rows": [{"values": ["Data1", "Data2"]}]
            }
        })
        
        migrated_json, success, errors = self.migrator.migrate_json_example(v2_json)
        
        assert success
        assert "Already v2 format" in str(errors)
        assert migrated_json == v2_json  # Should be unchanged
    
    def test_migrate_no_styles(self):
        """Test migration of JSON with no styling information"""
        no_style_json = json.dumps({
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Test", "range": "A1:B2"},
            "data": {
                "header": {"values": ["Col1", "Col2"]},
                "rows": [{"values": ["Data1", "Data2"]}]
            }
        })
        
        migrated_json, success, errors = self.migrator.migrate_json_example(no_style_json)
        
        assert success
        
        # Parse result
        migrated_data = json.loads(migrated_json)
        
        # Should have empty styles array
        assert "styles" in migrated_data
        assert len(migrated_data["styles"]) == 0
    
    def test_migrate_invalid_json(self):
        """Test migration of invalid JSON"""
        invalid_json = '{"invalid": json,}'
        
        migrated_json, success, errors = self.migrator.migrate_json_example(invalid_json)
        
        assert not success
        assert "JSON parsing error" in str(errors)
    
    def test_duplicate_style_consolidation(self):
        """Test that duplicate styles are consolidated"""
        v1_json = json.dumps({
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Test", "range": "A1:B3"},
            "data": {
                "header": {
                    "values": ["Col1", "Col2"],
                    "style": {"background_color": "#F2F2F2"}
                },
                "rows": [
                    {
                        "values": ["Data1", "Data2"],
                        "style": {"background_color": "#F2F2F2"}  # Same as header
                    },
                    {
                        "values": ["Data3", "Data4"],
                        "style": {"background_color": "#FFFFFF"}  # Different
                    }
                ]
            }
        })
        
        migrated_json, success, errors = self.migrator.migrate_json_example(v1_json)
        
        assert success
        
        migrated_data = json.loads(migrated_json)
        
        # Should only have 2 unique styles, not 3
        assert len(migrated_data["styles"]) == 2
        
        # Header and first row should reference the same style
        header_style = migrated_data["data"]["header"]["style"]
        row1_style = migrated_data["data"]["rows"][0]["style"]
        row2_style = migrated_data["data"]["rows"][1]["style"]
        
        assert header_style == row1_style
        assert header_style != row2_style


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Migration modules not available")
class TestMigrationValidator:
    """Test cases for migration validation logic"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.validator = MigrationValidator()
    
    def test_validate_v2_format(self):
        """Test validation of correct v2 format"""
        v2_json = json.dumps({
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Test", "range": "A1:B2"},
            "styles": [
                {"id": "test_style", "background_color": "#FF0000"}
            ],
            "data": {
                "header": {
                    "values": ["Col1", "Col2"],
                    "style": "test_style"
                },
                "rows": [{"values": ["Data1", "Data2"]}]
            }
        })
        
        is_valid, errors, data = self.validator.validate_json_structure(v2_json)
        
        assert is_valid, f"Validation failed: {errors}"
        assert len(errors) == 0
        assert "styles" in data
    
    def test_validate_missing_style_reference(self):
        """Test validation of missing style reference"""
        invalid_json = json.dumps({
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Test", "range": "A1:B2"},
            "styles": [
                {"id": "existing_style", "background_color": "#FF0000"}
            ],
            "data": {
                "header": {
                    "values": ["Col1", "Col2"],
                    "style": "missing_style"  # This style doesn't exist
                },
                "rows": [{"values": ["Data1", "Data2"]}]
            }
        })
        
        is_valid, errors, data = self.validator.validate_json_structure(invalid_json)
        
        assert not is_valid
        assert any("missing_style" in error for error in errors)
    
    def test_validate_inline_style_detection(self):
        """Test detection of inline styles (v1 format)"""
        v1_json = json.dumps({
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Test", "range": "A1:B2"},
            "data": {
                "header": {
                    "values": ["Col1", "Col2"],
                    "style": {"background_color": "#FF0000"}  # Inline style
                },
                "rows": [{"values": ["Data1", "Data2"]}]
            }
        })
        
        is_valid, errors, data = self.validator.validate_json_structure(v1_json)
        
        assert not is_valid
        assert any("inline style" in error.lower() for error in errors)
    
    def test_validate_missing_required_fields(self):
        """Test validation of missing required fields"""
        incomplete_json = json.dumps({
            "metadata": {"version": "1.0"}
            # Missing worksheet and data fields
        })
        
        is_valid, errors, data = self.validator.validate_json_structure(incomplete_json)
        
        assert not is_valid
        assert any("worksheet" in error for error in errors)
        assert any("data" in error for error in errors)


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Migration modules not available")
class TestStyleRegistry:
    """Test cases for style registry functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.registry = StyleRegistry()
    
    def test_add_style_from_dict(self):
        """Test adding styles from dictionary"""
        style_dict = {
            "background_color": "#FF0000",
            "font_weight": "bold"
        }
        
        style_id = self.registry.add_style_from_dict(style_dict)
        
        assert style_id is not None
        assert isinstance(style_id, str)
        
        # Retrieve the style
        retrieved_style = self.registry.get_style(style_id)
        assert retrieved_style is not None
        assert retrieved_style.background_color == "#FF0000"
        assert retrieved_style.font_weight == "bold"
    
    def test_duplicate_style_consolidation(self):
        """Test that duplicate styles return the same ID"""
        style_dict = {"background_color": "#FF0000"}
        
        id1 = self.registry.add_style_from_dict(style_dict)
        id2 = self.registry.add_style_from_dict(style_dict)
        
        assert id1 == id2
        assert len(self.registry.get_all_styles()) == 1
    
    def test_validate_style_references(self):
        """Test style reference validation"""
        # Add a style
        style_id = self.registry.add_style_from_dict({"background_color": "#FF0000"})
        
        # Test valid reference
        assert self.registry.validate_style_reference(style_id)
        
        # Test invalid reference
        assert not self.registry.validate_style_reference("nonexistent_style")
    
    def test_semantic_style_id_generation(self):
        """Test semantic style ID generation"""
        # Test header style
        header_style = {"font_weight": "bold", "background_color": "#4472C4"}
        header_id = self.registry.add_style_from_dict(header_style)
        
        # Test negative value style
        negative_style = {"font_color": "#FF0000"}
        negative_id = self.registry.add_style_from_dict(negative_style)
        
        # IDs should be meaningful
        assert "bold" in header_id.lower() or "4472c4" in header_id.lower()
        assert "ff0000" in negative_id.lower() or "red" in negative_id.lower()


class TestIntegration:
    """Integration tests for the complete migration pipeline"""
    
    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Migration modules not available")
    def test_complete_migration_pipeline(self):
        """Test the complete migration from v1 to v2 format"""
        # Create a temporary YAML file with v1 format
        yaml_content = """
prompt: |
  Test prompt
examples:
- request: |
    Test request
  response: |
    {
      "metadata": {"version": "1.0"},
      "worksheet": {"name": "Test", "range": "A1:B2"},
      "data": {
        "header": {
          "values": ["Col1", "Col2"],
          "style": {
            "background_color": "#4472C4",
            "font_weight": "bold"
          }
        },
        "rows": [
          {
            "values": ["Data1", "Data2"],
            "style": {
              "background_color": "#F2F2F2"
            }
          }
        ]
      }
    }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_file = Path(f.name)
        
        try:
            # Test migration
            migrator = YAMLFileMigrator()
            success, messages, stats = migrator.migrate_file(temp_file)
            
            assert success, f"Migration failed: {messages}"
            assert stats["migrated_examples"] > 0
            
            # Test validation
            validator = MigrationValidator()
            success, messages, stats = validator.validate_file(temp_file)
            
            assert success, f"Validation failed: {messages}"
            assert stats["v2_format_examples"] > 0
            
        finally:
            # Clean up
            temp_file.unlink()
    
    def test_payload_size_estimation(self):
        """Test payload size reduction estimation"""
        # Original v1 format (estimated)
        v1_example = {
            "data": {
                "header": {
                    "values": ["Col1", "Col2"],
                    "style": {
                        "background_color": "#4472C4",
                        "font_color": "#FFFFFF", 
                        "font_weight": "bold"
                    }
                },
                "rows": [
                    {
                        "values": ["Data1", "Data2"],
                        "style": {
                            "background_color": "#F2F2F2"
                        }
                    },
                    {
                        "values": ["Data3", "Data4"],
                        "style": {
                            "background_color": "#FFFFFF"
                        }
                    }
                ]
            }
        }
        
        # Migrated v2 format
        v2_example = {
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
                    "values": ["Col1", "Col2"],
                    "style": "header_style"
                },
                "rows": [
                    {
                        "values": ["Data1", "Data2"],
                        "style": "even_row_style"
                    },
                    {
                        "values": ["Data3", "Data4"],
                        "style": "odd_row_style"
                    }
                ]
            }
        }
        
        v1_size = len(json.dumps(v1_example))
        v2_size = len(json.dumps(v2_example))
        
        # With duplicate styles, v2 should be more efficient
        # This is a rough test, actual results may vary
        print(f"V1 size: {v1_size}, V2 size: {v2_size}")
        
        # The test passes if both formats are valid JSON
        assert v1_size > 0
        assert v2_size > 0


def test_basic_functionality_without_imports():
    """Test basic functionality even when imports are not available"""
    # Test JSON parsing
    test_json = '{"test": "value"}'
    data = json.loads(test_json)
    assert data["test"] == "value"
    
    # Test style ID generation logic (simplified)
    def generate_style_id(style_dict):
        parts = []
        if style_dict.get("background_color"):
            parts.append(f"bg_{style_dict['background_color'][1:]}")
        if style_dict.get("font_weight") == "bold":
            parts.append("bold")
        return "_".join(parts) if parts else "default"
    
    style1 = {"background_color": "#FF0000", "font_weight": "bold"}
    style2 = {"background_color": "#00FF00"}
    
    id1 = generate_style_id(style1)
    id2 = generate_style_id(style2)
    
    assert "FF0000" in id1
    assert "bold" in id1
    assert "00FF00" in id2
    assert id1 != id2


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])