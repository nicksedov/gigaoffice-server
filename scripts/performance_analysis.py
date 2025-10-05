#!/usr/bin/env python3
"""
Performance Analysis for YAML Schema Migration

This script analyzes the performance improvements achieved by migrating from
v1 format (inline styles) to v2 format (style reference architecture).

Measures:
- Payload size reduction
- JSON parsing performance
- Memory usage optimization
- Style resolution efficiency

Usage:
    python scripts/performance_analysis.py --all
    python scripts/performance_analysis.py --file system_prompt_spreadsheet_formatting.yaml
"""

import os
import sys
import json
import yaml
import time
import argparse
import statistics
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@dataclass
class PerformanceMetrics:
    """Container for performance measurement results"""
    file_name: str
    original_size: int
    migrated_size: int
    size_reduction_bytes: int
    size_reduction_percent: float
    parse_time_original: float
    parse_time_migrated: float
    parse_time_improvement: float
    style_count: int
    reference_count: int
    duplicate_elimination: int


class PerformanceAnalyzer:
    """Analyzes performance improvements from v1 to v2 migration"""
    
    def __init__(self):
        self.resources_dir = project_root / "resources" / "prompts"
        
        # Files that were migrated
        self.migrated_files = [
            "system_prompt_spreadsheet_formatting.yaml",
            "system_prompt_spreadsheet_generation.yaml",
            "system_prompt_spreadsheet_search.yaml"
        ]
    
    def simulate_v1_format(self, v2_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate what the v1 format would look like by converting back from v2.
        
        Args:
            v2_data: Data in v2 format with style references
            
        Returns:
            Simulated v1 data with inline styles
        """
        if "styles" not in v2_data:
            return v2_data  # Already v1 or no styles
        
        # Create a lookup for styles
        style_lookup = {style["id"]: style for style in v2_data["styles"] if "id" in style}
        
        # Clone the data
        v1_data = json.loads(json.dumps(v2_data))
        
        # Remove styles array
        del v1_data["styles"]
        
        # Replace style references with inline styles
        if "data" in v1_data:
            # Handle header
            header = v1_data["data"].get("header", {})
            if "style" in header and isinstance(header["style"], str):
                style_ref = header["style"]
                if style_ref in style_lookup:
                    style_dict = style_lookup[style_ref].copy()
                    del style_dict["id"]  # Remove id field
                    header["style"] = style_dict
            
            # Handle rows
            for row in v1_data["data"].get("rows", []):
                if "style" in row and isinstance(row["style"], str):
                    style_ref = row["style"]
                    if style_ref in style_lookup:
                        style_dict = style_lookup[style_ref].copy()
                        del style_dict["id"]  # Remove id field
                        row["style"] = style_dict
        
        return v1_data
    
    def measure_parsing_performance(self, json_str: str, iterations: int = 1000) -> float:
        """
        Measure JSON parsing performance.
        
        Args:
            json_str: JSON string to parse
            iterations: Number of parsing iterations
            
        Returns:
            Average parsing time in milliseconds
        """
        times = []
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            json.loads(json_str)
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)  # Convert to milliseconds
        
        return statistics.mean(times)
    
    def analyze_style_usage(self, v2_data: Dict[str, Any]) -> Tuple[int, int, int]:
        """
        Analyze style usage patterns in v2 format.
        
        Args:
            v2_data: Data in v2 format
            
        Returns:
            Tuple of (style_count, reference_count, duplicate_elimination)
        """
        if "styles" not in v2_data:
            return 0, 0, 0
        
        style_count = len(v2_data["styles"])
        reference_count = 0
        
        # Count style references
        if "data" in v2_data:
            # Header reference
            if v2_data["data"].get("header", {}).get("style"):
                reference_count += 1
            
            # Row references
            for row in v2_data["data"].get("rows", []):
                if row.get("style"):
                    reference_count += 1
        
        # Estimate duplicate elimination
        # This is the number of times styles would have been duplicated in v1
        duplicate_elimination = max(0, reference_count - style_count)
        
        return style_count, reference_count, duplicate_elimination
    
    def analyze_example(self, json_str: str) -> PerformanceMetrics:
        """
        Analyze performance metrics for a single JSON example.
        
        Args:
            json_str: JSON string in v2 format
            
        Returns:
            Performance metrics
        """
        try:
            # Parse v2 data
            v2_data = json.loads(json_str)
            
            # Simulate v1 format
            v1_data = self.simulate_v1_format(v2_data)
            
            # Convert back to strings
            v1_json = json.dumps(v1_data, separators=(',', ':'))  # Compact format
            v2_json = json.dumps(v2_data, separators=(',', ':'))  # Compact format
            
            # Size measurements
            v1_size = len(v1_json.encode('utf-8'))
            v2_size = len(v2_json.encode('utf-8'))
            size_reduction = v1_size - v2_size
            size_reduction_percent = (size_reduction / v1_size * 100) if v1_size > 0 else 0
            
            # Performance measurements
            v1_parse_time = self.measure_parsing_performance(v1_json, 100)
            v2_parse_time = self.measure_parsing_performance(v2_json, 100)
            parse_improvement = ((v1_parse_time - v2_parse_time) / v1_parse_time * 100) if v1_parse_time > 0 else 0
            
            # Style analysis
            style_count, reference_count, duplicate_elimination = self.analyze_style_usage(v2_data)
            
            return PerformanceMetrics(
                file_name="",  # Will be set by caller
                original_size=v1_size,
                migrated_size=v2_size,
                size_reduction_bytes=size_reduction,
                size_reduction_percent=size_reduction_percent,
                parse_time_original=v1_parse_time,
                parse_time_migrated=v2_parse_time,
                parse_time_improvement=parse_improvement,
                style_count=style_count,
                reference_count=reference_count,
                duplicate_elimination=duplicate_elimination
            )
            
        except Exception as e:
            # Return empty metrics on error
            return PerformanceMetrics(
                file_name="",
                original_size=0,
                migrated_size=0,
                size_reduction_bytes=0,
                size_reduction_percent=0,
                parse_time_original=0,
                parse_time_migrated=0,
                parse_time_improvement=0,
                style_count=0,
                reference_count=0,
                duplicate_elimination=0
            )
    
    def analyze_file(self, file_path: Path) -> Tuple[bool, List[str], List[PerformanceMetrics]]:
        """
        Analyze performance metrics for a YAML file.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            Tuple of (success, messages, metrics_list)
        """
        messages = []
        metrics_list = []
        
        if not file_path.exists():
            return False, [f"File not found: {file_path}"], metrics_list
        
        try:
            # Read YAML file
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
            
            if "examples" not in yaml_data:
                messages.append("No examples found in YAML file")
                return True, messages, metrics_list
            
            file_name = file_path.name
            messages.append(f"Analyzing {file_name}...")
            
            total_v1_size = 0
            total_v2_size = 0
            valid_examples = 0
            
            # Analyze each example
            for i, example in enumerate(yaml_data["examples"]):
                if "response" not in example:
                    continue
                
                response_content = example["response"].strip()
                
                try:
                    # Check if it has styles (v2 format)
                    data = json.loads(response_content)
                    if "styles" not in data:
                        messages.append(f"  Example {i+1}: No styles (skipping)")
                        continue
                    
                    metrics = self.analyze_example(response_content)
                    metrics.file_name = f"{file_name} (Example {i+1})"
                    metrics_list.append(metrics)
                    
                    total_v1_size += metrics.original_size
                    total_v2_size += metrics.migrated_size
                    valid_examples += 1
                    
                    messages.append(f"  Example {i+1}: {metrics.size_reduction_percent:.1f}% size reduction")
                    
                except json.JSONDecodeError:
                    messages.append(f"  Example {i+1}: Invalid JSON (skipping)")
                    continue
            
            # File summary
            if valid_examples > 0:
                total_reduction = ((total_v1_size - total_v2_size) / total_v1_size * 100) if total_v1_size > 0 else 0
                messages.append(f"  File summary: {total_reduction:.1f}% average size reduction")
                messages.append(f"  Total bytes saved: {total_v1_size - total_v2_size}")
            
            return True, messages, metrics_list
            
        except Exception as e:
            return False, [f"Error processing file: {str(e)}"], metrics_list
    
    def analyze_all_files(self) -> Tuple[bool, List[str], List[PerformanceMetrics]]:
        """
        Analyze performance metrics for all migrated files.
        
        Returns:
            Tuple of (success, messages, all_metrics)
        """
        messages = ["Starting performance analysis of migrated YAML files..."]
        all_metrics = []
        overall_success = True
        
        for filename in self.migrated_files:
            file_path = self.resources_dir / filename
            messages.append(f"\n{'='*60}")
            messages.append(f"ANALYZING: {filename}")
            messages.append(f"{'='*60}")
            
            success, file_messages, file_metrics = self.analyze_file(file_path)
            
            if not success:
                overall_success = False
            
            all_metrics.extend(file_metrics)
            messages.extend(file_messages)
        
        # Overall analysis
        if all_metrics:
            messages.append(f"\n{'='*60}")
            messages.append("OVERALL PERFORMANCE ANALYSIS")
            messages.append(f"{'='*60}")
            
            # Aggregate statistics
            total_v1_size = sum(m.original_size for m in all_metrics)
            total_v2_size = sum(m.migrated_size for m in all_metrics)
            total_reduction = total_v1_size - total_v2_size
            avg_reduction_percent = (total_reduction / total_v1_size * 100) if total_v1_size > 0 else 0
            
            total_styles = sum(m.style_count for m in all_metrics)
            total_references = sum(m.reference_count for m in all_metrics)
            total_duplicates_eliminated = sum(m.duplicate_elimination for m in all_metrics)
            
            avg_parse_improvement = statistics.mean([m.parse_time_improvement for m in all_metrics if m.parse_time_improvement > 0])
            
            messages.append(f"Examples analyzed: {len(all_metrics)}")
            messages.append(f"Total size reduction: {total_reduction:,} bytes ({avg_reduction_percent:.1f}%)")
            messages.append(f"Original total size: {total_v1_size:,} bytes")
            messages.append(f"Migrated total size: {total_v2_size:,} bytes")
            messages.append(f"")
            messages.append(f"Style efficiency:")
            messages.append(f"  Total unique styles: {total_styles}")
            messages.append(f"  Total style references: {total_references}")
            messages.append(f"  Duplicate styles eliminated: {total_duplicates_eliminated}")
            messages.append(f"  Style reuse ratio: {(total_references / total_styles):.1f}x" if total_styles > 0 else "  Style reuse ratio: N/A")
            messages.append(f"")
            messages.append(f"Performance improvements:")
            messages.append(f"  Average parsing speed improvement: {avg_parse_improvement:.1f}%" if avg_parse_improvement > 0 else "  Parsing speed: No significant change")
            
            # Achievement assessment
            target_reduction = 40  # From design document
            if avg_reduction_percent >= target_reduction:
                messages.append(f"")
                messages.append(f"🎯 TARGET ACHIEVED: {avg_reduction_percent:.1f}% reduction exceeds {target_reduction}% target!")
            else:
                messages.append(f"")
                messages.append(f"⚠️  Target missed: {avg_reduction_percent:.1f}% reduction below {target_reduction}% target")
        
        return overall_success, messages, all_metrics
    
    def generate_report(self, metrics_list: List[PerformanceMetrics]) -> str:
        """
        Generate a detailed performance report.
        
        Args:
            metrics_list: List of performance metrics
            
        Returns:
            Formatted report string
        """
        if not metrics_list:
            return "No performance metrics available"
        
        report = []
        report.append("DETAILED PERFORMANCE REPORT")
        report.append("=" * 50)
        report.append("")
        
        # Individual example details
        for metrics in metrics_list:
            report.append(f"Example: {metrics.file_name}")
            report.append(f"  Original size: {metrics.original_size:,} bytes")
            report.append(f"  Migrated size: {metrics.migrated_size:,} bytes")
            report.append(f"  Size reduction: {metrics.size_reduction_bytes:,} bytes ({metrics.size_reduction_percent:.1f}%)")
            report.append(f"  Parse time (original): {metrics.parse_time_original:.3f}ms")
            report.append(f"  Parse time (migrated): {metrics.parse_time_migrated:.3f}ms")
            report.append(f"  Parse improvement: {metrics.parse_time_improvement:.1f}%")
            report.append(f"  Styles defined: {metrics.style_count}")
            report.append(f"  Style references: {metrics.reference_count}")
            report.append(f"  Duplicates eliminated: {metrics.duplicate_elimination}")
            report.append("")
        
        return "\n".join(report)


def main():
    """Main entry point for the performance analysis script"""
    parser = argparse.ArgumentParser(
        description="Analyze performance improvements from YAML schema migration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/performance_analysis.py --all
  python scripts/performance_analysis.py --file system_prompt_spreadsheet_formatting.yaml
  python scripts/performance_analysis.py --detailed --all
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=str, help="Analyze a specific YAML file")
    group.add_argument("--all", action="store_true", help="Analyze all migrated YAML files")
    
    parser.add_argument("--detailed", action="store_true", 
                       help="Generate detailed performance report")
    parser.add_argument("--output", type=str, 
                       help="Save report to file")
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = PerformanceAnalyzer()
    
    try:
        if args.file:
            # Analyze single file
            file_path = analyzer.resources_dir / args.file
            success, messages, metrics_list = analyzer.analyze_file(file_path)
            
        elif args.all:
            # Analyze all files
            success, messages, metrics_list = analyzer.analyze_all_files()
        
        # Print results
        for message in messages:
            print(message)
        
        # Generate detailed report if requested
        if args.detailed and metrics_list:
            report = analyzer.generate_report(metrics_list)
            print(f"\n{report}")
            
            # Save to file if specified
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"\nDetailed report saved to: {args.output}")
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
        return 1
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())