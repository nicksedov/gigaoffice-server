#!/usr/bin/env python3
"""
Command-line interface for the code analysis system.

Provides a user-friendly CLI for running code analysis with various options
and output formats.
"""

import sys
import argparse
from pathlib import Path
from code_analysis.analyzer import CodeAnalyzer


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description='Code Analysis Tool - Detect unused imports and type errors',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze current directory
  python -m code_analysis.cli
  
  # Analyze specific directory
  python -m code_analysis.cli /path/to/project
  
  # Save results as JSON
  python -m code_analysis.cli --output report.json
  
  # Use custom configuration
  python -m code_analysis.cli --config custom_config.yaml
  
  # Disable parallel processing
  python -m code_analysis.cli --no-parallel
        """
    )
    
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Path to the project directory to analyze (default: current directory)'
    )
    
    parser.add_argument(
        '-c', '--config',
        dest='config_path',
        help='Path to configuration YAML file'
    )
    
    parser.add_argument(
        '-o', '--output',
        dest='output_path',
        help='Path to save JSON report (optional)'
    )
    
    parser.add_argument(
        '--format',
        choices=['console', 'json', 'both'],
        default='console',
        help='Output format (default: console)'
    )
    
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output'
    )
    
    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='Disable parallel processing'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress progress messages'
    )
    
    parser.add_argument(
        '--exclude-dirs',
        nargs='+',
        help='Additional directories to exclude from analysis'
    )
    
    parser.add_argument(
        '--check-types',
        action='store_true',
        default=True,
        help='Enable type annotation checking (default: enabled)'
    )
    
    parser.add_argument(
        '--no-check-types',
        dest='check_types',
        action='store_false',
        help='Disable type annotation checking'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Code Analysis Tool 1.0.0'
    )
    
    args = parser.parse_args()
    
    # Validate path
    project_path = Path(args.path).resolve()
    if not project_path.exists():
        print(f"Error: Path does not exist: {project_path}", file=sys.stderr)
        sys.exit(1)
    
    if not project_path.is_dir():
        print(f"Error: Path is not a directory: {project_path}", file=sys.stderr)
        sys.exit(1)
    
    # Determine config path
    config_path = args.config_path
    if not config_path:
        # Look for config in project directory
        default_config = project_path / 'code_analysis' / 'config.yaml'
        if default_config.exists():
            config_path = str(default_config)
    
    try:
        # Initialize analyzer
        analyzer = CodeAnalyzer(str(project_path), config_path)
        
        # Apply CLI overrides to configuration
        if args.no_color:
            analyzer.config.set('report.color_output', False)
        
        if args.no_parallel:
            analyzer.config.set('performance.parallel_processing', False)
        
        if args.verbose:
            analyzer.config.set('report.verbose', True)
        
        if args.exclude_dirs:
            current_excludes = analyzer.config.get_excluded_directories()
            analyzer.config.set('exclude_directories', current_excludes + args.exclude_dirs)
        
        if not args.check_types:
            analyzer.config.set('analysis_rules.check_type_annotations', False)
        
        # Suppress output if quiet mode
        if args.quiet:
            import os
            sys.stdout = open(os.devnull, 'w')
        
        # Run analysis
        result = analyzer.analyze()
        
        # Restore stdout if it was suppressed
        if args.quiet:
            sys.stdout = sys.__stdout__
        
        # Generate reports
        if args.format in ('console', 'both'):
            analyzer.generate_console_report(result)
        
        if args.output_path or args.format in ('json', 'both'):
            output_path = args.output_path or 'code_analysis_report.json'
            analyzer.save_json_report(result, output_path)
        
        # Exit with appropriate code
        total_issues = result.summary.total_unused_imports + result.summary.total_type_errors
        if total_issues > 0:
            sys.exit(1)  # Non-zero exit code if issues found
        else:
            sys.exit(0)
    
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user", file=sys.stderr)
        sys.exit(130)
    
    except Exception as e:
        print(f"Error during analysis: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(2)


if __name__ == '__main__':
    main()
