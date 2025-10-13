"""
Example script demonstrating programmatic usage of the code analysis system.
"""

from code_analysis.analyzer import CodeAnalyzer
from pathlib import Path

def main():
    # Get project root
    project_root = Path(__file__).parent
    
    print("="*80)
    print("Code Analysis System - Example Usage")
    print("="*80)
    print()
    
    # Initialize analyzer
    print("Initializing analyzer...")
    config_path = project_root / "code_analysis" / "config.yaml"
    analyzer = CodeAnalyzer(
        project_root=str(project_root / "app"),
        config_path=str(config_path) if config_path.exists() else None
    )
    
    # Run analysis
    print("Running analysis...")
    print()
    result = analyzer.analyze()
    
    print()
    print("="*80)
    print("Generating Report")
    print("="*80)
    print()
    
    # Generate console report
    analyzer.generate_console_report(result)
    
    # Save JSON report
    output_path = project_root / "code_analysis_report.json"
    analyzer.save_json_report(result, str(output_path))
    
    print()
    print("="*80)
    print("Statistics")
    print("="*80)
    stats = analyzer.get_statistics()
    
    print("Import Statistics:")
    import_stats = stats.get('import_statistics', {})
    print(f"  Total imports: {import_stats.get('total_imports', 0)}")
    print(f"  Files with imports: {import_stats.get('files_with_imports', 0)}")
    
    if 'import_types' in import_stats:
        print("  Import types:")
        for itype, count in import_stats['import_types'].items():
            print(f"    {itype}: {count}")
    
    print()
    print(f"Analysis complete! Report saved to: {output_path}")

if __name__ == "__main__":
    main()
