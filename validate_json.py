#!/usr/bin/env python3
import yaml
import json
import sys

def validate_transformation_template():
    """Validate the enhanced transformation template"""
    try:
        # Load the YAML file
        with open('/data/workspace/gigaoffice-server/resources/prompts/system_prompt_spreadsheet_transformation.yaml', 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            print('✓ YAML structure is valid')

        # Validate each example
        examples = data['examples']
        for i, example in enumerate(examples):
            print(f'\nValidating Example {i+1}:')
            try:
                # Parse JSON from the response
                response_json = json.loads(example['response'].strip())
                print(f'  ✓ JSON structure is valid')
                
                # Validate required components
                required_sections = ['metadata', 'worksheet', 'data', 'columns', 'styles']
                for section in required_sections:
                    if section not in response_json:
                        print(f'  ✗ Missing {section} section')
                        return False
                    else:
                        print(f'  ✓ {section} section present')
                
                # Validate styles section
                styles = response_json['styles']
                print(f'  ✓ styles section has {len(styles)} style(s)')
                
                # Collect style IDs
                style_ids = {style['id'] for style in styles}
                print(f'  ✓ Style IDs: {list(style_ids)}')
                
                # Check header style reference
                header = response_json['data']['header']
                if 'style' in header:
                    header_style = header['style']
                    if header_style in style_ids:
                        print(f'  ✓ Header style reference "{header_style}" is valid')
                    else:
                        print(f'  ✗ Header style reference "{header_style}" not found in styles')
                        return False
                
                # Check row style references  
                rows = response_json['data']['rows']
                for j, row in enumerate(rows):
                    if 'style' in row:
                        row_style = row['style']
                        if row_style in style_ids:
                            print(f'  ✓ Row {j+1} style reference "{row_style}" is valid')
                        else:
                            print(f'  ✗ Row {j+1} style reference "{row_style}" not found in styles')
                            return False
                
            except json.JSONDecodeError as e:
                print(f'  ✗ JSON parsing error: {str(e)}')
                return False

        print('\n✓ All validation checks passed successfully!')
        return True
        
    except Exception as e:
        print(f'✗ Validation failed: {str(e)}')
        return False

if __name__ == "__main__":
    success = validate_transformation_template()
    sys.exit(0 if success else 1)