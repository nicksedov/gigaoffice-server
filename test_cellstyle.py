"""Test script to verify CellStyle implementation"""

from app.models.api.spreadsheet import CellStyle, HeaderData, DataRow

def test_cellstyle_creation():
    """Test creating CellStyle instances"""
    # Test creating a CellStyle with all properties
    style = CellStyle(
        background_color="#FFFFFF",
        font_color="#000000",
        font_weight="bold",
        font_size=12,
        font_style="italic",
        horizontal_alignment="center",
        vertical_alignment="middle"
    )
    
    print("CellStyle created successfully:")
    print(f"Background color: {style.background_color}")
    print(f"Font color: {style.font_color}")
    print(f"Font weight: {style.font_weight}")
    print(f"Font size: {style.font_size}")
    print(f"Font style: {style.font_style}")
    print(f"Horizontal alignment: {style.horizontal_alignment}")
    print(f"Vertical alignment: {style.vertical_alignment}")
    
    # Test creating HeaderData with CellStyle
    header = HeaderData(
        values=["Name", "Age", "City"],
        style=style
    )
    
    print("\nHeaderData with CellStyle created successfully:")
    print(f"Header values: {header.values}")
    print(f"Header style background color: {header.style.background_color}")
    
    # Test creating DataRow with CellStyle
    row = DataRow(
        values=["John", 30, "New York"],
        style=style
    )
    
    print("\nDataRow with CellStyle created successfully:")
    print(f"Row values: {row.values}")
    print(f"Row style font weight: {row.style.font_weight}")

if __name__ == "__main__":
    test_cellstyle_creation()
    print("\nAll tests passed!")